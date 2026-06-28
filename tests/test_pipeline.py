"""End-to-end test: mock extract -> transform -> load -> analytics, all offline."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.analytics import Analytics
from src.extract import MockExtractor
from src.load import SQLiteLoader
from src.pipeline import Pipeline
from src.transform import CoinTransformer


def test_full_pipeline(tmp_path):
    db = tmp_path / "test.db"
    pipeline = Pipeline(
        extractor=MockExtractor(config.SAMPLE_PATH),
        transformer=CoinTransformer(),
        loader=SQLiteLoader(db),
    )
    result = pipeline.run()

    assert result.extracted == 18      # raw rows in the sample (incl. dup + broken)
    assert result.transformed == 16    # after dedup + validation
    assert result.loaded == 16

    # Idempotency: a second run UPSERTs, it does not duplicate.
    pipeline.run()
    summary = Analytics(db).summary()
    assert summary["coins_tracked"] == 16


def test_analytics_movers(tmp_path):
    db = tmp_path / "test.db"
    Pipeline(MockExtractor(config.SAMPLE_PATH), CoinTransformer(), SQLiteLoader(db)).run()
    gainers = Analytics(db).top_gainers(limit=1)
    assert gainers[0]["symbol"] == "SHIB"   # +11.23% in the sample
