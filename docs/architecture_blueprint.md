# SAGE SmartTrade — Architecture Blueprint

## 1. Overview
- **Purpose:** SAGE SmartTrade is an AI‑assisted, event‑driven trading system that ingests market, news, and social data; computes signals; evaluates strategies under strict risk constraints; and routes orders through paper or live brokers.
- **Style:** Modular, testable, and extensible for a solo developer who wants to grow the system from MVP (paper trading) to a richer live‑trading platform with AI and dashboards.
- **Key design goals:**
  - Clear separation of concerns between ingestion, signals, strategies, risk, execution/brokers, AI, and user interfaces.
  - Event‑driven data flow via a simple message queue abstraction (in‑memory or Redis).
  - Plugin‑style extensibility for strategies, brokers, and new data sources.
  - Safety and observability first: strong logging, risk guards, and kill‑switch mechanisms.

Top‑level components are implemented primarily under the `sagetrade/` package and are designed to evolve incrementally as the project matures.

## 2. Top‑Level Modules

### 2.1 Ingestion (`sagetrade.ingestion`)
- **Responsibility:**
  - Connect to external data sources (market, news, social, calendars).
  - Normalize raw data into internal models and publish events to the message bus.
- **Inputs:**
  - External APIs (Alpaca, Binance, RSS feeds, news APIs, social platforms).
  - Local configuration (symbols universe, polling intervals, API keys).
- **Outputs:**
  - Events such as:
    - `market.bar` (normalized OHLCV bars per symbol/timeframe).
    - `news.article` (structured news items).
    - `social.post` (normalized social posts with sentiment metadata when available).
    - `calendar.event` (earnings/macro events).
- **Technologies:**
  - HTTP/REST/WebSocket clients from providers.
  - Internal JSON/JSONL writers for persistence under `data/`.
  - `sagetrade.messaging` as the primary event bus abstraction.

### 2.2 Signals (`sagetrade.signals`)
- **Responsibility:**
  - Transform raw data into trading signals.
  - Provide quantitative indicators, NLP signals, social sentiment, and composite signals.
- **Inputs:**
  - `market.bar` events.
  - `news.article` and `social.post` events.
  - Universe configuration and risk state (when needed for regime detection).
- **Outputs:**
  - `signal.quant` (SMA, EMA, RSI, ATR, Bollinger, volatility, regime, etc.).
  - `signal.news_nlp` (sentiment, event flags, impact scores).
  - `signal.social` (weighted social sentiment).
  - `signal.composite` (final direction, score, confidence, risk flags).
- **Implementation notes:**
  - `sagetrade.signals.quant` for technical indicators.
  - `sagetrade.signals.nlp` for news/social NLP.
  - `sagetrade.signals.aggregator` for CompositeSignal construction.

### 2.3 Strategies (`sagetrade.strategy`)
- **Responsibility:**
  - Encapsulate trading logic as reusable strategies that consume signals and propose trade ideas.
- **Inputs:**
  - `signal.composite` (per symbol/timeframe).
  - Current portfolio/position state and risk snapshot.
  - Optional contextual data (calendar events, volatility regimes, etc.).
- **Outputs:**
  - `strategy.trade_candidate` events representing proposed trades:
    - Side (long/short).
    - Entry type (market/limit).
    - Initial SL/TP suggestions.
    - Position size recommendations (subject to risk manager approval).
- **Implementation notes:**
  - Strategy base and registry under `sagetrade.strategy.base` and `sagetrade.strategy.registry`.
  - Concrete strategies under `sagetrade.strategy.strategies`:
    - `news_quick_trade`, `momentum_scalper`, `mean_reversion_scalper`, etc.
  - Strategies are auto‑discoverable via the registry for plugin‑style loading.

### 2.4 Risk (`sagetrade.risk`)
- **Responsibility:**
  - Enforce global and per‑symbol risk limits.
  - Track exposure and block unsafe trades before they reach the broker.
- **Inputs:**
  - `strategy.trade_candidate` events.
  - Portfolio and exposure state (open positions, realized/unrealized PnL).
  - System configuration for risk (max risk per trade/day, per symbol, correlation rules).
