# SAGE SmartTrade — System Specification

## 1. Vision & Goals
- **Primary user:** Single independent trader (the project owner) with technical background who wants to codify and automate their own trading process.
- **Style:** Moderate (balanced between capital preservation and growth; no extreme leverage or ultra‑high‑frequency assumptions).
- **Main objectives:**
  - Build an AI‑assisted, partially autonomous trading system for equities, crypto, and (later) major FX pairs.
  - Combine market data, news, and social sentiment into a unified decision layer (CompositeSignal).
  - Start with robust paper trading, then carefully transition to live trading with strict risk controls.
  - Provide a simple but powerful operational interface via CLI and Telegram bot, with a dashboard in later phases.
- **Non‑goals (for the foreseeable future):**
  - No ultra‑HFT or colocation‑style latency games.
  - No complex derivatives (options, futures) in the initial versions.
  - No “black‑box” behavior: decisions should be explainable via logs and AI explanations.

## 2. Supported Assets (Universe)
- **Asset classes (initial target):**
  - US equities (large and mid‑cap).
  - Crypto spot (BTC, ETH, and liquid majors; later top‑N list).
  - FX majors (optional, in later phases).
- **Selection criteria:**
  - Sufficient liquidity and tight spreads.
  - Reasonable historical data availability for backtesting.
  - Stable and reliable data feeds from supported brokers/exchanges.
- **Symbol universe examples:**
  - Equities: S&P 500 constituents plus a curated watchlist.
  - Crypto: BTCUSD, ETHUSD, plus top ~20–50 by market cap.
  - FX: EURUSD, GBPUSD, USDJPY, and other major pairs (later).
- **Fractional trading:** Allowed when supported by the broker (e.g., Alpaca) to better control risk per trade and portfolio sizing.

## 3. Timeframes & Holding Period
- **Operational timeframes:**
  - Intra‑day: 5m, 15m, 1h bars.
  - Swing/position: 4h, 1D bars.
- **Strategy/timeframe mapping (initial intent):**
  - `news_quick_trade`: 5m–15m (intraday, typically flat by end of session).
  - `trend_follow`: 1h–1D (holding from days to weeks).
  - `mean_reversion`: 15m–1h (short‑term swings).
  - `breakout`: 1h–4h.
  - `volatility_scaling`: overlays across timeframes to adjust position size.
- **Holding policies:**
  - Intraday strategies aim to close by session end (for equities).
  - Swing strategies may hold overnight and across days, within defined risk limits.

## 4. Data Sources

### 4.1 Market Data
- **Providers (target):**
  - Alpaca: US equities and some crypto pairs.
  - Binance: Crypto (spot; possibly futures later).
  - Optional later: Polygon.io or other consolidated feeds for improved quality.
- **Bar frequencies:**
  - Minimum: 1m bars for intraday.
  - Aggregated: 5m, 15m, 1h, 4h, 1D.
- **Data features:**
  - OHLCV + timestamp (UTC).
  - Corporate events for equities (splits, dividends) handled via provider where available.
  - Basic sanity checks and validation (non‑negative prices, volume spikes, missing bars).

### 4.2 News
- **Sources:**
  - RSS feeds (e.g., Yahoo Finance, Reuters, Investing, company news feeds).
  - News APIs (e.g., NewsAPI or financial‑focused providers) when available.
- **Usage:**
  - Generate structured articles (symbol(s), headline, body, timestamp, source, link).
  - Feed NLP pipeline for sentiment, event detection (earnings, M&A, guidance, downgrades).
  - Provide human‑readable context in logs and Telegram notifications.

### 4.3 Social Media
- **Sources (planned):**
  - X/Twitter (tracked accounts, lists, or keyword filters).
  - Reddit (subreddits like r/stocks, r/options, r/cryptocurrency, etc.).
  - Telegram public channels focused on markets/crypto.
  - Optionally StockTwits or other sentiment providers.
- **Usage:**
  - Normalize posts into a unified schema: `symbol`, `text`, `author`, `engagement`, `timestamp`, `source`.
  - Compute Social Sentiment Signals with weighting based on engagement and author influence.
  - Act more as a complementary context/risk flag than as a standalone signal at the beginning.

### 4.4 Calendars & Events
- **Earnings calendar:**
  - Upcoming earnings announcements per equity symbol.
  - Flags for pre‑/post‑earnings periods in signals and risk checks.
- **Macro/economic calendar:**
  - Major events: FOMC, CPI, NFP, ECB, etc.
  - Used for risk throttling or “no‑trade windows” around high‑impact events.

## 5. Execution Modes
- **Paper Trading Mode (Phase 1 / MVP):**
  - Uses a `PaperBroker` implementation (simulated fills on market/limit orders).
  - No real money at risk.
  - Full logging of orders, fills, PnL, and risk metrics.
