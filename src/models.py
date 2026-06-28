"""Domain models for the pipeline.

These classes demonstrate OOP fundamentals: encapsulation (the raw API payload
is hidden behind a clean interface), classmethods as alternative constructors,
and behaviour living next to the data it operates on.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class Coin:
    """A single, cleaned cryptocurrency market record.

    The pipeline only ever passes ``Coin`` objects around internally — the messy
    shape of the upstream REST API is normalised away in :meth:`from_api`.
    """

    coin_id: str
    symbol: str
    name: str
    price_usd: float
    market_cap: float
    rank: int | None
    volume_24h: float
    change_24h_pct: float
    ingested_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "Coin":
        """Build a ``Coin`` from a CoinGecko ``/coins/markets`` element.

        Missing or null numeric fields are coerced to ``0.0`` so downstream SQL
        never has to deal with ``NULL`` in numeric columns.
        """

        def num(value: Any) -> float:
            try:
                return float(value) if value is not None else 0.0
            except (TypeError, ValueError):
                return 0.0

        return cls(
            coin_id=str(payload.get("id", "")).strip(),
            symbol=str(payload.get("symbol", "")).strip().upper(),
            name=str(payload.get("name", "")).strip(),
            price_usd=num(payload.get("current_price")),
            market_cap=num(payload.get("market_cap")),
            rank=payload.get("market_cap_rank"),
            volume_24h=num(payload.get("total_volume")),
            change_24h_pct=num(payload.get("price_change_percentage_24h")),
        )

    def is_valid(self) -> bool:
        """A record is only loaded if it has an id and a non-negative price."""
        return bool(self.coin_id) and self.price_usd >= 0

    def to_row(self) -> dict[str, Any]:
        """Flat dict ready to be bound to a parameterised SQL statement."""
        return asdict(self)
