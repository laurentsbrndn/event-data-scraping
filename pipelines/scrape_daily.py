# import sys
# import os
# import json
# from datetime import datetime
# from deep_translator import GoogleTranslator

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from src.scrapers.loket_scraper import LoketScraper
# from src.scrapers.yesplis_scraper import YesplisScraper
# from src.scrapers.artatix_scraper import ArtatixScraper
# from src.utils.db_connector import init_db, event_exists, save_event, export_today_events
# from src.utils.geocoder import get_lat_lng

# def process_platform(scraper_class, platform_name, translator):
#     print(f"\n=== Memulai Pipeline {platform_name.upper()} ===")
#     scraper = scraper_class(headless=True)
    
#     try:
#         scraper.open_homepage()
#         event_links = scraper.get_event_links(limit=35) 
#         print(f"Ditemukan {len(event_links)} link event di {platform_name}.\n")

#         for link in event_links:
#             clean_link = link.split('?')[0]
#             event_id = clean_link.rstrip('/').split('/')[-1]

#             # Cek eksistensi berdasarkan id DAN source
#             if event_exists(event_id, platform_name):
#                 print(f"[SKIP] Event '{event_id}' sudah ada.")
#                 continue

#             print(f"Memproses: {clean_link}")
            
#             try:
#                 event_data = scraper.scrape_event(clean_link)
                
#                 venue = event_data.get("venue_name") or ""
                
#                 if not venue.strip():
#                     print(f"[SKIP] Event '{event_id}' diabaikan karena kolom lokasi kosong.")
#                     continue

#                 lat, lng = get_lat_lng(venue)
                
#                 apple_maps_link = f"https://maps.apple.com/?ll={lat},{lng}&q={venue.replace(' ', '%20')}" if lat and lng else ""

#                 raw_desc = event_data.get("description") or ""
#                 translated_desc = raw_desc
#                 if raw_desc:
#                     try:
#                         translated_desc = translator.translate(raw_desc[:4900])
#                     except Exception as e:
#                         pass

#                 event_data_to_save = {
#                     "id": event_id,
#                     "source": platform_name,
#                     "title": event_data.get("title", ""),
#                     "description": translated_desc,
#                     "organizer": event_data.get("organizer", ""),
#                     "location": venue,
#                     "latitude": lat,
#                     "longitude": lng,
#                     "period": event_data.get("period", ""),
#                     "ticket_price": event_data.get("ticket_price", ""),
#                     "currency": event_data.get("currency", "IDR"),
#                     "photo": event_data.get("photo", ""), 
#                     "registration_link": clean_link,
#                     "apple_maps_link": apple_maps_link
#                 }

#                 save_event(event_data_to_save)
#                 print(f"[SUCCESS] Tersimpan: {event_data_to_save['title']}\n")

#             except Exception as e:
#                 print(f"[ERROR] Gagal memproses {clean_link}: {e}")

#     finally:
#         scraper.close()

# def run_unified_pipeline():
#     init_db()
#     today_str = datetime.now().strftime("%Y-%m-%d")
#     translator = GoogleTranslator(source='auto', target='en')

#     process_platform(LoketScraper, "loket", translator)
#     process_platform(YesplisScraper, "yesplis", translator)
#     process_platform(ArtatixScraper, "artatix", translator)

#     output_file = f"data/processed_json/all_events_{today_str}.json"
#     events = export_today_events()
    
#     os.makedirs(os.path.dirname(output_file), exist_ok=True)
#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(events, f, indent=4, ensure_ascii=False)

#     print(f"\n=== Pipeline Selesai ===")
#     print(f"{len(events)} event valid dari semua platform berhasil diekspor ke {output_file}")

# if __name__ == "__main__":
#     run_unified_pipeline()

import sys
import os
import json
import re
from datetime import datetime
from deep_translator import GoogleTranslator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.scrapers.loket_scraper import LoketScraper
from src.scrapers.yesplis_scraper import YesplisScraper
from src.scrapers.artatix_scraper import ArtatixScraper
from src.utils.db_connector import init_db, event_exists, save_event, export_today_events
from src.utils.geocoder import get_lat_lng

