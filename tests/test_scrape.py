"""Test the HTML web-scraping extractor against the bundled fixture."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.scrape import HtmlScrapeExtractor
from src.transform import CoinTransformer


def test_scrape_parses_fixture():
    raw = HtmlScrapeExtractor(html_path=config.SCRAPE_HTML_PATH).extract()
    assert len(raw) == 6
    btc = raw[0]
    assert btc["symbol"] == "BTC"
    assert btc["current_price"] == 61250.0
    assert btc["price_change_percentage_24h"] == 2.41


def test_scraped_records_flow_through_transformer():
    raw = HtmlScrapeExtractor(html_path=config.SCRAPE_HTML_PATH).extract()
    coins = CoinTransformer().transform(raw)
    assert len(coins) == 6
    assert all(c.is_valid() for c in coins)
