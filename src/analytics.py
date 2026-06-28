"""Analytics layer — answers business questions with pure SQL.

This is the "strong analytical thinking" part of the job spec: rather than
pulling everything into Python and looping, the heavy lifting (ranking,
aggregation, bucketing) is pushed down into SQL where it belongs.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class Analytics:
    """Read-only analytical queries over the ``coins`` table."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def _query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def summary(self) -> dict[str, Any]:
        """Single-row market overview using aggregate functions."""
        sql = """
            SELECT
                COUNT(*)                AS coins_tracked,
                ROUND(SUM(market_cap), 2)  AS total_market_cap,
                ROUND(AVG(price_usd), 2)   AS avg_price_usd,
                ROUND(SUM(volume_24h), 2)  AS total_volume_24h
            FROM coins;
        """
        return self._query(sql)[0]

    def top_gainers(self, limit: int = 5) -> list[dict[str, Any]]:
        """Biggest 24h % gainers — ORDER BY + LIMIT."""
        sql = """
            SELECT symbol, name, price_usd, change_24h_pct
            FROM coins
            ORDER BY change_24h_pct DESC
            LIMIT ?;
        """
        return self._query(sql, (limit,))

    def top_losers(self, limit: int = 5) -> list[dict[str, Any]]:
        sql = """
            SELECT symbol, name, price_usd, change_24h_pct
            FROM coins
            ORDER BY change_24h_pct ASC
            LIMIT ?;
        """
        return self._query(sql, (limit,))

    def market_cap_buckets(self) -> list[dict[str, Any]]:
        """Bucket coins by market-cap tier — CASE expression + GROUP BY."""
        sql = """
            SELECT
                CASE
                    WHEN market_cap >= 1e11 THEN 'mega   (>= $100B)'
                    WHEN market_cap >= 1e10 THEN 'large  ($10B-100B)'
                    WHEN market_cap >= 1e9  THEN 'mid    ($1B-10B)'
                    ELSE                         'small  (< $1B)'
                END AS tier,
                COUNT(*)                  AS coins,
                ROUND(SUM(market_cap), 2) AS tier_market_cap
            FROM coins
            GROUP BY tier
            ORDER BY tier_market_cap DESC;
        """
        return self._query(sql)

    def dominance(self, limit: int = 5) -> list[dict[str, Any]]:
        """Each coin's share of total market cap — window-style subquery."""
        sql = """
            SELECT
                symbol,
                name,
                ROUND(market_cap, 2) AS market_cap,
                ROUND(100.0 * market_cap / (SELECT SUM(market_cap) FROM coins), 2)
                    AS dominance_pct
            FROM coins
            ORDER BY market_cap DESC
            LIMIT ?;
        """
        return self._query(sql, (limit,))
