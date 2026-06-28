"""Apache Airflow DAG that orchestrates the CryptoStream pipeline.

Instead of running ``run_pipeline.py`` by hand, Airflow runs the stages on a
schedule (hourly here) with automatic retries and dependency ordering:

    extract  ->  transform  ->  quality_gate  ->  load  ->  report

Each task is a small Python callable that reuses the project's own classes —
the DAG is just orchestration glue, the logic lives in ``src/``. Drop this file
in your Airflow ``dags/`` folder (the bundled docker-compose mounts it for you).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Make the project package importable when Airflow loads this DAG file.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from airflow import DAG                       # noqa: E402
from airflow.operators.python import PythonOperator  # noqa: E402

import config                                  # noqa: E402
from src.extract import MockExtractor, RestExtractor  # noqa: E402
from src.load import SQLiteLoader              # noqa: E402
from src.quality import default_coin_suite     # noqa: E402
from src.transform import CoinTransformer       # noqa: E402

default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


def _extract(**ctx):
    """Pull raw records; fall back to the bundled sample if the API is down."""
    try:
        raw = RestExtractor(config.COINGECKO_BASE_URL, config.VS_CURRENCY,
                            config.PER_PAGE).extract()
    except Exception:
        raw = MockExtractor(config.SAMPLE_PATH).extract()
    ctx["ti"].xcom_push(key="raw", value=raw)


def _transform(**ctx):
    raw = ctx["ti"].xcom_pull(key="raw", task_ids="extract")
    coins = CoinTransformer().transform(raw)
    ctx["ti"].xcom_push(key="rows", value=[c.to_row() for c in coins])


def _quality_gate(**ctx):
    rows = ctx["ti"].xcom_pull(key="rows", task_ids="transform")
    report = default_coin_suite().run(rows)
    report.save(config.QUALITY_REPORT_PATH)
    if not report.passed:
        raise ValueError(f"Quality gate failed:\n{report.pretty()}")


def _load(**ctx):
    from src.models import Coin
    rows = ctx["ti"].xcom_pull(key="rows", task_ids="transform")
    coins = [Coin(**r) for r in rows]
    SQLiteLoader(config.DB_PATH).load(coins)


def _report(**ctx):
    from src.analytics import Analytics
    print(Analytics(config.DB_PATH).summary())


with DAG(
    dag_id="cryptostream_etl",
    description="Hourly REST -> SQL ETL with a data-quality gate",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["etl", "crypto", "sql"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=_extract)
    transform = PythonOperator(task_id="transform", python_callable=_transform)
    quality_gate = PythonOperator(task_id="quality_gate", python_callable=_quality_gate)
    load = PythonOperator(task_id="load", python_callable=_load)
    report = PythonOperator(task_id="report", python_callable=_report)

    extract >> transform >> quality_gate >> load >> report
