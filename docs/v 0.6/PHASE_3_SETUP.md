Phase 3 — Strategy Manager and Plugins

1) Strategy interface
- Files:
  - `sagetrade/strategy/base.py`
  - `sagetrade/strategy/__init__.py`
- Core pieces:
  - `Decision` dataclass: generic trade decision (side, size_pct, tp/sl, duration, reason).
  - `Strategy` protocol:
    - `initialize(config)`
    - `on_new_signal(signal: CompositeSignal) -> Optional[Decision]`
    - `on_tick(market_state) -> List[Decision]` (currently unused in demos).

2) Built-in strategy plugins (MVP)
- Directory: `sagetrade/strategy/strategies/`
- Strategies:
  - `MomentumScalper` (`momentum_scalper.py`)
    - Follows trend when composite direction is long/short.
    - Uses RSI and volatility regime to filter entries.
  - `MeanReversionScalper` (`mean_reversion_scalper.py`)
    - Trades against extremes (overbought/oversold) based on RSI.
  - `NewsQuickTrade` (`news_quick_trade.py`)
    - Reacts to strong NLP sentiment with sufficient `impact_score`.

3) Strategy registry and selector
- File: `sagetrade/strategy/registry.py`
- Components:
  - `StrategyConfig`: enabled flag, min_confidence, allowed_regimes.
  - `StrategyManager`:
    - Instantiates strategies from `STRATEGY_CLASSES`.
    - Supports env-based toggles:
      - `STRATEGIES_ENABLED=momentum_scalper,news_quick_trade`
      - `STRATEGIES_DISABLED=mean_reversion_scalper`
    - `select_for_signal(signal)` returns appropriate strategies based on:
      - `signal.quant.regime`
      - `signal.confidence`
      - configuration.

4) Demo: from signals to decisions
- Script: `scripts/strategy_demo.py`
- Prerequisites:
  - Market data:
    - `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
  - RSS news:
    - `python scripts/ingest_rss_demo.py --publish --store`
- Run:
  - `python scripts/strategy_demo.py`
- Output:
  - Prints the composite signal.
  - Lists active strategies for that signal.
  - Shows each strategy's decision (or that it skips trading).

5) Enabling / disabling strategies
- Use environment variables before running any strategy-related script:
  - Enable only momentum + news:
    - On PowerShell:
      - `$env:STRATEGIES_ENABLED="momentum_scalper,news_quick_trade"`
  - Disable mean-reversion:
    - `$env:STRATEGIES_DISABLED="mean_reversion_scalper"`
- If `STRATEGIES_ENABLED` is set, only strategies listed there are considered.
- If `STRATEGIES_DISABLED` is set, those strategies are skipped even if enabled by default.

6) Next steps (beyond Phase 3)
- Connect `Decision` objects to:
  - Position sizing and risk manager (Phase 4).
  - Execution engine and order manager (Phase 4).
- Implement a simple paper-trading loop:
  - Subscribe to `market.bars` and `news.rss`.
  - Build `CompositeSignal` in near-real-time.
  - Feed signals into `StrategyManager` and log hypothetical trades for backtesting.

