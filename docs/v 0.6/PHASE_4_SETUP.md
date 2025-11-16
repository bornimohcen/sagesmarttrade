Phase 4 — Execution Engine & Risk Manager

Goal
- Safely turn strategy decisions into executable orders, while enforcing strict risk limits.

1) Execution models and paper broker
- Files:
  - `sagetrade/execution/models.py`
    - `Order`: basic order lifecycle (created, filled, etc.).
    - `Position`: open trade with entry price, TP/SL, and realized PnL on close.
    - `AccountState`: balance, equity, realized PnL, open positions.
  - `sagetrade/execution/paper_broker.py`
    - `PaperBrokerConfig`: commission and slippage percentages.
    - `PaperBroker`:
      - Holds an in-memory `AccountState`.
      - `execute_decision(decision, price)`:
        - Computes notional from `equity * size_pct`.
        - Creates a market `Order`.
        - Fills immediately at `price +/- slippage`.
        - Applies commission to balance and realized PnL.
        - Opens a `Position` with TP/SL price levels.

2) Risk Manager
- Files:
  - `sagetrade/risk/manager.py`
- Components:
  - `RiskConfig`:
    - `initial_equity`
    - `max_open_trades`
    - `max_exposure_pct` (total open notional vs equity)
    - `per_symbol_max_trades`
    - `max_trade_risk_pct` (per-trade notional vs equity)
    - `max_daily_loss_pct` (circuit breaker)
  - `RiskState`:
    - Tracks equity start, current equity, realized PnL, open trades, and per-symbol exposure.
  - `RiskManager`:
    - `can_open(decision, price) -> (bool, reason)`:
      - Checks trade notional vs `max_trade_risk_pct`.
      - Enforces `max_open_trades`, `per_symbol_max_trades`, `max_exposure_pct`.
      - Blocks trades when `max_daily_loss_pct` is breached.
    - `on_open(decision, price)`: updates exposure and open trade count.
    - `on_close(symbol, notional, pnl)`: updates PnL, equity, and exposure.

3) Demo: from composite signal to orders (paper trading)
- Script: `scripts/paper_trade_demo.py`
- Prerequisites:
  - Market data:
    - `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
  - RSS news:
    - `python scripts/ingest_rss_demo.py --publish --store`
- Run:
  - `python scripts/paper_trade_demo.py`
- Flow:
  - Loads last day of `BTCUSD` market data and RSS text.
  - Builds `QuantSignals`, `NLPSignals`, and a `CompositeSignal`.
  - Instantiates:
    - `StrategyManager`
    - `RiskManager`
    - `PaperBroker`
  - For each active strategy:
    - Gets a `Decision` via `on_new_signal`.
    - Asks `RiskManager.can_open(...)`.
    - If allowed, passes the decision to `PaperBroker.execute_decision(...)`.
    - Prints created `Order`, `Position`, and final risk/broker summary.

4) Notes and next steps
- The current paper broker:
  - Assumes immediate fills (no explicit timeouts/partial fills yet).
  - Applies simple slippage and commission to approximate live trading costs.
- Risk limits are enforced on trade opening; closing logic and full PnL tracking can be extended in Phase 5 (backtesting framework).
- Before any real integration with a live broker (e.g. Alpaca, Binance, etc.), this layer should be used to:
  - Validate strategy behavior under different risk configs.
  - Tune `size_pct`, TP/SL, and risk limits for micro-trades.

