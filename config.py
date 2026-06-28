"""Central configuration. Values can be overridden with environment variables."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Where the SQLite warehouse lives.
DB_PATH = Path(os.getenv("CRYPTOSTREAM_DB", BASE_DIR / "data" / "cryptostream.db"))

# CoinGecko public API (no key needed).
COINGECKO_BASE_URL = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3")
VS_CURRENCY = os.getenv("VS_CURRENCY", "usd")
PER_PAGE = int(os.getenv("PER_PAGE", "50"))

# Bundled offline sample used when --source mock (or no network).
SAMPLE_PATH = BASE_DIR / "sample_data" / "coins_sample.json"

# Local HTML page scraped when --source scrape.
SCRAPE_HTML_PATH = BASE_DIR / "sample_data" / "partner_prices.html"

# Where the data-quality gate writes its JSON report.
QUALITY_REPORT_PATH = Path(
    os.getenv("QUALITY_REPORT", BASE_DIR / "data" / "quality_report.json")
)

# Flask API.
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "5000"))
