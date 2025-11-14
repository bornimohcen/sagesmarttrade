Phase 6 — Experimentation & Self-Improvement (Sandbox)

Goal
- Run controlled experiments on strategy/risk/config changes using backtests, then generate auditable reports that can be attached to AI-proposed PRs.

1) Metrics from backtests
- File: `sagetrade/backtest/simple.py`
- `BacktestResult` now provides:
  - `total_pnl`
  - `return_pct` (PnL / initial equity * 100)
  - `max_drawdown` (fraction, e.g. 0.08 for 8%)
  - `sharpe` (simple Sharpe approximation based on per-step returns)
  - `trades` (count via `len(result.trades)`)

2) Experiment Manager
- Files:
  - `sagetrade/experiment/manager.py`
  - `sagetrade/experiment/__init__.py`
- Data structures:
  - `ExperimentMetrics`:
    - `sharpe`
    - `return_pct`
    - `max_drawdown_pct`
    - `trades`
  - `ExperimentReport`:
    - `experiment_id`: e.g. `exp-20251114-120301`
    - `name`: human-readable experiment name
    - `symbol`
    - `hypothesis`
    - `backtest_range` (optional, string)
    - `experiment_metrics: ExperimentMetrics`
    - `baseline_metrics: Optional[ExperimentMetrics]`
    - `uplift: {sharpe_delta, return_pct_delta, max_drawdown_pct_delta}`
    - `promotion_recommended: bool`
    - `approved: bool` (always False by default; only humans can change this)
- Logic:
  - `ExperimentManager(output_dir="experiments")`:
    - Ensures `experiments/` exists.
    - `_metrics_from_result(result)` converts `BacktestResult` to `ExperimentMetrics`.
    - `_compare(baseline, experiment)` computes deltas.
    - `_promotion_recommended(uplift, min_sharpe_increase=0.2, min_return_increase=5.0)`:
      - Returns True if both Sharpe and return improved by at least these thresholds.
  - `run_experiment(...)`:
    - Runs `run_single_symbol_backtest(...)`.
    - Loads optional baseline report from JSON (via `--baseline` path).
    - Builds `ExperimentReport`.
    - Writes:
      - `experiments/<experiment_id>.json`
      - `experiments/experiment_report.json` (last run).

3) CLI: run an experiment
- Script: `scripts/experiment_run.py`
- Prerequisites:
  - Market + RSS data:
    - `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
    - `python scripts/ingest_rss_demo.py --publish --store`
- Usage examples:
  - First experiment (no baseline yet):
    - `python scripts/experiment_run.py --name baseline_news_quick_trade --symbol BTCUSD`
  - Subsequent experiment compared to baseline:
    - `python scripts/experiment_run.py --name tuned_news_quick_trade --symbol BTCUSD --baseline experiments/exp-YYYYMMDD-HHMMSS.json --hypothesis "increase sharpe by 0.2 with similar drawdown"`
- Output:
  - Prints key metrics and whether `promotion_recommended` is True (when a baseline is provided).
  - Writes detailed `experiment_report.json` under `experiments/`.

4) Promotion policy (recommended, not enforced automatically)
- Suggested thresholds (configurable in code):
  - `sharpe_delta >= 0.2`
  - `return_pct_delta >= 5.0`
  - No hard constraint yet on drawdown, but it is recorded in `max_drawdown_pct_delta`.
- Even when `promotion_recommended = True`:
  - No auto-merge.
  - No auto-deploy.
  - Human review is required (see `AI_POLICY.md` and `.github/PULL_REQUEST_TEMPLATE.md`).

5) Integrating with PRs (manual workflow)
- Typical workflow:
  1) Modify strategy/risk/config code in a branch.
  2) Run `scripts/experiment_run.py` on representative data.
  3) Attach `experiments/experiment_report.json` to the PR.
  4) Fill in PR template (`.github/PULL_REQUEST_TEMPLATE.md`) with:
     - Metrics baseline vs experiment.
     - Canary plan for live testing (1% capital, etc.).
     - Rollback criteria.
  5) Human reviewer uses experiment metrics + code diff to decide whether to approve.

6) Next extensions (future work)
- Add:
  - Multiple-symbol experiments.
  - Config-driven experiments (e.g. JSON/YAML describing parameter sweeps).
  - Automatic grid search for strategy hyperparameters, still gated by human review.

