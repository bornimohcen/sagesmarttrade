#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sagetrade.signals.quant import get_signals_from_bars
from sagetrade.signals.nlp import get_signals
from sagetrade.signals.aggregator import aggregate
from sagetrade.strategy.registry import StrategyManager
from sagetrade.execution.paper_broker import PaperBroker
from sagetrade.risk.manager import RiskManager


def load_jsonl(path: str) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple multi-symbol paper trading demo.")
    parser.add_argument(
        "--symbols",
        default="BTCUSD,AAPL,EURUSD",
        help="Comma-separated list of symbols to trade in the sandbox.",
    )
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument(
        "--account-id",
        default="paper-multi",
        help="Paper account id for trade history segregation.",
    )
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise SystemExit("No symbols provided.")

    market_dirs = sorted(glob.glob(os.path.join("data", "market", "*")))
    text_dirs = sorted(glob.glob(os.path.join("data", "text", "*")))
    if not market_dirs or not text_dirs:
        raise SystemExit(
            "Need both market and text data; run ingest_market_sim_demo and ingest_rss_demo first for each symbol."
        )

    m_last = market_dirs[-1]
    t_last = text_dirs[-1]
    text_path = os.path.join(t_last, "rss.jsonl")
    if not os.path.exists(text_path):
        raise SystemExit(f"Missing text file: {text_path}")

    items = load_jsonl(text_path)
    nlp_sig = get_signals("market", items)

    risk = RiskManager()
    broker = PaperBroker(initial_balance=risk.cfg.initial_equity, account_id=args.account_id)
    manager = StrategyManager()

    print(f"Running multi-symbol paper demo for symbols: {symbols}")

    for symbol in symbols:
        market_path = os.path.join(m_last, f"{symbol}.jsonl")
        if not os.path.exists(market_path):
            print(f"[{symbol}] skipping: missing market file {market_path}")
            continue

        bars = load_jsonl(market_path)
        if not bars:
            print(f"[{symbol}] skipping: no bars in {market_path}")
            continue

        current_price = float(bars[-1]["c"])
        q_sig = get_signals_from_bars(symbol, bars, window=args.window)
        comp = aggregate(symbol, q_sig, nlp_sig)

        print(f"[{symbol}] Composite signal:", comp)

        strategies = manager.select_for_signal(comp)
        print(f"[{symbol}] Active strategies:", [s.name for s in strategies])

        for strat in strategies:
            decision = strat.on_new_signal(comp)
            if decision is None:
                print(f"[{symbol}] {strat.name}: no trade decision.")
                continue

            allowed, reason = risk.can_open(decision, current_price)
            if not allowed:
                print(f"[{symbol}] {strat.name}: BLOCKED by risk manager ({reason}).")
                continue

            order, position = broker.execute_decision(decision, current_price)
            risk.on_open(decision, current_price)
            print(f"[{symbol}] {strat.name}: ORDER -> {order}")
            print(f"[{symbol}] {strat.name}: POSITION -> {position}")

            # For demo: immediately close to create realized trades in account history.
            closed, notional = broker.close_position(position.id, current_price)
            risk.on_close(closed.symbol, notional, closed.realized_pnl)
            print(f"[{symbol}] {strat.name}: CLOSED -> {closed}")

    print("Risk state:", risk.state)
    print("Broker summary:", broker.summary())
    print(f"Trades for account_id={args.account_id} are stored under runtime/trades/")


if __name__ == "__main__":
    main()

