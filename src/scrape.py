"""HTML web-scraping extractor.

Most data has a clean REST API (see ``RestExtractor``) — but sometimes the only
source is an HTML page. This extractor parses a price table out of HTML with
BeautifulSoup and emits the *same* raw-dict shape the REST extractor does, so it
drops straight into the existing pipeline (polymorphism: the orchestrator can't
tell which extractor it's using).

It can read a live URL or a local HTML file, so it runs and tests offline.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import Extractor

logger = logging.getLogger("cryptostream")


class HtmlScrapeExtractor(Extractor):
    """Scrape a coin price table from an HTML page into raw records."""

    def __init__(self, url: str | None = None, html_path: str | Path | None = None,
                 timeout: int = 20) -> None:
        if not url and not html_path:
            raise ValueError("provide either url= or html_path=")
        self.url = url
        self.html_path = Path(html_path) if html_path else None
        self.timeout = timeout

    def _load_html(self) -> str:
        if self.html_path:
            logger.info("Scraping local HTML file %s", self.html_path)
            return self.html_path.read_text(encoding="utf-8")
        import requests
        logger.info("Scraping live URL %s", self.url)
        resp = requests.get(self.url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _to_float(text: str) -> float:
        """'$61,250.00' / '+2.41%' -> float."""
        cleaned = (text or "").replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def extract(self) -> list[dict]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(self._load_html(), "html.parser")
        rows = soup.select("table.coins tbody tr")
        records: list[dict] = []
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 7:
                continue
            records.append({
                "id": cells[0].get_text(strip=True).lower().replace(" ", "-"),
                "name": cells[0].get_text(strip=True),
                "symbol": cells[1].get_text(strip=True),
                "current_price": self._to_float(cells[2].get_text()),
                "market_cap": self._to_float(cells[3].get_text()),
                "total_volume": self._to_float(cells[4].get_text()),
                "market_cap_rank": int(self._to_float(cells[5].get_text())) or None,
                "price_change_percentage_24h": self._to_float(cells[6].get_text()),
            })
        logger.info("Scraped %d rows from HTML", len(records))
        return records
