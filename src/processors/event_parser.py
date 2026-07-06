import json
import re
from bs4 import BeautifulSoup

class EventParser:

    @staticmethod
    def parse(html: str, url: str):

        soup = BeautifulSoup(html, "lxml")

        result = {
            "id": None,
            "title": None,
            "description": None,
            "organizer": None,
            "venue_name": None,
            "address": None,
            "city": None,
            "province": None,
            "period": None,
            "ticket_price": None,
            "currency": "IDR",
            "photo": None,
            "terms_conditions": None,
            "latitude": None,
            "longitude": None
        }

        # ===========================
        # JSON-LD Parsing
        # ===========================
        scripts = soup.find_all(
            "script",
            attrs={"type": "application/ld+json"}
        )

        schema = None

        for s in scripts:
            try:
                data = json.loads(s.string)
                
                # Antisipasi jika JSON-LD berbentuk list of objects
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "Event":
                            schema = item
                            break
                elif isinstance(data, dict):
                    if data.get("@type") == "Event":
                        schema = data
                        break
                
                if schema:
                    break

            except Exception:
                pass

        if schema is None:
            return result

        # ===========================
        # TITLE, DESC & ID
        # ===========================
        result["title"] = schema.get("name")
        raw_desc = schema.get("description")
        if raw_desc:
            result["description"] = BeautifulSoup(raw_desc, "lxml").get_text(separator=" ", strip=True)

        result["id"] = schema.get("url", url).split("?")[0].split("/")[-1]

        # ===========================
        # WAKTU
        # ===========================
        start_date = schema.get("startDate", "")
        end_date = schema.get("endDate", "")
        if start_date:
            result["period"] = f"{start_date} - {end_date}" if end_date else start_date

        # ===========================
        # LOCATION & ADDRESS (Anti-Error)
        # ===========================
        raw_location = schema.get("location", {})
        location_dict = {}

        # 1. Pastikan kita bekerja dengan dictionary, bukan list
        if isinstance(raw_location, list):
            location_dict = raw_location[0] if len(raw_location) > 0 else {}
        elif isinstance(raw_location, dict):
            location_dict = raw_location

        # 2. Ambil venue_name dengan aman
        result["venue_name"] = location_dict.get("name")

        # 3. Ambil address dengan aman dari location_dict
        address = location_dict.get("address", {})
        if isinstance(address, dict):
            result["address"] = address.get("streetAddress")
            result["province"] = address.get("addressRegion")
            result["city"] = address.get("addressLocality")
        elif isinstance(address, str):
            result["address"] = address # Terkadang address cuma berupa string

        # ===========================
        # OFFERS / HARGA TIKET
        # ===========================
        raw_offers = schema.get("offers", {})
        offers_dict = {}

        if isinstance(raw_offers, list):
            offers_dict = raw_offers[0] if len(raw_offers) > 0 else {}
        elif isinstance(raw_offers, dict):
            offers_dict = raw_offers

        harga = offers_dict.get("lowPrice") or offers_dict.get("price")
        if harga:
            result["ticket_price"] = str(harga)
        
        result["currency"] = offers_dict.get("priceCurrency", "IDR")
        
        location_context = f"{result.get('venue_name', '')} {result.get('city', '')} {result.get('province', '')}".lower()
        
        if "malaysia" in location_context or "kuala lumpur" in location_context:
            result["currency"] = "MYR"
        elif "singapore" in location_context or "singapura" in location_context:
            result["currency"] = "SGD"
        elif "australia" in location_context or "sydney" in location_context:
            result["currency"] = "AUD"

        # ===========================
        # POSTER / GAMBAR (PHOTO)
        # ===========================
        image = schema.get("image")
        if image:
            if isinstance(image, list) and len(image) > 0:
                result["photo"] = image[0]
            elif isinstance(image, str):
                result["photo"] = image 

        # ===========================
        # ORGANIZER
        # ===========================
        text = soup.get_text("\n", strip=True)
        m = re.search(
            r"Diselenggarakan oleh\s*(.*?)\n",
            text
        )
        if m:
            result["organizer"] = m.group(1).strip()

        # ===========================
        # TERMS & CONDITIONS
        # ===========================
        tnc = soup.find(id="tnc")
        if tnc:
            result["terms_conditions"] = tnc.get_text(
                "\n",
                strip=True
            )

        return result