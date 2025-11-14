SAGE SMART TRADE — Overview

1 — High-level Idea

SAGE SMART TRADE is an automated trading agent composed of several layers:
- Data ingestion (market data, social feeds, news).
- Signal analysis (quantitative indicators + text/sentiment).
- Strategy manager that selects/combines strategies according to market regime and risk budget.
- Execution engine that opens/closes trades with strict risk controls.
- Experimentation and self-improvement layer that runs controlled experiments on new strategies and promotes the best ones under governance.

A Telegram bot acts as the main user interface: it provides forecasts, reports, manual/automatic approval of trades, and explanations of decisions (why a trade was opened or closed).

2 — Core Design Principles

- Capital safety first:
  - Strict per-trade risk, daily loss limits, and automatic shutdown when limits are breached.

- Separation of sandbox vs production:
  - All new strategies and code changes are evaluated via backtests and paper trading before affecting live capital.

- Human approval for critical code changes:
  - The AI agent only generates PRs labeled `ai-proposed`; humans review, run tests, and merge manually.

- Immediate kill-switch:
  - A global kill-switch plus Telegram commands can pause all trading instantly.

- Strong monitoring:
  - PnL, drawdown, Sharpe, win rate, latency, and exposure are monitored and logged.

- Rollback:
  - Every experiment/release is versioned and can be rolled back quickly.

3 — Architecture (Simplified)

- Data Ingestion:
  - Market data (ticks/candles/order book) via providers (real-time + historical).
  - News & Social: RSS feeds, Twitter/X, Reddit, Telegram channels, news APIs.

- Preprocessing & Storage:
  - Normalization, deduplication, time alignment.
  - Data stored as JSONL/Parquet; communication via a message queue (in-memory or Redis; Kafka/RabbitMQ later).

- Signals:
  - Quant indicators (SMA, EMA, RSI, ATR, volatility, regime classification).
  - NLP signals: sentiment, event detection (earnings, M&A, guidance), impact scoring.

- Strategy Manager:
  - Pluggable strategies (momentum scalper, mean-reversion, news-driven, etc.).
  - Policy engine chooses strategies based on regime and risk constraints.

- Execution & Risk:
  - Order manager (market/limit/OCO) with slippage and partial-fill handling.
  - Risk manager for max exposure, per-symbol limits, max intraday drawdown, and circuit breakers.

- Experimentation:
  - Experiment manager runs controlled A/B tests, collects metrics, and proposes PRs for improvements.

- Monitoring & Bot:
  - Metrics via Prometheus/Grafana, logs via ELK.
  - Telegram bot for status, portfolio, explaining trades, pausing/resuming trading.

4 — Current Implementation Status (MVP)

Phase 0 — Prep & Safety
- Secrets management scaffold:
  - `config/secrets.env.example` template (copy to `config/secrets.env`).
  - `.gitignore` excludes `config/secrets.env` and runtime artifacts.
- Governance:
  - `AI_POLICY.md` defines generate-only mode, `ai-proposed` PR label, and human gates.
  - `.github/PULL_REQUEST_TEMPLATE.md` enforces safety and risk review on PRs.
- Kill-switch:
  - `sagetool/kill_switch.py` implements a file-based kill-switch.
  - Scripts:
    - `scripts/emergency_stop.py`
    - `scripts/emergency_resume.py`
    - `scripts/kill_switch_status.py`
- Health checks:
  - `scripts/verify_installation.py` validates presence of secrets without printing them.
  - `scripts/startup_check.py` verifies secrets, account status, and kill-switch before starting.

See `docs/PHASE_0_SETUP.md` for step-by-step usage.

Phase 1 — Data & Messaging
- Messaging:
  - `sagetrade/messaging/queue.py`:
    - `InMemoryQueue` (default).
    - `RedisQueue` (when `MSG_BACKEND=redis`).
  - `docker-compose.yml` provides a Redis service for local testing.
- Storage:
  - `sagetrade/storage/sink.py` for market (`MarketStorage`) and text (`TextStorage`) data.
- Ingestion (MVP):
  - Market simulator:
    - `sagetrade/ingestion/market_fetcher.py` (`SimulatedMarketFetcher`).
    - `scripts/ingest_market_sim_demo.py` publishes to `market.bars` and stores JSONL files under `data/market/YYYY-MM-DD/`.
  - News via RSS:
    - `sagetrade/ingestion/news_social.py` (`RSSIngestor`).
    - `scripts/ingest_rss_demo.py` publishes to `news.rss` and stores JSONL under `data/text/YYYY-MM-DD/`.
- Replay:
  - `sagetrade/replay/replay_engine.py` can replay market days from disk back into the queue.
- Queue demos:
  - `scripts/queue_demo_producer.py`
  - `scripts/queue_demo_consumer.py`

See `docs/PHASE_1_SETUP.md` for examples.

Phase 2 — Signals
- Quant signals:
  - `sagetrade/signals/quant.py`:
    - Indicators: SMA, EMA, RSI, ATR, volatility, and regime classification.
    - `QuantSignals` dataclass and `get_signals_from_bars(...)`.
- NLP signals:
  - `sagetrade/signals/nlp.py`:
    - Simple rule-based sentiment and event detection.
    - `NLPSignals` dataclass and `get_signals(entity, items)`.
- Aggregation:
  - `sagetrade/signals/aggregator.py`:
    - Combines quant + NLP into a `CompositeSignal` (`score`, `direction`, `confidence`).
- Signal demos:
  - `scripts/signals_quant_demo.py`
  - `scripts/signals_nlp_demo.py`
  - `scripts/signals_aggregate_demo.py`

See `docs/PHASE_2_SETUP.md` for how to run these demos.

5 — How to Run the MVP Locally

1) Install Python 3.10+.
2) (Optional) Create a virtualenv and install dependencies (at minimum `redis` if you want Redis backend).
3) Prepare secrets:
   - `cp config/secrets.env.example config/secrets.env`
   - Edit `config/secrets.env` with dummy keys (for now) and keep `ACCOUNT_STATUS=ACTIVE`.
4) Run safety checks:
   - `python scripts/verify_installation.py`
   - `python scripts/startup_check.py`
5) Start Redis (optional):
   - `docker-compose up -d redis`
   - `export MSG_BACKEND=redis`
6) Generate data and signals:
   - Market sim: `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
   - RSS news: `python scripts/ingest_rss_demo.py --publish --store`
   - Quant signals: `python scripts/signals_quant_demo.py --symbol BTCUSD --window 20`
   - NLP signals: `python scripts/signals_nlp_demo.py --entity market`
   - Composite signals: `python scripts/signals_aggregate_demo.py`

From here, the next phases will add: strategy plugins, backtesting, risk manager, real market connectors, and the Telegram bot.

