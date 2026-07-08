from playwright.sync_api import sync_playwright
from src.processors.event_parser import EventParser
from bs4 import BeautifulSoup

class YesplisScraper:
    BASE_URL = "https://yesplis.com"

    def __init__(self, headless=True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
        )
        self.page = self.context.new_page()

    def close(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()

    def open_homepage(self):
        print("[INFO] Opening Yesplis homepage...")
        self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
        self.page.wait_for_timeout(3000)

    def get_event_links(self, limit=30):
        html = self.page.content()
        soup = BeautifulSoup(html, "lxml")
        links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/event/" in href or "/e/" in href: 
                if href.startswith("/"): href = self.BASE_URL + href
                links.add(href.split('?')[0])
                
        return list(links)[:limit]

    def scrape_event(self, url):
        self.page.goto(url, wait_until="networkidle")
        self.page.wait_for_timeout(3000)
        return EventParser.parse(self.page.content(), url)