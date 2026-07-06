import sqlite3
import os
from datetime import datetime

DB_PATH = "data/scraper.db"

def get_connection():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loket_events(
            event_id TEXT PRIMARY KEY,
            judul TEXT,
            organizer TEXT,
            harga_tiket TEXT,
            mata_uang TEXT,
            lokasi TEXT,
            latitude REAL,
            longitude REAL,
            apple_maps_link TEXT,
            waktu TEXT,
            deskripsi TEXT,
            link_registrasi TEXT,
            photo TEXT, 
            status_code INTEGER,
            processed_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def event_exists(event_id):
    """
    Mengecek apakah event dengan ID (slug) tertentu sudah pernah di-scrape.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM loket_events WHERE event_id=?",
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
            event_id,
            judul,
            organizer,
            harga_tiket,
            mata_uang,
            lokasi,
            latitude,
            longitude,
            apple_maps_link,
            waktu,
            deskripsi,
            link_registrasi,
            photo,
            status_code,
            processed_at
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_data.get("event_id"),
        event_data.get("judul"),
        event_data.get("organizer"),
        event_data.get("harga_tiket"),
        event_data.get("mata_uang", "IDR"),
        event_data.get("lokasi"),
        event_data.get("latitude"),
        event_data.get("longitude"),
        event_data.get("apple_maps_link"),
        event_data.get("waktu"),
        event_data.get("deskripsi"),
        event_data.get("link_registrasi"),
        event_data.get("photo"),
        event_data.get("status_code", 200),
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()

def export_today_events():
    """
    Mengambil seluruh event Loket.com yang berhasil diproses hari ini 
    untuk kemudian diekspor ke dalam format JSON.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    today_start = datetime.now().strftime("%Y-%m-%dT00:00:00")
    
    cur.execute("""
        SELECT *
        FROM loket_events
        WHERE processed_at >= ?
        ORDER BY processed_at DESC
    """, (today_start,))
    
    rows = cur.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]