- **Outputs:**
  - `risk.trade_approved` events (trade candidates enriched with final position size and risk metadata).
  - `risk.trade_blocked` events with reasons for rejection.
  - `risk.alert` events (e.g., kill‑switch triggered, limit breaches).
- **Implementation notes:**
  - Core logic in `sagetrade.risk.manager`.
  - Future AI‑assisted risk inspector will live under `sagetrade.ai` (or a dedicated submodule) but integrate via the same interfaces.

### 2.5 Execution & Brokers (`sagetrade.execution`, `sagetrade.brokers`)
- **Responsibility:**
  - Translate approved trades into broker orders.
  - Maintain positions and executions, both in paper and live modes.
- **Inputs:**
  - `risk.trade_approved` events.
  - Broker account state and confirmations.
- **Outputs:**
  - `trade.submitted`, `trade.executed`, `trade.rejected` events.
  - `portfolio.updated` events (positions, cash, PnL).
- **Implementation notes:**
  - Execution layer in `sagetrade.execution` (order models, paper broker, position tracking).
  - Broker metadata and integrations in `sagetrade.brokers` (e.g., Alpaca asset info).
  - Future concrete broker implementations:
    - `BrokerBase` (abstract).
    - `PaperBroker` (simulation).
    - `AlpacaBroker`, `BinanceBroker`, etc.

### 2.6 AI (`sagetrade.ai` — planned, prototypes in `sagetrade.experiment`)
- **Responsibility:**
  - Provide higher‑level AI services:
    - AI‑based signal advisor (direction, confidence, suggested TP/SL).
    - Risk inspector (AI warnings before executing trades).
    - Trade explainer (pre‑ and post‑trade analysis for humans).
- **Inputs:**
  - Quantitative, news, and social signals (and historical context).
  - Recent orders, positions, and PnL.
- **Outputs:**
  - `ai.signal_advice`, `ai.risk_warning`, and human‑readable explanations.
- **Implementation notes:**
  - Initial experiments may live under `sagetrade.experiment`.
  - Stable AI contracts will eventually move into `sagetrade.ai` with well‑defined interfaces to signals, risk, and Telegram.

### 2.7 Telegram (`sagetrade.telegram`)
- **Responsibility:**
  - Provide a chat‑based interface for monitoring and controlling the system.
- **Inputs:**
  - System status, positions, trades, risk alerts, AI explanations.
  - User commands (`/status`, `/positions`, `/kill`, `/resume`, `/explain`, etc.).
- **Outputs:**
  - `telegram.alert` notifications for important events (trade opens/closes, errors).
  - Control events such as `control.kill_switch_activated`, `control.resume_trading`.
- **Implementation notes:**
  - Basic bot under `sagetrade.telegram.bot`.
  - Future extension to support richer commands, inline keyboards, and manual approvals for live trades.

### 2.8 Backtesting (`sagetrade.backtest`)
- **Responsibility:**
  - Run strategies on historical data to evaluate performance, risk, and robustness.
- **Inputs:**
  - Historical market data (bars).
  - Strategy definitions and configuration.
  - Risk parameters.
- **Outputs:**
  - Backtest results: equity curves, trade logs, summary statistics.
  - Metrics for performance and robustness (Sharpe, drawdown, win rate, etc.).
- **Implementation notes:**
  - Current utilities in `sagetrade.backtest.simple`.
  - Future engine to reuse as much of the live pipeline as possible (signals/strategies/risk).

### 2.9 Dashboard (planned)
- **Responsibility:**
  - Web UI for visualizing equity, positions, PnL, logs, and possibly editing safe configuration fields.
- **Inputs:**
  - Aggregated state and metrics from the trading engine.
- **Outputs:**
  - HTTP views/HTML/JSON for human operators.
- **Implementation notes:**
  - Likely implemented as a separate web app (e.g., FastAPI + HTMX or Streamlit) backed by the same data models and logs.

### 2.10 Utils & Infrastructure (`sagetrade.utils`, `sagetrade.messaging`, `sagetrade.config`, `sagetrade.storage`, `sagetrade.replay`)
- **Responsibility:**
  - Cross‑cutting helpers and infrastructure:
    - Configuration loading and validation.
    - Logging and structured JSON logs.
    - Message queue abstraction (in‑memory + optional Redis).
    - Storage utilities (JSONL, parquet, etc.).
    - Replay tools for debugging (feeding past events through the pipeline).