def is_upcoming_event(period_str):
    """
    Validasi apakah event masih akan datang (minimal H+1 dari hari ini).
    Mengekstrak tanggal terakhir dari string period berformat YYYY-MM-DD.
    """
    if not period_str:
        return True # Loloskan jika periode kosong agar tidak kehilangan data
        
    # Ekstrak semua format YYYY-MM-DD dari string
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', period_str)
    if not dates:
        return True 
        
    # Ambil tanggal paling akhir (End Date) jika berupa range
    end_date_str = dates[-1] 
    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        
        # Jika acara selesai hari ini atau di masa lalu, skip datanya
        if end_date <= today:
            return False
        return True
    except ValueError:
        return True

def process_platform(scraper_class, platform_name, translator):
    print(f"\n=== Memulai Pipeline {platform_name.upper()} ===")
    scraper = scraper_class(headless=True)
    
    try:
        scraper.open_homepage()
        event_links = scraper.get_event_links(limit=35) 
        print(f"Ditemukan {len(event_links)} link event di {platform_name}.\n")

        for link in event_links:
            clean_link = link.split('?')[0]
            event_id = clean_link.rstrip('/').split('/')[-1]

            # Cek eksistensi berdasarkan id DAN source
            if event_exists(event_id, platform_name):
                print(f"[SKIP] Event '{event_id}' sudah ada.")
                continue

            print(f"Memproses: {clean_link}")
            
            try:
                event_data = scraper.scrape_event(clean_link)
                
                # ==========================================
                # VALIDASI TANGGAL EVENT (H+1)
                # ==========================================
                period = event_data.get("period") or ""
                if not is_upcoming_event(period):
                    print(f"[SKIP] Event '{event_id}' diabaikan karena jadwal sudah selesai atau sedang berlangsung hari ini ({period}).")
                    continue
                
                venue = event_data.get("venue_name") or ""
                
                if not venue.strip():
                    print(f"[SKIP] Event '{event_id}' diabaikan karena kolom lokasi kosong.")
                    continue

                lat, lng = get_lat_lng(venue)
                
                apple_maps_link = f"https://maps.apple.com/?ll={lat},{lng}&q={venue.replace(' ', '%20')}" if lat and lng else ""

                raw_desc = event_data.get("description") or ""
                translated_desc = raw_desc
                if raw_desc:
                    try:
                        translated_desc = translator.translate(raw_desc[:4900])
                    except Exception as e:
                        pass

                event_data_to_save = {
                    "id": event_id,
                    "source": platform_name,
                    "title": event_data.get("title", ""),
                    "description": translated_desc,
                    "organizer": event_data.get("organizer", ""),
                    "location": venue,
                    "latitude": lat,
                    "longitude": lng,
                    "period": period,
                    "ticket_price": event_data.get("ticket_price", ""),
                    "currency": event_data.get("currency", "IDR"),
                    "photo": event_data.get("photo", ""), 
                    "registration_link": clean_link,
                    "apple_maps_link": apple_maps_link
                }

                save_event(event_data_to_save)
                print(f"[SUCCESS] Tersimpan: {event_data_to_save['title']}\n")

            except Exception as e:
                print(f"[ERROR] Gagal memproses {clean_link}: {e}")

    finally:
        scraper.close()

def run_unified_pipeline():
    init_db()
    today_str = datetime.now().strftime("%Y-%m-%d")
    translator = GoogleTranslator(source='auto', target='en')

    process_platform(LoketScraper, "loket", translator)
    process_platform(YesplisScraper, "yesplis", translator)
    process_platform(ArtatixScraper, "artatix", translator)

    output_file = f"data/processed_json/all_events_{today_str}.json"
    events = export_today_events()
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=4, ensure_ascii=False)

    print(f"\n=== Pipeline Selesai ===")
    print(f"{len(events)} event valid dari semua platform berhasil diekspor ke {output_file}")

if __name__ == "__main__":
    run_unified_pipeline()