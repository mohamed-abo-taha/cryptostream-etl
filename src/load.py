"""Loader — persists ``Coin`` objects into a relational SQLite database.

Demonstrates core SQL skills: DDL with constraints and indexes, idempotent
UPSERTs (``ON CONFLICT``) and parameterised queries (no SQL injection).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from .base import Loader
from .models import Coin

logger = logging.getLogger("cryptostream")

SCHEMA = """
CREATE TABLE IF NOT EXISTS coins (
    coin_id         TEXT    PRIMARY KEY,
    symbol          TEXT    NOT NULL,
    name            TEXT    NOT NULL,
    price_usd       REAL    NOT NULL CHECK (price_usd >= 0),
    market_cap      REAL    NOT NULL,
    rank            INTEGER,
    volume_24h      REAL    NOT NULL,
    change_24h_pct  REAL    NOT NULL,
    ingested_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_coins_market_cap ON coins (market_cap DESC);
CREATE INDEX IF NOT EXISTS idx_coins_change     ON coins (change_24h_pct);
"""

UPSERT = """
INSERT INTO coins (
    coin_id, symbol, name, price_usd, market_cap,
    rank, volume_24h, change_24h_pct, ingested_at
) VALUES (
    :coin_id, :symbol, :name, :price_usd, :market_cap,
    :rank, :volume_24h, :change_24h_pct, :ingested_at
)
ON CONFLICT(coin_id) DO UPDATE SET
    symbol         = excluded.symbol,
    name           = excluded.name,
    price_usd      = excluded.price_usd,
    market_cap     = excluded.market_cap,
    rank           = excluded.rank,
    volume_24h     = excluded.volume_24h,
    change_24h_pct = excluded.change_24h_pct,
    ingested_at    = excluded.ingested_at;
"""


class SQLiteLoader(Loader):
    """Create the schema on first use, then UPSERT each batch idempotently."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        logger.info("Schema ready at %s", self.db_path)

    def load(self, coins: Iterable[Coin]) -> int:
        rows = [c.to_row() for c in coins]
        if not rows:
            logger.warning("No rows to load")
            return 0
        with self._connect() as conn:
            conn.executemany(UPSERT, rows)
            conn.commit()
        logger.info("Loaded %d rows into 'coins'", len(rows))
        return len(rows)