- **Inputs/Outputs:**
  - Used by all other modules; they typically provide services rather than producing business‑level events themselves.

## 3. Data & Event Flow

### 3.1 Market‑to‑Trade Flow
1. **Ingestion → `market.bar` / `news.article` / `social.post`:**
   - Ingestion workers fetch data from external APIs on schedules or streams.
   - Each new bar/article/post is normalized and published to the message bus.
2. **Signals → `signal.quant` / `signal.news_nlp` / `signal.social`:**
   - Signal processors subscribe to relevant topics and maintain rolling windows.
   - They compute technical indicators, news sentiment, social sentiment, and event flags.
3. **CompositeSignal → `signal.composite`:**
   - A composite module combines quant, news, social, and (optionally) AI advice into a single `CompositeSignal` object with:
     - Direction (bullish/bearish/neutral).
     - Confidence score.
     - Risk flags (e.g., earnings soon, high volatility).
4. **Strategies → `strategy.trade_candidate`:**
   - StrategyManager routes `signal.composite` to registered strategies.
   - Each strategy decides whether to enter/exit and constructs a `TradeCandidate`:
     - Symbol, side, entry type, SL/TP, and preliminary size.
   - The candidate is published as `strategy.trade_candidate`.
5. **Risk Manager → `risk.trade_approved` / `risk.trade_blocked`:**
   - RiskManager consumes trade candidates and checks:
     - Max risk per trade.
     - Daily loss / exposure limits.
     - Symbol/correlation constraints.
   - If approved, it finalizes position size and emits `risk.trade_approved`.
   - If blocked, it emits `risk.trade_blocked` with reasons (logged and optionally sent to Telegram).
6. **Execution & Brokers → `trade.executed` / `trade.rejected`:**
   - Execution workers subscribe to `risk.trade_approved` and create actual broker orders.
   - Broker responses (fills, rejects) produce `trade.executed` or `trade.rejected` events and update internal positions.
7. **Portfolio & Notifications → `portfolio.updated` / `telegram.alert`:**
   - Position/portfolio modules update equity and PnL and publish `portfolio.updated`.
   - Telegram and (later) Dashboard subscribe to trade and portfolio events to notify the user and update UIs.

### 3.2 Error & Anomaly Flow
1. **Operational errors (data/API/broker):**
   - Ingestion and broker modules wrap external calls with retries and timeouts.
   - Persistent failures emit `error.ingestion` or `error.broker` events.
2. **Risk and AI anomalies:**
   - RiskManager or AI RiskInspector may emit `risk.alert` or `ai.risk_warning` when conditions look abnormal (e.g., unusually high volatility, conflicting signals, or repeated failures).
3. **Kill‑switch activation:**
   - When hard thresholds are exceeded (max daily loss, repeated broker failures, AI anomaly), a `control.kill_switch_activated` event is emitted.
   - Execution workers immediately stop sending new orders; strategies may still run in “simulation only” mode.
   - Telegram alerts the user with clear instructions.
4. **Recovery:**
   - Monitoring tools or the operator can issue `/resume` via Telegram, which emits `control.resume_trading` after checks.
   - The system gradually ramps back up under stricter temporary limits if desired.

## 4. Interfaces & Contracts

### 4.1 `MarketIngestor` Interface
- **Responsibility:** Unified interface for fetching or streaming market bars.
- **Key methods (conceptual):**
  - `subscribe_bars(symbols, timeframe) -> AsyncIterator[Bar]`
  - `fetch_bars(symbol, timeframe, start, end) -> list[Bar]`
- **Bar model (logical fields):**
  - `symbol`, `time`, `open`, `high`, `low`, `close`, `volume`, `source`.

### 4.2 `NewsIngestor` Interface
- **Responsibility:** Fetch and normalize news articles.
- **Key methods:**
  - `fetch_recent(symbols, since) -> list[NewsArticle]`
  - Optionally `stream_news(topics) -> AsyncIterator[NewsArticle]`
- **NewsArticle fields:**
  - `symbols`, `headline`, `body`, `timestamp`, `source`, `url`.

