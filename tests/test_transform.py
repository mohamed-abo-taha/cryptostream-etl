"""Unit tests for the transform stage (no network, no DB)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import Coin
from src.transform import CoinTransformer


def test_from_api_normalises_fields():
    raw = {
        "id": "bitcoin", "symbol": "btc", "name": "Bitcoin",
        "current_price": 61000, "market_cap": 1.2e12, "market_cap_rank": 1,
        "total_volume": 2.8e10, "price_change_percentage_24h": 2.4,
    }
    coin = Coin.from_api(raw)
    assert coin.symbol == "BTC"          # upper-cased
    assert coin.price_usd == 61000.0     # coerced to float
    assert coin.is_valid()


def test_from_api_handles_nulls():
    coin = Coin.from_api({"id": "x", "current_price": None, "market_cap": None})
    assert coin.price_usd == 0.0
    assert coin.market_cap == 0.0


def test_transform_drops_invalid_and_dedupes():
    raw = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "current_price": 61000},
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "current_price": 61000},  # dup
        {"id": "", "symbol": "", "name": "", "current_price": None},                     # invalid
    ]
    out = CoinTransformer().transform(raw)
    assert len(out) == 1
    assert out[0].coin_id == "bitcoin"
