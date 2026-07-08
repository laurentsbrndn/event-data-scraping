"""
Reads events from local SQLite (data/scraper.db) and pushes them to Postgres.
Parses period string → start_at / end_at, infers category, converts ticket_price.
Run after scrape_daily.py.
"""

import sys
import os
import re
import uuid
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import psycopg2
from src.utils.db_connector import export_today_events

# ---------------------------------------------------------------------------
# Postgres connection — read from env or fall back to VPS defaults
# ---------------------------------------------------------------------------
PG_HOST = os.environ.get("PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("PG_PORT", "5432"))
PG_DB   = os.environ.get("PG_DB",   "nowi")
PG_USER = os.environ.get("PG_USER", "nowi")
PG_PASS = os.environ.get("PG_PASS", "nowi_prod_2025")

# ---------------------------------------------------------------------------
# Category inference from title/description keywords
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    "music":   ["music", "konser", "concert", "festival musik", "live music", "band", "dj", "jazz", "pop", "rock"],
    "sport":   ["sport", "run", "marathon", "lari", "badminton", "futsal", "olahraga", "fitness", "yoga", "cycling"],
    "art":     ["art", "seni", "pameran", "exhibition", "galeri", "gallery", "lukis", "craft", "kerajinan"],
    "food":    ["food", "kuliner", "gastronomy", "festival makanan", "bazaar", "bazar", "cafe", "coffee"],
    "tech":    ["tech", "technology", "startup", "hackathon", "coding", "developer", "ai", "digital", "workshop tech"],
    "culture": ["budaya", "culture", "traditional", "tradisional", "heritage", "kebudayaan", "wayang", "batik"],
    "comedy":  ["comedy", "stand up", "komedi", "humor", "lawak"],
    "seminar": ["seminar", "webinar", "conference", "konferensi", "summit", "talk", "workshop", "training", "kelas"],
    "theater": ["theater", "theatre", "drama", "teater", "pertunjukan", "perform", "show"],
    "expo":    ["expo", "exhibition", "pameran", "fair", "bazaar", "market"],
}

def infer_category(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "other"

# ---------------------------------------------------------------------------
# Period → start_at / end_at
# ---------------------------------------------------------------------------
DATE_PATTERNS = [
    r'(\d{4}-\d{2}-\d{2})',                          # 2025-07-10
    r'(\d{2}/\d{2}/\d{4})',                           # 10/07/2025
    r'(\d{1,2}\s+\w+\s+\d{4})',                       # 10 July 2025
]

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
}

def _parse_single_date(s: str):
    s = s.strip()
    # Try YYYY-MM-DD
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    # Try DD/MM/YYYY
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    # Try "10 July 2025"
    m = re.match(r'^(\d{1,2})\s+(\w+)\s+(\d{4})$', s)
    if m:
        month = MONTH_MAP.get(m.group(2).lower())
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                pass
    return None

def parse_period(period_str: str):
    """Return (start_at, end_at) as datetime or (None, None)."""
    if not period_str:
        return None, None

    # Collect all date-like tokens
    all_dates = re.findall(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}\s+\w+\s+\d{4}', period_str)
    parsed = [_parse_single_date(d) for d in all_dates]
    parsed = [d for d in parsed if d is not None]

    if not parsed:
        return None, None
    if len(parsed) == 1:
        return parsed[0], parsed[0]
    return parsed[0], parsed[-1]

# ---------------------------------------------------------------------------
# Ticket price → float
# ---------------------------------------------------------------------------
def parse_price(price_str: str):
    if not price_str:
        return None
    cleaned = re.sub(r'[^\d.]', '', price_str.replace(",", ""))
    try:
        v = float(cleaned)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None

# ---------------------------------------------------------------------------
# Main push
# ---------------------------------------------------------------------------
def push_to_postgres():
    events = export_today_events()
    print(f"[INFO] {len(events)} events loaded from SQLite.")

    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        dbname=PG_DB, user=PG_USER, password=PG_PASS
    )
    cur = conn.cursor()

    inserted = 0
    skipped  = 0

    for ev in events:
        reg_link = ev.get("registration_link") or ""
        source   = ev.get("source") or ""

        # De-duplicate by registration_link + source
        cur.execute(
            "SELECT 1 FROM events WHERE link_registrasi = %s AND source = %s",
            (reg_link, source)
        )
        if cur.fetchone():
            skipped += 1
            continue

        start_at, end_at = parse_period(ev.get("period") or "")
        price            = parse_price(ev.get("ticket_price") or "")
        title            = ev.get("title") or ""
        description      = ev.get("description") or ""
        category         = infer_category(title, description)

        cur.execute(
            """
            INSERT INTO events (
                id, name, longitude, latitude,
                deskripsi, link_maps, link_registrasi, harga_tiket,
                start_at, end_at, image_url, category, location_name,
                organizer, currency, source,
                created_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                NOW()
            )
            """,
            (
                str(uuid.uuid4()),
                title,
                ev.get("longitude") or 0.0,
                ev.get("latitude")  or 0.0,
                description,
                ev.get("apple_maps_link") or "",
                reg_link,
                price,
                start_at,
                end_at,
                ev.get("photo") or "",
                category,
                ev.get("location") or "",
                ev.get("organizer") or "",
                ev.get("currency") or "IDR",
                source,
            )
        )
        inserted += 1
        print(f"[OK] {title[:60]}")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n=== Done: {inserted} inserted, {skipped} skipped ===")

if __name__ == "__main__":
    push_to_postgres()
