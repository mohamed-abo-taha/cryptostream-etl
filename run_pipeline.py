"""CLI entry point: run the ETL pipeline, validate quality, print analytics.

Examples
--------
    python run_pipeline.py --source mock --report        # offline (default)
    python run_pipeline.py --source rest --report        # live CoinGecko API
    python run_pipeline.py --source scrape --report       # HTML web scraping (offline file)
    python run_pipeline.py --source mock --no-quality     # skip the quality gate
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

import config
from src.analytics import Analytics
from src.extract import MockExtractor, RestExtractor
from src.load import SQLiteLoader
from src.quality import default_coin_suite
from src.scrape import HtmlScrapeExtractor
from src.transform import CoinTransformer


def build_extractor(source: str):
    if source == "rest":
        return RestExtractor(config.COINGECKO_BASE_URL, config.VS_CURRENCY, config.PER_PAGE)
    if source == "scrape":
        return HtmlScrapeExtractor(html_path=config.SCRAPE_HTML_PATH)
    return MockExtractor(config.SAMPLE_PATH)


def print_report(db_path) -> None:
    a = Analytics(db_path)
    print("\n================ MARKET ANALYTICS ================")
    print("\n# Summary")
    print(json.dumps(a.summary(), indent=2))
    print("\n# Top 5 gainers (24h)")
    for r in a.top_gainers():
        print(f"  {r['symbol']:<6} {r['change_24h_pct']:+7.2f}%  {r['name']}")
    print("\n# Top 5 losers (24h)")
    for r in a.top_losers():
        print(f"  {r['symbol']:<6} {r['change_24h_pct']:+7.2f}%  {r['name']}")
    print("\n# Market-cap tiers")
    for r in a.market_cap_buckets():
        print(f"  {r['tier']:<20} {r['coins']:>3} coins   ${r['tier_market_cap']:,.0f}")
    print("\n# Dominance (top 5)")
    for r in a.dominance():
        print(f"  {r['symbol']:<6} {r['dominance_pct']:>5.2f}%   {r['name']}")
    print("==================================================\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="CryptoStream ETL pipeline")
    parser.add_argument("--source", choices=["mock", "rest", "scrape"], default="mock")
    parser.add_argument("--report", action="store_true", help="print the analytics report")
    parser.add_argument("--no-quality", action="store_true", help="skip the data-quality gate")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
    )

    # Extract + transform first so the quality gate can inspect the clean batch.
    extractor = build_extractor(args.source)
    transformer = CoinTransformer()
    coins = transformer.transform(extractor.extract())

    if not args.no_quality:
        report = default_coin_suite().run([c.to_row() for c in coins])
        report.save(config.QUALITY_REPORT_PATH)
        print(report.pretty())
        if not report.passed:
            print(f"\nQuality gate FAILED — aborting load. "
                  f"See {config.QUALITY_REPORT_PATH}", file=sys.stderr)
            sys.exit(2)

    loaded = SQLiteLoader(config.DB_PATH).load(coins)
    print(f"\nPipeline OK: transformed={len(coins)} loaded={loaded}  ->  {config.DB_PATH}")

    if args.report:
        print_report(config.DB_PATH)


if __name__ == "__main__":
    main()