### 4.3 `SocialIngestor` Interface
- **Responsibility:** Ingest social posts from platforms like X/Twitter, Reddit, Telegram.
- **Key methods:**
  - `fetch_recent(symbols_or_keywords, since) -> list[SocialPost]`
- **SocialPost fields:**
  - `symbol`, `text`, `author`, `engagement`, `timestamp`, `source`, optional pre‑computed sentiment.

### 4.4 `QuantSignals` Interface
- **Responsibility:** Compute technical indicators on bar streams.
- **Key methods:**
  - `compute(symbol, timeframe, bars) -> QuantSignalsResult`
- **QuantSignalsResult fields:**
  - Indicators such as SMA/EMA (multi‑window), RSI, ATR, Bollinger Bands, volatility, trend/regime flags.

### 4.5 `CompositeSignal` Contract
- **Responsibility:** Unified view of all signals for a symbol/timeframe.
- **Fields (logical):**
  - `symbol`, `timeframe`, `timestamp`.
  - `quant` (QuantSignalsResult).
  - `news_nlp` (news sentiment/events).
  - `social` (social sentiment).
  - Optional `ai_advice`.
  - Final `direction`, `score`, `confidence`, `risk_flags`.

### 4.6 `StrategyBase` Interface
- **Responsibility:** Define the minimal contract each strategy must implement.
- **Key methods:**
  - `should_enter(composite_signal, context) -> bool`
  - `should_exit(position, context) -> bool`
  - `compute_position_size(composite_signal, risk_state) -> PositionSizeDecision`
- **Notes:**
  - Strategies are pure logic: no direct I/O or broker calls.
  - They receive all external data via `context` and events.

### 4.7 `RiskManager` Interface
- **Responsibility:** Evaluate trade candidates against risk rules.
- **Key methods:**
  - `evaluate(candidate, portfolio_state) -> RiskDecision`
  - `update_with_fill(fill_event) -> None`
- **RiskDecision:**
  - `approved: bool`
  - `reason: str | None`
  - `final_size` and any modified SL/TP levels.

### 4.8 `BrokerBase` Interface
- **Responsibility:** Abstract broker operations for both paper and live trading.
- **Key methods:**
  - `submit_order(order) -> BrokerOrderId`
  - `cancel_order(order_id) -> None`
  - `get_positions() -> list[Position]`
  - `get_account_summary() -> AccountSummary`
- **Notes:**
  - Concrete implementations: PaperBroker, AlpacaBroker, BinanceBroker, etc.
  - Should implement robust error handling and mapping between internal and external models.

### 4.9 AI Module Interfaces
- **AISignalAdvisor:**
  - `advise(composite_signal, context) -> AISignalAdvice`
  - Returns direction hints, confidence, and suggested TP/SL.
- **AIRiskInspector:**
  - `inspect(candidate, market_context, portfolio_state) -> AIRiskReport`
  - Emits warnings or “do not trade” suggestions.
- **AITradeExplainer:**
  - `explain_before_trade(candidate, composite_signal) -> str`
  - `explain_after_trade(trade_history) -> str`

## 5. Design Patterns & Principles
- **Event‑driven architecture:**
  - Loose coupling via message topics (market, signals, trades, risk, alerts).
  - Individual workers can scale independently or be restarted without global downtime.
- **Strategy pattern:**
  - Strategies encapsulated behind `StrategyBase` and loaded dynamically.
  - Allows adding/removing strategies without touching the core engine.
- **Plugin architecture:**
  - Strategy and broker implementations discovered via registry patterns or filesystem scanning.
  - AI modules and ingestors can also be plugged in behind their interfaces.
- **Separation of concerns / layered design:**
  - Domain logic (signals, strategies, risk) separated from I/O (brokers, APIs, Telegram).
  - Enables easier testing and evolution over time.
- **Dependency inversion:**
  - High‑level modules depend on abstractions (`BrokerBase`, `MarketIngestor`, `StrategyBase`) rather than concrete classes.

## 6. Folder & File Mapping

Planned and existing structure (some modules already present, others to be added/refined):

