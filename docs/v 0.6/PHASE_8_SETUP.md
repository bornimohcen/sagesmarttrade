Phase 8 — Hardening, Monitoring & Ops

Goal
- Turn the sandbox into a system with basic observability primitives (metrics + structured logs) that can later be wired to Prometheus/Grafana and ELK, without adding heavy external dependencies.

1) Logging utilities (structured JSON logs)
- File: `sagetrade/utils/logging.py`
- Functions:
  - `log_event(event: str, level: str = "INFO", **fields)`
    - Emits a single JSON line to stdout with fields:
      - `ts`: ISO timestamp (UTC).
      - `level`: log level (e.g. INFO, ERROR).
      - `event`: short event name.
      - Additional keyword fields (e.g. `symbol`, `trades`, `sharpe`).
    - Safely falls back to a minimal text log if JSON printing fails.
  - `log_error(event: str, **fields)`
    - Convenience wrapper that calls `log_event(..., level="ERROR")`.
- Usage patterns:
  - In long-running tasks or critical flows, emit start/finish events:
    - `log_event("backtest_run_started", symbol=symbol, bars=len(bars), window=window)`
    - `log_event("backtest_run_finished", symbol=symbol, trades=len(trades), total_pnl=result.total_pnl, ...)`
  - These logs can later be collected by a log shipper (e.g. Filebeat) into ELK.

2) Metrics utilities (Prometheus-style)
- File: `sagetrade/utils/metrics.py`
- Types:
  - `Counter`:
    - Methods:
      - `inc(amount: float = 1.0)`
  - `Gauge`:
    - Methods:
      - `set(value: float)`
  - `MetricsRegistry`:
    - `counter(name, help="") -> Counter`
    - `gauge(name, help="") -> Gauge`
    - `render_prometheus() -> str`:
      - Returns all metrics in Prometheus text exposition format.
- Globals:
  - `REGISTRY: MetricsRegistry`
  - `get_registry() -> MetricsRegistry`
- Thread safety:
  - Internal `Lock` protects creation and iteration of metrics.

3) Metrics HTTP server
- File: `scripts/metrics_server.py`
- Purpose:
  - Exposes in-process metrics over HTTP for Prometheus or manual inspection.
- Usage:
  - `python scripts/metrics_server.py`
  - Options:
    - `--host 0.0.0.0` (default)
    - `--port 8000` (default)
  - Endpoint:
    - `GET /metrics`
      - Returns output from `get_registry().render_prometheus()` with:
        - `Content-Type: text/plain; version=0.0.4`
- Notes:
  - The HTTP server uses only the Python stdlib (`http.server`).
  - Logging of HTTP requests is suppressed; rely on main app logging.

4) Instrumented flows
- Backtest engine:
  - File: `sagetrade/backtest/simple.py`
  - Function: `run_single_symbol_backtest(...)`
  - Metrics:
    - On each call:
      - `backtest_runs_total` (counter)
    - After completing:
      - `backtest_last_trades` (gauge) — number of trades in last run.
      - `backtest_last_total_pnl` (gauge).
      - `backtest_last_return_pct` (gauge).
      - `backtest_last_max_drawdown` (gauge).
  - Logs:
    - `backtest_run_started`:
      - Fields: `symbol`, `bars`, `window`.
    - `backtest_run_finished`:
      - Fields: `symbol`, `trades`, `total_pnl`, `return_pct`, `max_drawdown`.
- Experiment manager:
  - File: `sagetrade/experiment/manager.py`
  - Method: `ExperimentManager.run_experiment(...)`
  - Metrics:
    - `experiments_runs_total` (counter) — incremented per experiment.
    - `experiment_last_sharpe` (gauge).
    - `experiment_last_return_pct` (gauge).
    - `experiment_last_max_drawdown_pct` (gauge).
    - `experiment_last_trades` (gauge).
    - `experiments_promotion_recommended_total` (counter) — increments when `promotion_recommended` is `True`.
  - Logs:
    - `experiment_run_started`:
      - Fields: `experiment_id`, `name`, `symbol`, `window`, `has_baseline`.
    - `experiment_run_finished`:
      - Fields: `experiment_id`, `name`, `symbol`, `sharpe`, `return_pct`, `max_drawdown_pct`, `trades`, `has_baseline`, `promotion_recommended`.

5) How to use metrics in practice
- Start metrics server:
  - `python scripts/metrics_server.py --port 9000`
- Run experiments/backtests in another terminal:
  - `python scripts/backtest_demo.py`
  - `python scripts/experiment_run.py --name baseline_news_quick_trade --symbol BTCUSD`
- Scrape metrics:
  - Via browser:
    - Open `http://localhost:9000/metrics`
  - Via Prometheus (future):
    - Add a scrape job pointing to the metrics server.

6) How this maps to the original plan
- Observability:
  - Prometheus/Grafana:
    - `scripts/metrics_server.py` + `sagetrade.utils.metrics` give a ready-made endpoint for integration.
  - ELK (logs):
    - `sagetrade.utils.logging.log_event` emits JSON lines suitable for ingestion by log shippers.
- Alerts & On-call:
  - Can be built on top of Prometheus rules using:
    - `backtest_runs_total`, `experiments_runs_total`, and aggregate metrics.
  - Example future rules:
    - Alert if `experiment_last_return_pct` drops below a threshold.
    - Alert if no experiments/backtests ran in a given time window.
- Backup & Rollback:
  - Experiments already persist JSON reports under `experiments/`.
  - These artifacts, combined with logs/metrics, form an auditable history for rollbacks.
- Autoscaling & Infra:
  - Current implementation remains docker-compose friendly.
  - Adding K8s manifests later is straightforward:
    - Expose `scripts/metrics_server.py` as a sidecar or as part of the main container.

7) Safety reminders
- No change to risk limits:
  - Metrics/logging do not modify any `RiskConfig` values.
  - All risk-related decisions remain in `sagetrade.risk.manager`.
- No live trading:
  - This phase keeps everything in sandbox/paper/backtest mode.
  - Any move to a real broker or production infra must still pass through human review as dictated by `AI_POLICY.md`.

