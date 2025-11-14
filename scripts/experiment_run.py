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

from sagetrade.experiment.manager import ExperimentManager


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
    parser = argparse.ArgumentParser(description="Run backtest experiment and emit experiment_report.json")
    parser.add_argument("--name", required=True, help="Short experiment name, e.g. news_quick_trade_tuned")
    parser.add_argument("--symbol", default="BTCUSD")
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--baseline", help="Path to previous experiment report JSON for comparison")
    parser.add_argument(
        "--hypothesis",
        default="",
        help="Short hypothesis, e.g. 'increase sharpe by 0.2 without worse drawdown'",
    )
    args = parser.parse_args()

    symbol = args.symbol

    market_dirs = sorted(glob.glob(os.path.join("data", "market", "*")))
    text_dirs = sorted(glob.glob(os.path.join("data", "text", "*")))
    if not market_dirs or not text_dirs:
        raise SystemExit(
            "Need both market and text data; run ingest_market_sim_demo and ingest_rss_demo first."
        )

    m_last = market_dirs[-1]
    t_last = text_dirs[-1]

    market_path = os.path.join(m_last, f"{symbol}.jsonl")
    text_path = os.path.join(t_last, "rss.jsonl")
    if not os.path.exists(market_path):
        raise SystemExit(f"Missing market file: {market_path}")
    if not os.path.exists(text_path):
        raise SystemExit(f"Missing text file: {text_path}")

    bars = load_jsonl(market_path)
    items = load_jsonl(text_path)

    mgr = ExperimentManager()
    report = mgr.run_experiment(
        name=args.name,
        symbol=symbol,
        bars=bars,
        news_items=items,
        window=args.window,
        hypothesis=args.hypothesis,
        baseline_report_path=args.baseline,
        backtest_range=None,
    )

    print("Experiment finished.")
    print(f"- experiment_id: {report.experiment_id}")
    print(f"- name: {report.name}")
    print(f"- symbol: {report.symbol}")
    print(f"- sharpe: {report.experiment_metrics.sharpe:.4f}")
    print(f"- return_pct: {report.experiment_metrics.return_pct:.2f}%")
    print(f"- max_drawdown_pct: {report.experiment_metrics.max_drawdown_pct:.2f}%")
    print(f"- trades: {report.experiment_metrics.trades}")
    if report.baseline_metrics:
        print("- uplift:", report.uplift)
        print(f"- promotion_recommended: {report.promotion_recommended}")
    print("Report written to experiments/ (including experiment_report.json).")


if __name__ == "__main__":
    main()

