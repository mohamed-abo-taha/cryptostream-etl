"""REST API that serves the warehoused data to other systems.

The pipeline *consumes* a REST API (CoinGecko); this module *exposes* one. That
closes the loop the job description cares about: data flowing between systems
over HTTP/JSON in both directions.

Endpoints
---------
GET /health                 liveness probe
GET /coins?limit=&sort=     list coins (paged / sortable)
GET /coins/<symbol>         single coin by ticker
GET /analytics/summary      market overview
GET /analytics/movers       top gainers and losers
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request

from .analytics import Analytics

ALLOWED_SORTS = {"market_cap", "price_usd", "change_24h_pct", "volume_24h", "rank"}


def create_app(db_path: str | Path) -> Flask:
    """Application factory — keeps the app testable and config-driven."""
    app = Flask(__name__)
    db_path = str(db_path)
    analytics = Analytics(db_path)

    def query(sql: str, params: tuple = ()) -> list[dict]:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/coins")
    def list_coins():
        limit = min(request.args.get("limit", default=20, type=int), 250)
        sort = request.args.get("sort", default="market_cap")
        if sort not in ALLOWED_SORTS:  # whitelist guards against SQL injection
            return jsonify(error=f"invalid sort, choose from {sorted(ALLOWED_SORTS)}"), 400
        rows = query(
            f"SELECT * FROM coins ORDER BY {sort} DESC LIMIT ?", (limit,)
        )
        return jsonify(count=len(rows), results=rows)

    @app.get("/coins/<symbol>")
    def get_coin(symbol: str):
        rows = query("SELECT * FROM coins WHERE symbol = ?", (symbol.upper(),))
        if not rows:
            return jsonify(error="not found"), 404
        return jsonify(rows[0])

    @app.get("/analytics/summary")
    def summary():
        return jsonify(analytics.summary())

    @app.get("/analytics/movers")
    def movers():
        return jsonify(
            gainers=analytics.top_gainers(),
            losers=analytics.top_losers(),
        )

    return app
