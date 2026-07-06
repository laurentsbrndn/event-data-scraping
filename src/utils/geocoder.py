import time
import re
import objc
from CoreLocation import CLGeocoder
from Foundation import NSRunLoop, NSDate

VENUE_ALIASES = {
    "gbk": "Gelora Bung Karno, Jakarta",
    "gelora bung karno": "Gelora Bung Karno, Jakarta",
    "tennis indoor": "Stadion Tenis Indoor, Jakarta",
    "istora": "Istora Senayan, Jakarta",
    "jiexpo": "JIExpo Kemayoran, Jakarta",
    "ice bsd": "Indonesia Convention Exhibition, Tangerang",
    "bengkel hall": "Bengkel Space, Jakarta",
    "zepp kuala lumpur": "Zepp Kuala Lumpur, Malaysia",
    "lampung marriott": "Lampung Marriott Resort & Spa",
    "plenary hall jcc": "Jakarta Convention Center", 
    "jcc senayan": "Jakarta Convention Center",
    "balai sarbini": "Balai Sarbini, Jakarta",
    "cinema 4d hall": "Taman Ismail Marzuki, Jakarta", 
    "taman ismail marzuki": "Taman Ismail Marzuki, Jakarta",
    "fakultas ekonomi dan bisnis universitas indonesia": "Fakultas Ekonomi dan Bisnis UI, Depok",
    "feb ui": "Fakultas Ekonomi dan Bisnis UI, Depok"
}

def clean_location_name(location):
    if not location:
        return ""
    loc = re.sub(r'\(.*?\)', '', location)
    return loc.strip()

def fetch_apple_maps(query):
    """
    Menembak API Apple Maps menggunakan native macOS CoreLocation.
    Jauh lebih kaya database lokasinya dibanding Nominatim.
    """
    geocoder = CLGeocoder.alloc().init()
    result = {"lat": None, "lng": None, "done": False}

    # Callback saat Apple Maps mengembalikan data
    def completion_handler(placemarks, error):
        if placemarks and len(placemarks) > 0:
            loc = placemarks[0].location()
            if loc:
                result["lat"] = loc.coordinate().latitude
                result["lng"] = loc.coordinate().longitude
        result["done"] = True

    try:
        geocoder.geocodeAddressString_completionHandler_(query, completion_handler)

        loop = NSRunLoop.currentRunLoop()
        while not result["done"]:
            loop.runMode_beforeDate_("NSDefaultRunLoopMode", NSDate.dateWithTimeIntervalSinceNow_(0.1))

        time.sleep(1)
        
    except Exception as e:
        print(f"[Apple Maps Error] {e}")

    return result["lat"], result["lng"]

def get_lat_lng(venue_name, city="", province=""):
    if not venue_name or venue_name.lower() == "belum diumumkan":
        return None, None

    venue_name = clean_location_name(venue_name)
    v_lower = venue_name.lower()

    for alias_key, alias_val in VENUE_ALIASES.items():
        if alias_key in v_lower:
            lat, lng = fetch_apple_maps(alias_val)
            if lat and lng:
                return lat, lng

    if city:
        query_with_city = f"{venue_name}, {city}"
        lat, lng = fetch_apple_maps(query_with_city)
        if lat and lng:
            return lat, lng

    lat, lng = fetch_apple_maps(venue_name)
    if lat and lng:
        return lat, lng

    if "," in venue_name:
        first_part = venue_name.split(",")[0].strip()
        lat, lng = fetch_apple_maps(first_part)
        if lat and lng:
            return lat, lng

    foreign_keywords = ["kuala lumpur", "singapore", "malaysia", "tokyo", "bangkok"]
    if not any(kw in v_lower or (city and kw in city.lower()) for kw in foreign_keywords):
        lat, lng = fetch_apple_maps(venue_name + ", Indonesia")
        if lat and lng:
            return lat, lng

    return None, None