"""Extractors — concrete implementations of the ``Extractor`` interface.

Two are provided:

* ``RestExtractor``  — calls the live CoinGecko REST API (no API key required).
* ``MockExtractor``  — replays a bundled JSON sample so the whole pipeline can
  run completely offline (handy for CI, demos and the unit tests).

This is exactly the "data flows between systems via REST APIs" requirement:
System A (CoinGecko) -> HTTP/JSON -> our pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .base import Extractor

logger = logging.getLogger("cryptostream")


class RestExtractor(Extractor):
    """Ingest market data from the CoinGecko public REST API."""

    def __init__(
        self,
        base_url: str,
        vs_currency: str = "usd",
        per_page: int = 50,
        timeout: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.vs_currency = vs_currency
        self.per_page = per_page
        self.timeout = timeout

    def extract(self) -> list[dict]:
        # Imported lazily so the offline/mock path has zero hard dependencies.
        import requests

        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": self.vs_currency,
            "order": "market_cap_desc",
            "per_page": self.per_page,
            "page": 1,
            "price_change_percentage": "24h",
        }
        logger.info("GET %s (per_page=%s)", url, self.per_page)
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        logger.info("Extracted %d raw records from REST API", len(data))
        return data


class MockExtractor(Extractor):
    """Replay a local JSON file — lets the pipeline run with no network."""

    def __init__(self, sample_path: str | Path) -> None:
        self.sample_path = Path(sample_path)

    def extract(self) -> list[dict]:
        logger.info("Loading sample data from %s", self.sample_path)
        with self.sample_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        logger.info("Extracted %d raw records from sample file", len(data))
        return data
