import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

class EventParser:

    @staticmethod
    def parse(html: str, url: str):
        if "yesplis.com" in url:
            return EventParser._parse_yesplis(html, url)
        elif "artatix.co.id" in url:
            return EventParser._parse_artatix(html, url)
        else:
            return EventParser._parse_loket(html, url)

    @staticmethod
    def _normalize_period(date_str: str, time_str: str):
        """
        date_str mendeteksi 3 skenario:
            1. Hari tunggal: 18 Juli 2026
            2. Multi-hari (bulan sama): 25 - 26 Juli 2026
            3. Multi-hari (bulan beda): 19 Juni - 30 Agustus 2026
        """

        months = {
            "Januari": 1, "Februari": 2, "Maret": 3, "April": 4,
            "Mei": 5, "Juni": 6, "Juli": 7, "Agustus": 8,
            "September": 9, "Oktober": 10, "November": 11, "Desember": 12,
        }

        # waktu
        time_match = re.match(r"(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})", time_str)
        if not time_match:
            return None

        start_time = time_match.group(1)
        end_time = time_match.group(2)

        # Kasus 3: Beda bulan (Contoh: 19 Juni - 30 Agustus 2026)
        multi_month = re.match(
            r"(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", 
            date_str
        )

        # Kasus 2: Bulan sama (Contoh: 25 - 26 Juli 2026)
        multi_day = re.match(
            r"(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            date_str
        )
        
        # Kasus 1: Hari tunggal (Contoh: 18 Juli 2026)
        single_day = re.match(
            r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})",
            date_str
        )

        if multi_month:
            start_day = int(multi_month.group(1))
            start_month = months[multi_month.group(2)]
            end_day = int(multi_month.group(3))
            end_month = months[multi_month.group(4)]
            year = int(multi_month.group(5))

            start_dt = datetime.strptime(
                f"{year}-{start_month:02d}-{start_day:02d} {start_time}",
                "%Y-%m-%d %H:%M"
            )
            end_dt = datetime.strptime(
                f"{year}-{end_month:02d}-{end_day:02d} {end_time}",
                "%Y-%m-%d %H:%M"
            )

        elif multi_day:
            start_day = int(multi_day.group(1))
            end_day = int(multi_day.group(2))
            month = months[multi_day.group(3)]
            year = int(multi_day.group(4))

            start_dt = datetime.strptime(
                f"{year}-{month:02d}-{start_day:02d} {start_time}",
                "%Y-%m-%d %H:%M"
            )
            end_dt = datetime.strptime(
                f"{year}-{month:02d}-{end_day:02d} {end_time}",
                "%Y-%m-%d %H:%M"
            )

        elif single_day:
            day = int(single_day.group(1))
            month = months[single_day.group(2)]
            year = int(single_day.group(3))

            start_dt = datetime.strptime(
                f"{year}-{month:02d}-{day:02d} {start_time}",
                "%Y-%m-%d %H:%M"
            )
            end_dt = datetime.strptime(
                f"{year}-{month:02d}-{day:02d} {end_time}",
                "%Y-%m-%d %H:%M"
            )
            
        else:
            return None

        return (
            f"{start_dt.strftime('%Y-%m-%d %H:%M:%S')} Asia/Jakarta - "
            f"{end_dt.strftime('%Y-%m-%d %H:%M:%S')} Asia/Jakarta"
        )

    @staticmethod
    def _parse_loket(html: str, url: str):

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
    
    @staticmethod
    def _parse_yesplis(html: str, url: str):
        soup = BeautifulSoup(html, "lxml")
        
        result = {
            "id": url.rstrip('/').split('/')[-1],
            "title": None,
            "description": None,
            "organizer": None,
            "venue_name": None,
            "period": None,
            "ticket_price": None,
            "currency": "IDR",
            "photo": None,
            "registration_link": url
        }

        # ===========================
        # 1. META TAGS EXTRACTOR
        # ===========================
        meta_title = soup.find("meta", property="og:title")
        if meta_title:
            result["title"] = meta_title.get("content")

        meta_desc = soup.find("meta", property="og:description")
        if meta_desc:
            raw_desc = meta_desc.get("content")
            # --- [FIX 1] Membersihkan Tag HTML pada Deskripsi ---
            result["description"] = BeautifulSoup(raw_desc, "lxml").get_text(separator="\n", strip=True)

        # ===========================
        # 2. DOM PARSING (Lokasi, Harga, Organizer, Waktu)
        # ===========================
        
        # Ekstrak Lokasi (Venue)
        map_link = soup.find("a", string=re.compile(r"Petunjuk Arah", re.IGNORECASE))
        if map_link:
            loc_div = map_link.find_previous_sibling("div")
            if loc_div:
                result["venue_name"] = loc_div.get_text(strip=True)

        # Fallback Lokasi
        if not result["venue_name"]:
            gmaps_link = soup.find("a", href=re.compile(r"maps\.google\.com", re.IGNORECASE))
            if gmaps_link:
                loc_div = gmaps_link.find_previous_sibling("div")
                if loc_div:
                    result["venue_name"] = loc_div.get_text(strip=True)

        # --- [FIX 2] Ekstrak & Bersihkan Harga (DIPERBARUI) ---
        # Skenario 1: Cari berdasarkan kata kunci standar ("Mulai Dari" atau "Harga")
        price_label = soup.find(string=re.compile(r"(Mulai Dari|Harga)", re.IGNORECASE))
        if price_label and price_label.parent:
            price_val = price_label.parent.find_next_sibling()
            if price_val:
                raw_price = price_val.get_text(strip=True)
                clean_price = re.sub(r"[^\d]", "", raw_price)
                result["ticket_price"] = clean_price if clean_price else "0"
                
        # Skenario 2 (FALLBACK): Jika masih 0 atau None, sapu bersih teks yang mengandung "Rp"
        if not result.get("ticket_price") or result.get("ticket_price") == "0":
            # Mencari teks apapun di HTML yang polanya seperti "Rp 150.000" atau "Rp150000"
            rp_element = soup.find(string=re.compile(r"Rp\s*[\d\.,]+", re.IGNORECASE))
            if rp_element:
                clean_price = re.sub(r"[^\d]", "", rp_element)
                result["ticket_price"] = clean_price if clean_price else "0"
                
        # Ekstrak Organizer
        org_label = soup.find(string=re.compile(r"Dibuat Oleh", re.IGNORECASE))
        if org_label and org_label.parent:
            org_val = org_label.parent.find_next_sibling()
            if org_val:
                result["organizer"] = org_val.get_text(strip=True)
                
        # --- [FIX 3] Ekstrak & Standarisasi Tanggal (Format Loket) ---
        if map_link:
            try:
                loc_div = map_link.find_previous_sibling("div")
                time_div = loc_div.find_previous_sibling("div")
                date_div = time_div.find_previous_sibling("div")
                
                date_text = date_div.get_text(strip=True) if date_div else ""
                time_text = time_div.get_text(strip=True) if time_div else ""
                
                if date_text and time_text:
                    # Helper function untuk parse format indonesia
                    def parse_to_loket_format(d_text, t_text):
                        months = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "mei": "05", "jun": "06", 
                                  "jul": "07", "agt": "08", "sep": "09", "okt": "10", "nov": "11", "des": "12"}
                        
                        # Ekstrak Jam (Default ke 00:00:00 jika tidak terbaca)
                        time_match = re.search(r"(\d{2}:\d{2})", t_text)
                        base_time = f"{time_match.group(1)}:00" if time_match else "00:00:00"
                        
                        d_text_lower = d_text.lower()
                        year_match = re.search(r"(\d{4})", d_text_lower)
                        year = year_match.group(1) if year_match else str(datetime.now().year)
                        
                        # Hapus tahun dari string agar mudah di split
                        d_text_no_year = re.sub(r"\d{4}", "", d_text_lower).strip()
                        parts = [p.strip() for p in d_text_no_year.split("-")]
                        
                        def get_formatted_date(date_str, default_month="01"):
                            day_match = re.search(r"(\d{1,2})", date_str)
                            day = day_match.group(1).zfill(2) if day_match else "01"
                            month = default_month
                            for m_name, m_num in months.items():
                                if m_name in date_str:
                                    month = m_num
                                    break
                            return f"{year}-{month}-{day}"

                        if len(parts) == 1:
                            single_date = get_formatted_date(parts[0])
                            return f"{single_date} {base_time} Asia/Jakarta"
                        else:
                            end_date_str = get_formatted_date(parts[1])
                            end_month = end_date_str.split("-")[1] 
                            start_date_str = get_formatted_date(parts[0], default_month=end_month)
                            
                            return f"{start_date_str} {base_time} Asia/Jakarta - {end_date_str} {base_time} Asia/Jakarta"

                    result["period"] = parse_to_loket_format(date_text, time_text)
            except Exception as e:
                pass 
        
        poster_img = soup.find("img", src=re.compile(r"ypassets\.yesplis\.com/.*?/assets/", re.IGNORECASE))
        
        if poster_img:
            result["photo"] = poster_img.get("src")
        else:
            # Fallback jika URL asetnya berganti format, kita ambil dari class banner-nya
            banner_div = soup.find("div", class_=re.compile(r"ra-event-banner", re.IGNORECASE))
            if banner_div:
                img_tag = banner_div.find("img")
                if img_tag:
                    result["photo"] = img_tag.get("src")

        return result
    
    @staticmethod
    def _parse_artatix(html: str, url: str):
        soup = BeautifulSoup(html, "lxml")
        slug = url.rstrip('/').split('/')[-1]
        
        result = {
            "id": slug,
            "title": None,
            "description": None,
            "organizer": None,
            "venue_name": None,
            "period": None,
            "ticket_price": None,
            "currency": "IDR",
            "photo": None,
            "registration_link": url
        }

        # ==============================================================
        # 1. CLEANING DOM (Wajib!) 
        # Hapus script & svg agar kita fokus pada teks asli
        # ==============================================================
        for element in soup(["script", "style", "noscript", "template", "svg"]):
            element.extract()

        # ==============================================================
        # 2. META TAGS (Judul & Foto selalu akurat dari Meta SEO)
        # ==============================================================
        meta_title = soup.find("meta", property="og:title")
        if meta_title:
            result["title"] = meta_title.get("content", "").replace(" | Artatix", "").strip()
            
        meta_img = soup.find("meta", property="og:image")
        if meta_img:
            result["photo"] = meta_img.get("content", "")

        if not result["title"]:
            h1 = soup.find("h1")
            if h1: result["title"] = h1.get_text(strip=True)

        # ==============================================================
        # 3. EKSTRAK WAKTU & LOKASI (Dari Header "Detail Acara")
        # ==============================================================
        detail_header = soup.find(["h2", "h1"], string=re.compile(r"Detail Acara", re.IGNORECASE))
        if detail_header and detail_header.parent:
            # Ambil semua teks <span> di bawah parent Detail Acara
            spans = detail_header.parent.find_all("span")
            texts = [span.get_text(strip=True) for span in spans if span.get_text(strip=True)]
            
            # Format standar grid Artatix: [0] Tanggal, [1] Jam, [2] Lokasi Lengkap
            if len(texts) >= 3:
                result["period"] = EventParser._normalize_period(
                    texts[0],
                    texts[1]
                )
                result["venue_name"] = texts[2]
            elif len(texts) > 0:
                result["venue_name"] = texts[-1] 

        # ==============================================================
        # 4. EKSTRAK PENYELENGGARA
        # ==============================================================
        org_label = soup.find(string=re.compile(r"Penyelenggara", re.IGNORECASE))
        if org_label and org_label.parent and org_label.parent.parent:
            # Menyapu semua teks di dalam kontainer yang sama dengan label Penyelenggara
            org_texts = list(org_label.parent.parent.stripped_strings)
            if len(org_texts) > 1:
                result["organizer"] = org_texts[-1] # Nama penyelenggara selalu ada di urutan terakhir

        # ==============================================================
        # 5. EKSTRAK HARGA TIKET
        # ==============================================================
        price_label = soup.find(string=re.compile(r"Harga mulai dari", re.IGNORECASE))
        if price_label and price_label.parent:
            # Harga berada pada tag berikutnya, get_text() akan menghapus komentar "<!-- -->"
            price_val = price_label.parent.find_next_sibling()
            if price_val:
                raw_price = price_val.get_text(strip=True)
                clean_price = re.sub(r"[^\d]", "", raw_price)
                if clean_price:
                    result["ticket_price"] = clean_price
        
        # Fallback Harga jika struktur berbeda
        if not result["ticket_price"]:
            rp_elements = soup.find_all(string=re.compile(r"Rp", re.IGNORECASE))
            prices = []
            for rp in rp_elements:
                clean_price = re.sub(r"[^\d]", "", rp.parent.get_text(strip=True))
                if clean_price and len(clean_price) <= 9:
                    prices.append(int(clean_price))
            result["ticket_price"] = str(min(prices)) if prices else "0"

        # ==============================================================
        # 6. EKSTRAK DESKRIPSI
        # ==============================================================
        desc_header = soup.find(["h1", "h2", "h3"], string=re.compile(r"Deskripsi", re.IGNORECASE))
        if desc_header:
            desc_content = desc_header.find_next_sibling("div", class_=re.compile(r"editor-scope"))
            if desc_content:
                result["description"] = desc_content.get_text(separator="\n", strip=True)

        return result