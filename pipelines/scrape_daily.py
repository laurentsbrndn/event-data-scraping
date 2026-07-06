import sys
import os
import json
from datetime import datetime
import urllib.parse

from deep_translator import GoogleTranslator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.scrapers.loket_scraper import LoketScraper
from src.utils.db_connector import init_db, event_exists, save_event, export_today_events
from src.utils.geocoder import get_lat_lng

def run_loket_pipeline():
    init_db()
    today_str = datetime.now().strftime("%Y-%m-%d")
    output_file = f"data/processed_json/loket_events_{today_str}.json"

    print(f"\n=== Memulai Pipeline LOKET.COM {today_str} ===\n")

    scraper = LoketScraper(headless=True)
    
    translator = GoogleTranslator(source='auto', target='en')
    
    try:
        scraper.open_homepage()
        event_links = scraper.get_event_links(limit=20) 
        
        print(f"Ditemukan {len(event_links)} link event. Mulai scraping...\n")

        for link in event_links:
            clean_link = link.split('?')[0]
            event_id = clean_link.rstrip('/').split('/')[-1]

            if event_exists(event_id):
                print(f"[SKIP] Event '{event_id}' sudah ada di database.")
                continue

            print(f"Memproses: {clean_link}")
            
            try:
                event_data = scraper.scrape_event(clean_link)
            except Exception as e:
                print(f"[ERROR] Gagal parse {clean_link}: {e}")
                continue
            
            venue = event_data.get("venue_name", "")
            if not venue or venue.strip().lower() == "belum diumumkan":
                print(f"[SKIP] Event '{event_id}' dilewati karena lokasi Belum Diumumkan / Kosong.")
                continue

            # -------------------------------------
            # Geocoding Multi-Parameter
            # -------------------------------------
            city = event_data.get("city", "")
            province = event_data.get("province", "")
            
            lat, lng = None, None
            try:
                lat, lng = get_lat_lng(venue, city, province)
                print(f"[Geocoder] {venue} ({city}) -> ({lat}, {lng})")
            except Exception as e:
                print(f"[Geocoder Error] {e}")
            
            # -------------------------------------
            # Pembuatan Link Apple Maps
            # -------------------------------------
            encoded_venue = urllib.parse.quote(venue)
            if lat and lng:
                apple_maps_link = f"https://maps.apple.com/?ll={lat},{lng}&q={encoded_venue}"
            else:
                apple_maps_link = f"https://maps.apple.com/?q={encoded_venue}"

            # -------------------------------------
            # Translation (Deskripsi ke Bahasa Inggris)
            # -------------------------------------
            raw_desc = event_data.get("deskripsi", "")
            translated_desc = ""
            
            if raw_desc:
                try:
                    # Proses translasi
                    translated_desc = translator.translate(raw_desc)
                    print("[Translator] Deskripsi berhasil diterjemahkan ke Bahasa Inggris.")
                except Exception as e:
                    print(f"[Translator Error] Gagal menerjemahkan: {e}")
                    translated_desc = raw_desc

            # -------------------------------------
            # Persiapan Data untuk Database
            # -------------------------------------
            event_data_to_save = {
                "event_id": event_id,
                "judul": event_data.get("judul", ""),
                "organizer": event_data.get("organizer", ""),
                "harga_tiket": event_data.get("harga", ""),
                "mata_uang": event_data.get("mata_uang", "IDR"),
                "lokasi": venue,
                "latitude": lat,
                "longitude": lng,
                "apple_maps_link": apple_maps_link,
                "waktu": event_data.get("waktu", ""),
                "deskripsi": translated_desc,
                "link_registrasi": clean_link,
                "photo": event_data.get("photo", ""), 
                "status_code": 200
            }

            save_event(event_data_to_save)
            print(f"[SUCCESS] Tersimpan: {event_data_to_save['judul']}\n")

    finally:
        scraper.close()

    # -------------------------------------
    # Export JSON
    # -------------------------------------
    events = export_today_events()
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=4, ensure_ascii=False)

    print(f"\n=== Pipeline Selesai ===")
    print(f"{len(events)} event valid berhasil diekspor ke {output_file}")

if __name__ == "__main__":
    run_loket_pipeline()