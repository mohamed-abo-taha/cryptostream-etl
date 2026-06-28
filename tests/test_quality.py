"""Tests for the data-quality framework."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.quality import (
    AllowedValuesCheck, NotNullCheck, QualitySuite, RangeCheck,
    RowCountCheck, UniqueCheck, default_coin_suite,
)

GOOD = [
    {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "price_usd": 61000, "change_24h_pct": 2.4},
    {"coin_id": "ethereum", "symbol": "ETH", "name": "Ethereum", "price_usd": 3380, "change_24h_pct": 1.1},
    {"coin_id": "solana", "symbol": "SOL", "name": "Solana", "price_usd": 142, "change_24h_pct": 5.6},
    {"coin_id": "cardano", "symbol": "ADA", "name": "Cardano", "price_usd": 0.39, "change_24h_pct": -3.4},
    {"coin_id": "tron", "symbol": "TRX", "name": "TRON", "price_usd": 0.12, "change_24h_pct": 0.5},
]


def test_notnull_detects_missing():
    rows = GOOD + [{"coin_id": "", "symbol": "X", "name": "X", "price_usd": 1}]
    res = NotNullCheck(["coin_id"]).run(rows)
    assert not res.passed and res.failed_rows == 1


def test_range_detects_negative_price():
    rows = GOOD + [{"coin_id": "z", "symbol": "Z", "name": "Z", "price_usd": -5}]
    assert RangeCheck("price_usd", min_value=0).run(rows).failed_rows == 1


def test_unique_detects_duplicates():
    rows = GOOD + [GOOD[0]]
    assert UniqueCheck("coin_id").run(rows).failed_rows == 1


def test_allowed_values():
    rows = [{"level": "INFO"}, {"level": "BAD"}]
    assert AllowedValuesCheck("level", ["INFO", "WARN"]).run(rows).failed_rows == 1


def test_rowcount_gate():
    assert RowCountCheck(min_rows=5).run(GOOD).passed
    assert not RowCountCheck(min_rows=10).run(GOOD).passed


def test_suite_passes_clean_batch():
    report = default_coin_suite().run(GOOD)
    assert report.passed
    assert report.to_dict()["passed"] is True


def test_suite_blocks_on_error_severity():
    bad = GOOD + [{"coin_id": "bitcoin", "symbol": "", "name": "", "price_usd": -1}]
    report = default_coin_suite().run(bad)
    assert not report.passed          # unique + notnull + range all fail (error severity)


def test_warning_does_not_block():
    # change_24h_pct out of range is a WARNING, so the batch still passes.
    rows = [dict(r) for r in GOOD]
    rows[0]["change_24h_pct"] = 99999
    suite = QualitySuite([RangeCheck("change_24h_pct", max_value=1000, severity="warning")])
    assert suite.run(rows).passed
