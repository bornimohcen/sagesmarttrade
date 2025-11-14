Phase 5 — Backtest & Paper Trading

Goal
- Run strategies over historical bars to evaluate PnL and drawdown before any live deployment.

1) Backtest engine (single symbol)
- Files:
  - `sagetrade/backtest/simple.py`
    - `TradeLog`: describes a closed trade (entry/exit, qty, PnL).
    - `BacktestResult`:
      - `equity_curve`: list of `(timestamp, equity)`.
      - Helpers:
        - `total_pnl`
        - `max_drawdown`
    - `run_single_symbol_backtest(symbol, bars, news_items, window=20)`:
      - Sorts bars by timestamp.
      - Builds NLP signals once from `news_items`.
      - For each bar (after warm-up window):
        - Computes quant signals and a composite signal.
        - Sends signals into `StrategyManager`.
        - For each strategy decision:
          - Asks `RiskManager.can_open(...)`.
          - If allowed, executes via `PaperBroker.execute_decision(...)`.
        - Evaluates TP/SL on bar close via `PaperBroker.check_tp_sl(...)`.
        - For each closed position:
          - Calls `RiskManager.on_close(...)`.
          - Appends a `TradeLog`.
        - Records equity into `equity_curve`.

2) Paper broker extensions
- File: `sagetrade/execution/paper_broker.py`
- Additions:
  - `close_position(position_id, price)`:
    - Computes gross PnL based on entry/exit and side.
    - Applies commission on close.
    - Updates account balance, realized PnL, and equity.
    - Returns `(Position, notional)`.
  - `check_tp_sl(prices: Dict[str, float])`:
    - Scans open positions.
    - Closes those where current price hits TP or SL.
    - Returns `{position_id: (closed_position, notional)}` for integration with `RiskManager`.

3) CLI demo: run a backtest
- Script: `scripts/backtest_demo.py`
- Prerequisites:
  - Market data:
    - `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
  - RSS news:
    - `python scripts/ingest_rss_demo.py --publish --store`
- Run:
  - `python scripts/backtest_demo.py`
- Output (example):
  - `Backtest for BTCUSD`
  - `- bars: 1000`
  - `- trades closed: 12`
  - `- total PnL: 15.23`
  - `- max drawdown: 1.85%`

4) Relationship to previous phases
- Reuses:
  - Phase 1 data (market/text JSONL).
  - Phase 2 signals (quant + NLP + composite).
  - Phase 3 strategies and `StrategyManager`.
  - Phase 4 risk limits and `PaperBroker`.
- Provides:
  - A deterministic loop over bars to quickly assess:
    - How often strategies trade.
    - PnL distribution and worst drawdowns.
    - Impact of TP/SL and `size_pct` settings.

5) Next steps
- Extend to:
  - Multiple symbols and time ranges.
  - More detailed metrics (Sharpe, win rate, trade duration, etc.).
  - Configurable backtest runs via config files or CLI parameters.

