import sqlite3
import os

DB_PATH = "data/scraper.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loket_events(
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            organizer TEXT,
            location TEXT,
            latitude REAL,
            longitude REAL,
            period TEXT,
            ticket_price TEXT,
            currency TEXT,
            photo TEXT,
            registration_link TEXT,
            apple_maps_link TEXT
        )
    """)
    conn.commit()
    conn.close()

def event_exists(event_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM loket_events WHERE id=?",
        (event_id,)
    )
    result = cur.fetchone()
    conn.close()
    return result is not None

def save_event(event_data):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO loket_events(
            id,
            title,
            description,
            organizer,
            location,
            latitude,
            longitude,
            period,
            ticket_price,
            currency,
            photo,
            registration_link,
            apple_maps_link
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_data.get("id"),
        event_data.get("title"),
        event_data.get("description"),
        event_data.get("organizer"),
        event_data.get("location"),
        event_data.get("latitude"),
        event_data.get("longitude"),
        event_data.get("period"),
        event_data.get("ticket_price"),
        event_data.get("currency", "IDR"),
        event_data.get("photo"),
        event_data.get("registration_link"),
        event_data.get("apple_maps_link")
    ))
    conn.commit()
    conn.close()

def export_today_events():
    """
    Mengekspor seluruh data event karena field processed_at 
    sudah dihilangkan dari skema tabel.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM loket_events")
    
    rows = cur.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]