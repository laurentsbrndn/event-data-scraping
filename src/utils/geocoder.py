import time
import re
import platform

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
    "feb ui": "Fakultas Ekonomi dan Bisnis UI, Depok",
    "swasana lippo kuningan grand ballroom": "Lippo Kuningan, Jakarta",
    "swasana lippo kuningan": "Lippo Kuningan, Jakarta",
    "amphitheatre, kab. lampung selatan, lampung": "Krakatau Park, Bakauheni, Lampung Selatan",
    "amphitheatre, kab. lampung selatan": "Krakatau Park, Bakauheni, Lampung Selatan",
    "gedung jetun silangit": "Gedung Jetun Silangit, Tapanuli Utara",
    "stadium university of jember, kab. jember, jawa timur": "Stadion Universitas Jember, Jawa Timur",
    "stadium university of jember": "Stadion Universitas Jember, Jawa Timur",
    "lapangan pkor way halim, kota bandar lampung, lampung": "PKOR Way Halim, Bandar Lampung",
    "lapangan pkor way halim": "PKOR Way Halim, Bandar Lampung",
    "bagi kopi, kab. sumedang, jawa barat": "Bagi Kopi, Sumedang",
    "bagi kopi": "Bagi Kopi, Sumedang",
    "de tjolomadoe, karanganyar, kab. karanganyar, jawa tengah": "De Tjolomadoe, Karanganyar",
    "de tjolomadoe, kab. karanganyar, jawa tengah": "De Tjolomadoe, Karanganyar",
    "de tjolomadoe": "De Tjolomadoe, Karanganyar"
}

def clean_location_name(location):
    if not location:
        return ""
    loc = re.sub(r'\(.*?\)', '', location)
    return " ".join(loc.split())


# ---------------------------------------------------------------------------
# Backend: Apple Maps (macOS only) vs Nominatim (Linux/cross-platform)
# ---------------------------------------------------------------------------

def _fetch_apple_maps(query):
    try:
        import objc
        from CoreLocation import CLGeocoder
        from Foundation import NSRunLoop, NSDate

        geocoder = CLGeocoder.alloc().init()
        result = {"lat": None, "lng": None, "done": False}

        def completion_handler(placemarks, error):
            if placemarks and len(placemarks) > 0:
                loc = placemarks[0].location()
                if loc:
                    result["lat"] = loc.coordinate().latitude
                    result["lng"] = loc.coordinate().longitude
            result["done"] = True

        geocoder.geocodeAddressString_completionHandler_(query, completion_handler)
        loop = NSRunLoop.currentRunLoop()
        while not result["done"]:
            loop.runMode_beforeDate_("NSDefaultRunLoopMode", NSDate.dateWithTimeIntervalSinceNow_(0.1))
        time.sleep(1)
        return result["lat"], result["lng"]
    except Exception as e:
        print(f"[Apple Maps Error] {e}")
        return None, None


def _fetch_nominatim(query):
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError

        geolocator = Nominatim(user_agent="nowi-event-scraper/1.0")
        location = geolocator.geocode(query, timeout=10)
        time.sleep(1)  # respect Nominatim rate limit (1 req/s)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"[Nominatim Error] {e}")
    return None, None


# Use Apple Maps on macOS (better local data), Nominatim elsewhere
_IS_MACOS = platform.system() == "Darwin"

def fetch_geocode(query):
    if _IS_MACOS:
        return _fetch_apple_maps(query)
    return _fetch_nominatim(query)


def get_lat_lng(venue_name, city="", province=""):
    if not venue_name or venue_name.lower() == "belum diumumkan":
        return None, None

    venue_name = clean_location_name(venue_name)
    v_lower = venue_name.lower()

    # 1. Alias dictionary
    for alias_key, alias_val in VENUE_ALIASES.items():
        if alias_key in v_lower:
            lat, lng = fetch_geocode(alias_val)
            if lat and lng:
                return lat, lng

    # 2. Venue + city
    if city:
        lat, lng = fetch_geocode(f"{venue_name}, {city}")
        if lat and lng:
            return lat, lng

    # 3. Venue name only
    lat, lng = fetch_geocode(venue_name)
    if lat and lng:
        return lat, lng

    # 4. First part before comma
    if "," in venue_name:
        lat, lng = fetch_geocode(venue_name.split(",")[0].strip())
        if lat and lng:
            return lat, lng

    # 5. Fallback + Indonesia
    foreign_keywords = ["kuala lumpur", "singapore", "malaysia", "tokyo", "bangkok"]
    if not any(kw in v_lower or (city and kw in city.lower()) for kw in foreign_keywords):
        lat, lng = fetch_geocode(venue_name + ", Indonesia")
        if lat and lng:
            return lat, lng

    return None, None
