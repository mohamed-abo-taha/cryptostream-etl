# Airflow orchestration — CryptoStream

This schedules the ETL so it runs **automatically** (hourly) instead of by hand,
with retries and proper task ordering — the way pipelines run in production.

## The DAG

```
extract  ──►  transform  ──►  quality_gate  ──►  load  ──►  report
(REST API,    (clean,         (block load if    (UPSERT   (log market
 fallback     dedup)           data is bad)      SQLite)   summary)
 to sample)
```

- Defined in [`dags/cryptostream_dag.py`](dags/cryptostream_dag.py).
- Each task is a thin wrapper that **reuses the project's own classes**
  (`RestExtractor`, `CoinTransformer`, `QualitySuite`, `SQLiteLoader`) — Airflow
  only does orchestration, the logic stays in `src/`.
- `retries=2` with a 2-minute delay; `schedule="@hourly"`; `catchup=False`.
- The `quality_gate` task **raises** if the data-quality suite fails, which fails
  the run and stops a bad load — exactly what a quality gate is for.

## Run it

```bash
cd airflow
docker compose -f docker-compose.airflow.yml up
# open http://localhost:8080  (admin / admin)
# enable + trigger the "cryptostream_etl" DAG
```

The compose file mounts the whole project into the container and sets
`PYTHONPATH` so the DAG can import `config` and `src/`.