- **Live Trading Mode (later phases):**
  - **Primary broker:** Alpaca (equities and supported crypto).
  - **Secondary target:** Binance for crypto (subject to region/legal constraints).
  - Starts with very small size and strict protections (max risk per trade/day).
- **Automation levels:**
  - Fully automated: System executes trades end‑to‑end based on strategies and risk checks.
  - Semi‑automated: Requires explicit human confirmation (e.g., via Telegram) before placing live orders, especially in early live phases or for high‑risk setups.

## 6. User Interfaces
- **CLI scripts:**
  - Management and debugging (run ingestion demos, backtests, maintenance tasks).
  - Local utilities for developers (you) to inspect data, signals, and logs.
- **Telegram bot (primary operator UI):**
  - Core commands: `/start`, `/help`, `/status`, `/positions`, `/signals`, `/kill`, `/resume`, `/explain`.
  - Receives real‑time alerts for new trades, exits, and critical errors.
  - Optional “manual approval” mode for live trading (e.g., require 👍 before order placement).
- **Web dashboard (later):**
  - Exposes equity curve, open positions, historical PnL, and key risk metrics.
  - Allows read‑only insights initially; configuration editing may be added carefully later.
- **Internal APIs:**
  - Clear interfaces between ingestion, signals, strategies, risk, broker, and AI components, enabling future UI extensions.

## 7. Risk Management Constraints
- **Account‑level constraints (initial targets):**
  - Max risk per trade: ~0.5–1.0% of account equity.
  - Max daily realized loss: ~3% of account equity (triggers kill‑switch).
  - Max total exposure: e.g., 50–70% of account (rest in cash), configurable.
- **Symbol‑level constraints:**
  - Max exposure per symbol: e.g., 10–20% of account equity.
  - Limits on correlated exposure (e.g., multiple tech stocks counted together).
- **Position constraints:**
  - Max number of concurrent open trades: e.g., 5–10 in early versions.
  - Minimum distance for SL/TP relative to volatility (e.g., ATR‑based).
- **Operational constraints:**
  - Trading disabled on severe technical errors (data gaps, broker disconnections).
  - Optional “reduced risk mode” around high‑impact news events.
  - AI‑based risk inspector allowed to veto or downgrade trades when risk flags are high.

## 8. KPIs & Success Metrics
- **Performance metrics:**
  - Sharpe ratio: target >= 1.0–1.5 over a sufficiently long period.
  - Maximum drawdown: target <= 20–25% for a moderately aggressive profile.
  - Monthly return: realistic low‑double‑digit annualized expectations; no “get rich quick” targets.
- **Trade‑level metrics:**
  - Win rate and average R:R (reward:risk) per strategy.
  - Distribution of returns (avoid heavy dependence on a few outlier trades).
  - Holding time statistics and slippage behavior.
- **Stability & robustness:**
  - Uptime of core trading loop and ingestion services.
  - Number of unexpected crashes or forced restarts per month.
  - Quality of data (missing bars, outliers) and resilience to such issues.
- **User‑facing metrics:**
  - Clarity of logs and AI explanations (“why did we enter/exit?”).
  - Latency of alerts and Telegram updates.

## 9. Legal & Ethical Constraints
- Must comply with:
  - Broker Terms of Service (Alpaca, Binance, and any other providers).
  - Local/regional financial regulations applicable to the user.
- No insider trading or use of non‑public material information.
- No deliberate abuse of API rate limits or providers’ acceptable‑use policies.
- Respect privacy and terms of service of social platforms (X/Twitter, Reddit, Telegram, etc.).
- No market manipulation behavior (e.g., spoofing, wash trading).
- Logs and configuration should make it easy to demonstrate system behavior if needed.

## 10. Roadmap Phases (High‑Level)
- **Phase 1: MVP (current focus).**
  - Stable ingestion (simulated + at least one real data source).
  - Core QuantSignals + basic NLP from news.
  - Paper trading loop with logging and risk constraints (no real money).
- **Phase 2: Telegram + more strategies.**
  - Fully functional Telegram bot with monitoring and control commands.
  - StrategyManager with a small set of well‑tested strategies.
  - Simple backtesting engine to validate strategies on historical data.
- **Phase 3: Live trading (limited size).**
  - Connect to Alpaca (and selected crypto exchange).
  - Enable semi‑automated live trading with strict risk and kill‑switch.
  - Improve monitoring, alerts, and operational dashboards.
- **Phase 4: AI self‑improvement + dashboard.**
  - AI‑driven risk inspector and trade explainer.
  - Hyperparameter tuning and strategy refinement using AI assistance and backtests.
  - Web dashboard for visibility into system health, positions, and performance.
- **Phase 5+: Extended ecosystem.**
  - Deeper social sentiment integrations.
  - Auto‑strategy generation experiments with LLMs.
  - More sophisticated optimization, deployment, and monitoring as the system matures.

