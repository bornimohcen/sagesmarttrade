Phase 7 — Telegram Bot & User Interaction (Advisor)

Goal
- Provide a simple Telegram interface for the sandbox: status, basic controls (kill-switch), and advisor-style summaries based on existing signals and experiments.

1) Files and components
- `sagetrade/telegram/bot.py`
  - `TelegramBotConfig`:
    - `token`: bot token from BotFather.
    - `allowed_user_ids`: optional list of allowed Telegram user IDs (ints).
    - `polling_timeout`: long-poll timeout in seconds (default 30).
  - `TelegramBot`:
    - Long-polling loop using the Telegram HTTP API (via `requests`).
    - Authorization via `allowed_user_ids`.
    - Commands:
      - `/start`, `/help`
      - `/status`
      - `/portfolio`
      - `/open_positions`
      - `/pause`
      - `/resume`
      - `/emergency_stop`
      - `/explain <trade_id>`
    - Advisor mode:
      - Any non-command text is treated as an advisory question.
      - Uses latest stored market + RSS data and the existing signal pipeline to answer.
- `scripts/telegram_bot.py`
  - CLI entrypoint to run the bot in sandbox mode.
  - Loads secrets from `config/secrets.env` via `sagetool.env.load_env_file`.
  - Builds `TelegramBotConfig` from environment and starts `TelegramBot.run_forever()`.

2) Prerequisites
- Python 3.10+.
- Install `requests` for the Telegram HTTP client:
  - `pip install requests`
- Configure secrets:
  - Copy example env file:
    - `cp config/secrets.env.example config/secrets.env`
  - Set Telegram-related values:
    - `TELEGRAM_BOT_TOKEN=<your_bot_token>`
    - `TELEGRAM_ALLOWED_USER_IDS=123456789,987654321` (optional, comma-separated list of user IDs).
  - Keep `config/secrets.env` out of version control (already in `.gitignore`).

3) Running the bot
- Start the bot:
  - `python scripts/telegram_bot.py`
  - Optional:
    - `python scripts/telegram_bot.py --polling-timeout 10`
- The bot:
  - Uses long polling against `getUpdates`.
  - Restricts access to `TELEGRAM_ALLOWED_USER_IDS` when provided.
  - Logs start/stop events to stdout only (no external logging service).

4) Commands (MVP)
- `/start`
  - Greets the user and explains that the bot is running in sandbox mode.
- `/help`
  - Lists all supported commands and a short description for each.
- `/status`
  - Uses `sagetool.kill_switch.status()` to show:
    - Whether kill-switch is enabled.
    - Reason and timestamp if available.
  - Attempts to read `experiments/experiment_report.json` and prints:
    - `name`, `symbol`, `sharpe`, `return_pct`, `max_drawdown_pct`, `trades`.
- `/portfolio`
  - Sandbox placeholder:
    - Explains that there is no live portfolio yet.
    - Emphasizes that current system is backtest/paper-only.
- `/open_positions`
  - Sandbox placeholder:
    - Clarifies that no persistent live positions are tracked by this bot.
    - Live brokers/integration can be wired in future phases.
- `/pause`
  - Calls `sagetool.kill_switch.enable("paused via telegram /pause")`.
  - Instructs all components to treat kill-switch as authoritative stop signal.
- `/resume`
  - Calls `sagetool.kill_switch.disable()`.
  - Allows components (that check kill-switch) to resume.
- `/emergency_stop`
  - Calls `sagetool.kill_switch.enable("EMERGENCY_STOP via telegram")`.
  - Communicates this as an urgent kill-switch activation.
- `/explain <trade_id>`
  - Placeholder:
    - Acknowledges the `trade_id`.
    - Informs that full trade logs are not yet wired.
    - Points users to `experiment_report.json` and backtest reports.

5) Advisor mode (NLP + signals)
- Behavior:
  - Any non-command message is treated as an advisory query.
  - For now, analysis is centered on `BTCUSD` using the existing demo data.
- Data sources:
  - Market data:
    - Last day under `data/market/*/BTCUSD.jsonl`.
  - Text/news data:
    - Last day under `data/text/*/rss.jsonl`.
  - Requirements:
    - `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
    - `python scripts/ingest_rss_demo.py --publish --store`
- Signal pipeline:
  - Quant signals:
    - `sagetrade.signals.quant.get_signals_from_bars(symbol, bars, window=20)`
  - NLP signals:
    - `sagetrade.signals.nlp.get_signals("market", items)`
  - Aggregation:
    - `sagetrade.signals.aggregator.aggregate(symbol, q_sig, nlp_sig)`
- Response contents (example):
  - Direction with explanation:
    - `long` → ميل صعودي (إشارة شراء).
    - `short` → ميل هبوطي (إشارة بيع).
    - `flat` → إشارة محايدة.
  - Metrics:
    - `score`, `confidence`, `regime`, `RSI`, `volatility`.
    - `sentiment`, `impact_score`, `event_flags`.
  - Risk snippet:
    - Reads `RiskConfig` from `sagetrade.risk.manager` and reports:
      - `max_trade_risk_pct`
      - `max_daily_loss_pct`
  - Disclaimer:
    - Explicitly states that this is a sandbox-only, non-production, non-investment-advice analysis.

6) Safety & governance integration
- Kill-switch:
  - All critical stop actions funnel through `sagetool.kill_switch`.
  - Other components (strategies, runners, backtests) should check kill-switch before executing trades.
- Secrets:
  - No secrets are printed back to the user.
  - Bot only reads `TELEGRAM_BOT_TOKEN` and user IDs from `config/secrets.env` via `sagetool.env`.
- Audit trail:
  - Bot does not store external logs by default; stdout can be captured by the process supervisor.

7) Next steps (beyond Phase 7 MVP)
- Wire `/portfolio` and `/open_positions` to a persistent broker/account state.
- Add richer `/explain <trade_id>` by reading structured trade logs (e.g., from backtests or live execution).
- Integrate multi-symbol advisor support and allow the user to specify the symbol in natural language.

