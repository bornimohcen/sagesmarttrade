Phase 1 — Data & Messaging

1) Message broker
- By default, backend = `memory`. To use Redis:
  - Start Redis: `docker-compose up -d redis`
  - Export environment variables:
    - `export MSG_BACKEND=redis`
    - `export MSG_NAMESPACE=sagetrade`
    - `export REDIS_HOST=127.0.0.1`
    - `export REDIS_PORT=6379`

Quick test:
- Consumer: `python3 scripts/queue_demo_consumer.py`
- Producer: `python3 scripts/queue_demo_producer.py`

2) Market ingestion (simulated for now)
- Run simulated candle generator:
  - `python3 scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
- Output:
  - Messages on topic `market.bars`
  - Daily files in `data/market/YYYY-MM-DD/<symbol>.jsonl`

3) RSS / News ingestion
- Run:
  - `python3 scripts/ingest_rss_demo.py --publish --store`
- Output:
  - Messages on topic `news.rss`
  - Daily files in `data/text/YYYY-MM-DD/rss.jsonl`

4) Storage
- Currently stores JSONL files by default.
- If `pyarrow` is installed, the code can be extended to write Parquet for more efficient analytics.

5) Replay Engine
- Replay a full market day from disk into the queue:
  - `python3 -c "from sagetrade.replay.replay_engine import replay_market_day; from sagetrade.messaging.queue import build_queue_from_env; import glob; d=sorted(glob.glob('data/market/*'))[-1]; replay_market_day(d, build_queue_from_env(), 'market.bars', speed=10.0)"`

Acceptance (MVP)
- Able to publish/consume messages through the broker (memory or Redis).
- Market and text data stored in dated directories.
- Replay can republish historical data and be consumed by an example consumer.

Performance notes
- To reach roughly ~100 msgs/s, use `--interval 0.005` with the simulated publisher and Redis backend.
