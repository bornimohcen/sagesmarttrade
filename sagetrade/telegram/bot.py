from __future__ import annotations

import glob
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from sagetool.kill_switch import disable as kill_disable
from sagetool.kill_switch import enable as kill_enable
from sagetool.kill_switch import status as kill_status
from sagetrade.risk.manager import RiskConfig
from sagetrade.signals.aggregator import aggregate
from sagetrade.signals.nlp import get_signals as get_nlp_signals
from sagetrade.signals.quant import get_signals_from_bars
from sagetrade.storage.trade_log import load_trades


try:
    import requests  # type: ignore
except Exception as exc:  # pragma: no cover - import guard
    raise ImportError("requests package not installed. `pip install requests`.") from exc


@dataclass
class TelegramBotConfig:
    token: str
    allowed_user_ids: Optional[List[int]] = None
    polling_timeout: int = 30


class TelegramBot:
    """Very small Telegram bot wrapper using long polling.

    - Supports basic commands for the sandbox:
      /start, /help, /status, /portfolio, /open_positions,
      /pause, /resume, /explain <id>, /emergency_stop
    - Authorization is enforced via a list of allowed user IDs.
    """

    def __init__(self, cfg: TelegramBotConfig) -> None:
        self.cfg = cfg
        self.base_url = f"https://api.telegram.org/bot{cfg.token}"
        self._offset: Optional[int] = None

    def _api_call(self, method: str, params: Dict[str, object]) -> Dict[str, object]:
        url = f"{self.base_url}/{method}"
        resp = requests.get(url, params=params, timeout=self.cfg.polling_timeout + 5)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected Telegram response type for {method}")
        return data

    def send_message(self, chat_id: int, text: str) -> None:
        params: Dict[str, object] = {
            "chat_id": chat_id,
            "text": text,
        }
        try:
            self._api_call("sendMessage", params)
        except Exception:
            # In sandbox mode we swallow send errors to keep the bot running.
            pass

    def run_forever(self) -> None:
        """Run a simple long-polling loop."""
        while True:
            try:
                updates = self._api_call(
                    "getUpdates",
                    {
                        "timeout": self.cfg.polling_timeout,
                        "offset": self._offset,
                    },
                )
            except Exception:
                # Back off on network errors.
                time.sleep(5.0)
                continue

            if not updates.get("ok"):
                time.sleep(2.0)
                continue

            results = updates.get("result") or []
            if not isinstance(results, list):
                time.sleep(1.0)
                continue

            for upd in results:
                if not isinstance(upd, dict):
                    continue
                upd_id = upd.get("update_id")
                if isinstance(upd_id, int):
                    self._offset = upd_id + 1
                message = upd.get("message") or upd.get("edited_message")
                if not isinstance(message, dict):
                    continue
                self._handle_message(message)

    # Internal helpers -----------------------------------------------------

    def _handle_message(self, msg: Dict[str, object]) -> None:
        chat = msg.get("chat") or {}
        if not isinstance(chat, dict):
            return
        chat_id = chat.get("id")
        if not isinstance(chat_id, int):
            return

        frm = msg.get("from") or {}
        if not isinstance(frm, dict):
            return
        user_id = frm.get("id")
        if not isinstance(user_id, int):
            return

        text = msg.get("text")
        if not isinstance(text, str):
            return
        text = text.strip()

        if self.cfg.allowed_user_ids and user_id not in self.cfg.allowed_user_ids:
            self.send_message(chat_id, "❌ You are not authorized to use this bot.")
            return

        if text.startswith("/start"):
            self._cmd_start(chat_id)
        elif text.startswith("/help"):
            self._cmd_help(chat_id)
        elif text.startswith("/status"):
            self._cmd_status(chat_id)
        elif text.startswith("/portfolio"):
            self._cmd_portfolio(chat_id)
        elif text.startswith("/open_positions"):
            self._cmd_open_positions(chat_id)
        elif text.startswith("/pause"):
            self._cmd_pause(chat_id)
        elif text.startswith("/resume"):
            self._cmd_resume(chat_id)
        elif text.startswith("/emergency_stop"):
            self._cmd_emergency_stop(chat_id)
        elif text.startswith("/explain"):
            parts = text.split(maxsplit=1)
            trade_id = parts[1].strip() if len(parts) > 1 else ""
            self._cmd_explain(chat_id, trade_id)
        else:
            # Fallback to advisor-style reply (implemented in phase 7.2).
            self._cmd_advisor(chat_id, text)

    # Command implementations ----------------------------------------------

    def _cmd_start(self, chat_id: int) -> None:
        self.send_message(
            chat_id,
            (
                "Hello 👋\n"
                "This is the *SAGE SMART TRADE* sandbox bot.\n"
                "Use /help to list available commands."
            ),
        )

    def _cmd_help(self, chat_id: int) -> None:
        self.send_message(
            chat_id,
            (
                "*Available commands:*\n"
                "/status - system and kill-switch status\n"
                "/portfolio - portfolio summary (sandbox)\n"
                "/open_positions - open positions (if any)\n"
                "/pause - pause trading (enable kill-switch)\n"
                "/resume - resume trading (disable kill-switch)\n"
                "/emergency_stop - immediate emergency stop\n"
                "/explain <trade_id> - explain a trade (placeholder)\n"
                "Any other message is treated as an advisory question (Advisor Mode)."
            ),
        )

    def _cmd_status(self, chat_id: int) -> None:
        ks = kill_status()
        enabled = ks.get("enabled") == "true"
        lines = []
        lines.append(f"Kill-switch: {'ENABLED' if enabled else 'DISABLED'}")
        reason = ks.get("reason")
        if reason:
            lines.append(f"reason={reason}")
        ts = ks.get("enabled_at")
        if ts:
            lines.append(f"enabled_at={ts}")

        exp_summary = self._latest_experiment_summary()
        if exp_summary:
            lines.append("")
            lines.append("*Last experiment:*")
            lines.append(exp_summary)

        self.send_message(chat_id, "\n".join(lines))

    def _cmd_portfolio(self, chat_id: int) -> None:
        account_id = os.environ.get("PAPER_ACCOUNT_ID", "paper-sandbox")
        trades = load_trades(account_id, limit=10)

        total_trades = len(trades)
        total_pnl = sum(float(t.get("pnl", 0.0)) for t in trades)

        lines: List[str] = []
        lines.append(f"📊 Portfolio (sandbox account: {account_id})")
        lines.append(f"- trades_logged: {total_trades}")
        lines.append(f"- sum_realized_pnl: {total_pnl:.4f}")

        if trades:
            lines.append("")
            lines.append("Recent trades:")
            for t in trades[-5:]:
                symbol = t.get("symbol", "")
                side = t.get("side", "")
                pnl = float(t.get("pnl", 0.0))
                pnl_pct = float(t.get("pnl_pct", 0.0))
                ts = t.get("timestamp", "")
                lines.append(f"- {ts} {symbol} {side} pnl={pnl:.4f} ({pnl_pct:.4f}%)")
        else:
            lines.append("")
            lines.append(
                "No trades logged yet. Run paper trading scripts (e.g. `python scripts/paper_trade_demo.py`) "
                "to generate sample trades."
            )

        self.send_message(chat_id, "\n".join(lines))

    def _cmd_open_positions(self, chat_id: int) -> None:
        # In this sandbox implementation, there is no long-lived broker state.
        self.send_message(
            chat_id,
            (
                "📂 *Open positions*:\n"
                "There are no live positions tracked by this bot yet.\n"
                "This environment currently uses paper trading and backtests only."
            ),
        )

    def _cmd_pause(self, chat_id: int) -> None:
        kill_enable("paused via telegram /pause")
        self.send_message(chat_id, "⏸ Kill-switch *ENABLED* (Pause). Trading components should stop opening new trades.")

    def _cmd_resume(self, chat_id: int) -> None:
        kill_disable()
        self.send_message(chat_id, "▶️ Kill-switch *DISABLED* (Resume). Trading in the sandbox may resume.")

    def _cmd_emergency_stop(self, chat_id: int) -> None:
        kill_enable("EMERGENCY_STOP via telegram")
        self.send_message(
            chat_id,
            "🛑 *EMERGENCY STOP*: kill-switch enabled. Stop any live or sandbox processes linked to this environment.",
        )

    def _cmd_explain(self, chat_id: int, trade_id: str) -> None:
        if not trade_id:
            self.send_message(chat_id, "Please provide a trade_id, e.g. `/explain trade-0001`.")
            return
        # Placeholder implementation; detailed trade logs can be wired later.
        self.send_message(
            chat_id,
            (
                f"Preliminary explanation for trade `{trade_id}` (placeholder):\n"
                "- This sandbox version does not yet maintain a full trade log.\n"
                "- Check backtest reports or experiment_report.json for performance details."
            ),
        )

    def _cmd_advisor(self, chat_id: int, text: str) -> None:
        """Advisor-style reply for free-form questions using latest signals."""
        # For now we support BTCUSD كمثال رئيسي.
        symbol = "BTCUSD"
        comp = self._latest_composite_signal(symbol)
        if comp is None:
            self.send_message(
                chat_id,
                (
                    "Cannot provide analysis right now because market/news data "
                    "is not available.\n"
                    "Make sure you have run:\n"
                    "- `python scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`\n"
                    "- `python scripts/ingest_rss_demo.py --publish --store`"
                ),
            )
            return

        if comp.direction == "long":
            dir_text = "Bullish bias (buy signal)"
        elif comp.direction == "short":
            dir_text = "Bearish bias (sell signal)"
        else:
            dir_text = "Neutral / no clear trade"

        risk_cfg = RiskConfig()

        lines: List[str] = []
        lines.append(f"*Sandbox analysis for {symbol}:*")
        lines.append(f"- direction: {dir_text} (`{comp.direction}`)")
        lines.append(f"- score: {comp.score:.4f}")
        lines.append(f"- confidence: {comp.confidence:.2f}")
        lines.append(f"- regime: {comp.quant.regime}")
        lines.append(f"- RSI: {comp.quant.rsi:.2f}")
        lines.append(f"- volatility: {comp.quant.volatility:.4f}")
        lines.append(f"- sentiment: {comp.nlp.sentiment:.3f}")
        lines.append(f"- impact_score: {comp.nlp.impact_score:.3f}")
        lines.append(f"- events: {comp.nlp.event_flags}")

        lines.append("")
        lines.append("*RiskConfig summary:*")
        lines.append(f"- max_trade_risk_pct: {risk_cfg.max_trade_risk_pct:.2f}%")
        lines.append(f"- max_daily_loss_pct: {risk_cfg.max_daily_loss_pct:.2f}%")

        lines.append("")
        lines.append("⚠️ This is experimental sandbox analysis, not investment advice.")
        lines.append(f"Your question was: `{text}`")

        self.send_message(chat_id, "\n".join(lines))

    # Helpers --------------------------------------------------------------

    def _latest_experiment_summary(self) -> str:
        """Return a short summary from experiments/experiment_report.json if it exists."""
        path = os.path.join("experiments", "experiment_report.json")
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return ""

        name = data.get("name") or ""
        symbol = data.get("symbol") or ""
        metrics = data.get("experiment_metrics") or {}
        if not isinstance(metrics, dict):
            metrics = {}
        sharpe = metrics.get("sharpe")
        ret = metrics.get("return_pct")
        dd = metrics.get("max_drawdown_pct")
        trades = metrics.get("trades")

        parts: List[str] = []
        if name:
            parts.append(f"- name: {name}")
        if symbol:
            parts.append(f"- symbol: {symbol}")
        if sharpe is not None:
            parts.append(f"- sharpe: {float(sharpe):.4f}")
        if ret is not None:
            parts.append(f"- return_pct: {float(ret):.2f}%")
        if dd is not None:
            parts.append(f"- max_drawdown_pct: {float(dd):.2f}%")
        if trades is not None:
            parts.append(f"- trades: {int(trades)}")

        return "\n".join(parts)

    def _load_jsonl(self, path: str, limit: int = 0) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
        except FileNotFoundError:
            return []
        if limit > 0:
            return rows[-limit:]
        return rows

    def _latest_composite_signal(self, symbol: str) -> Optional[object]:
        """Compute latest composite signal for given symbol from stored data.

        Uses last day under data/market and data/text similar to the demo scripts.
        """
        market_dirs = sorted(glob.glob(os.path.join("data", "market", "*")))
        text_dirs = sorted(glob.glob(os.path.join("data", "text", "*")))
        if not market_dirs or not text_dirs:
            return None

        m_last = market_dirs[-1]
        t_last = text_dirs[-1]
        market_path = os.path.join(m_last, f"{symbol}.jsonl")
        text_path = os.path.join(t_last, "rss.jsonl")
        if not os.path.exists(market_path) or not os.path.exists(text_path):
            return None

        bars = self._load_jsonl(market_path, limit=200)
        items = self._load_jsonl(text_path, limit=500)
        if not bars or not items:
            return None

        q_sig = get_signals_from_bars(symbol, bars, window=20)
        nlp_sig = get_nlp_signals("market", items)
        return aggregate(symbol, q_sig, nlp_sig)
