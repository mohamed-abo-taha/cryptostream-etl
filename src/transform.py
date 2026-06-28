"""Transformer — cleans raw API dicts into validated ``Coin`` objects."""

from __future__ import annotations

import logging

from .base import Transformer
from .models import Coin

logger = logging.getLogger("cryptostream")


class CoinTransformer(Transformer):
    """Normalise raw records and drop anything that fails validation.

    Responsibilities:
      * map the upstream field names to our clean schema (delegated to
        ``Coin.from_api``),
      * deduplicate by ``coin_id`` (the API occasionally repeats entries),
      * filter out invalid rows so the loader only ever sees good data.
    """

    def transform(self, raw_records: list[dict]) -> list[Coin]:
        seen: set[str] = set()
        cleaned: list[Coin] = []
        dropped = 0

        for record in raw_records:
            coin = Coin.from_api(record)
            if not coin.is_valid():
                dropped += 1
                continue
            if coin.coin_id in seen:
                continue
            seen.add(coin.coin_id)
            cleaned.append(coin)

        logger.info(
            "Transformed %d records (%d kept, %d invalid, %d duplicates)",
            len(raw_records),
            len(cleaned),
            dropped,
            len(raw_records) - len(cleaned) - dropped,
        )
        return cleaned