```text
sagetrade/
  ingestion/
    market_fetcher.py        # MarketIngestor implementations and helpers
    news_social.py           # News & social ingestion utilities
  signals/
    quant.py                 # Quantitative indicators
    nlp.py                   # News/social NLP processing
    aggregator.py            # CompositeSignal builder
  strategy/
    base.py                  # StrategyBase and common context types
    registry.py              # Strategy registration/discovery
    strategies/
      news_quick_trade.py
      momentum_scalper.py
      mean_reversion_scalper.py
  risk/
    manager.py               # RiskManager implementation and risk rules
  execution/
    models.py                # Order/position/account models
    paper_broker.py          # PaperBroker implementation
  brokers/
    alpaca_assets.py         # Broker-specific helpers/metadata (Alpaca)
    # future: base.py, alpaca_broker.py, binance_broker.py
  messaging/
    queue.py                 # Event bus / queue abstraction (in-memory, Redis later)
  backtest/
    simple.py                # Initial backtesting engine
  telegram/
    bot.py                   # Telegram bot integration
  utils/
    ...                      # Logging, time utilities, general helpers
  config/
    ...                      # Config loading/glue for settings files
  storage/
    ...                      # Data writers/readers (e.g., JSONL)
  replay/
    ...                      # Event replay tools for debugging
  experiment/
    ...                      # Experimental/AI prototypes (to evolve into sagetrade.ai)
```

## 7. Extension Points
- **Adding a new strategy:**
  - Create a new file under `sagetrade/strategy/strategies/` defining a class that inherits from `StrategyBase`.
  - Register it in `sagetrade.strategy.registry` (or have the registry auto‑discover based on naming conventions).
  - The new strategy will be available to the StrategyManager via configuration.
- **Adding a new broker:**
  - Implement a class that conforms to `BrokerBase` (e.g., `AlpacaBroker`, `BinanceBroker`).
  - Place it under `sagetrade/execution` or `sagetrade/brokers` depending on the final organization.
  - Wire it into configuration so the trading engine can choose between `PaperBroker` and real brokers.
- **Adding a new data source:**
  - Implement a new ingestor (market, news, or social) that satisfies the corresponding interface.
  - Place it under `sagetrade.ingestion` and connect it to `sagetrade.messaging` topics (e.g., `news.api`, `social.stocktwits`).
- **Adding new AI capabilities:**
  - Implement modules under `sagetrade.ai` (or `experiment` first) that adhere to AI interfaces (advisor, risk inspector, trade explainer).
  - Register them with the components that will consume their output (signals, risk, Telegram).

## 8. Non‑Functional Considerations
- **Performance:**
  - Keep individual workers lightweight and focused on CPU‑bound or I/O‑bound tasks, not both.
  - Use batching where appropriate (e.g., fetching bars for multiple symbols at once).
  - Make the event bus pluggable (in‑memory for local dev, Redis or similar for distributed setups).
- **Resilience:**
  - Implement retry/backoff for all external API calls (brokers, data providers).
  - Use circuit breakers for failing brokers or data sources to avoid cascading failures.
  - Ensure kill‑switch is simple and robust (few dependencies, easy to reason about).
- **Observability:**
  - Structured JSON logging with correlation IDs for trades and positions.
  - Metrics for ingestion rates, signal latency, order latency, error counts.
  - Log summaries and critical alerts pushed to Telegram.
- **Testability:**
  - Heavy use of interfaces and dependency injection to allow mocking of brokers, ingestors, and AI modules.
  - Unit tests for signals and strategies using deterministic data.
  - Integration tests for the event flow (market → signals → strategy → risk → execution) using an in‑memory bus.

## 9. Future Evolution
- **Scaling:**
  - Move from single‑process to multi‑worker or distributed deployments by swapping the event bus and adding process supervision (Docker, systemd, etc.).
  - Support more assets and higher frequencies once performance is validated.
- **Modularization:**
  - Extract independent services (e.g., ingestion, backtesting, dashboard) if needed.
  - Harden the AI layer into a well‑defined module with clear contracts and resource limits.
- **Ecosystem:**
  - Add a web dashboard as a first‑class module.
  - Extend AI capabilities to strategy generation and parameter optimization.
  - Tighten monitoring and alerting for production‑grade reliability.

