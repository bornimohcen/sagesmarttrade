from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Optional

from sagetrade.backtest.simple import BacktestResult, run_single_symbol_backtest
from sagetrade.utils.logging import log_event
from sagetrade.utils.metrics import get_registry


@dataclass
class ExperimentMetrics:
    sharpe: float
    return_pct: float
    max_drawdown_pct: float
    trades: int


@dataclass
class ExperimentReport:
    experiment_id: str
    name: str
    symbol: str
    hypothesis: str
    backtest_range: Optional[str]
    experiment_metrics: ExperimentMetrics
    baseline_metrics: Optional[ExperimentMetrics] = None
    uplift: Dict[str, float] = field(default_factory=dict)
    promotion_recommended: bool = False
    approved: bool = False


class ExperimentManager:
    """Runs backtest-based experiments and produces JSON reports.

    This is a sandbox-only helper; no live trading or auto-merge.
    """

    def __init__(self, output_dir: str = "experiments") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _metrics_from_result(self, result: BacktestResult) -> ExperimentMetrics:
        return ExperimentMetrics(
            sharpe=result.sharpe,
            return_pct=result.return_pct,
            max_drawdown_pct=result.max_drawdown * 100.0,
            trades=len(result.trades),
        )

    def _compare(
        self,
        baseline: Optional[ExperimentMetrics],
        experiment: ExperimentMetrics,
    ) -> Dict[str, float]:
        if baseline is None:
            return {}
        return {
            "sharpe_delta": experiment.sharpe - baseline.sharpe,
            "return_pct_delta": experiment.return_pct - baseline.return_pct,
            "max_drawdown_pct_delta": experiment.max_drawdown_pct - baseline.max_drawdown_pct,
        }

    def _promotion_recommended(
        self,
        uplift: Dict[str, float],
        min_sharpe_increase: float = 0.2,
        min_return_increase: float = 5.0,
    ) -> bool:
        if not uplift:
            return False
        return (
            uplift.get("sharpe_delta", 0.0) >= min_sharpe_increase
            and uplift.get("return_pct_delta", 0.0) >= min_return_increase
        )

    def run_experiment(
        self,
        name: str,
        symbol: str,
        bars: list[dict],
        news_items: list[dict],
        window: int = 20,
        hypothesis: str = "",
        baseline_report_path: Optional[str] = None,
        backtest_range: Optional[str] = None,
    ) -> ExperimentReport:
        """Run a backtest experiment and optionally compare to a baseline report."""
        ts_id = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        experiment_id = f"exp-{ts_id}"

        registry = get_registry()
        registry.counter("experiments_runs_total", "Total number of experiments run").inc()
        log_event(
            "experiment_run_started",
            experiment_id=experiment_id,
            name=name,
            symbol=symbol,
            window=window,
            has_baseline=bool(baseline_report_path),
        )

        result = run_single_symbol_backtest(symbol, bars, news_items, window=window)
        exp_metrics = self._metrics_from_result(result)

        baseline_metrics: Optional[ExperimentMetrics] = None
        if baseline_report_path:
            data = json.loads(Path(baseline_report_path).read_text(encoding="utf-8"))
            bm = data.get("experiment_metrics") or data.get("baseline_metrics")
            if bm:
                baseline_metrics = ExperimentMetrics(
                    sharpe=float(bm.get("sharpe", 0.0)),
                    return_pct=float(bm.get("return_pct", 0.0)),
                    max_drawdown_pct=float(bm.get("max_drawdown_pct", 0.0)),
                    trades=int(bm.get("trades", 0)),
                )

        uplift = self._compare(baseline_metrics, exp_metrics)
        promotion = self._promotion_recommended(uplift)

        report = ExperimentReport(
            experiment_id=experiment_id,
            name=name,
            symbol=symbol,
            hypothesis=hypothesis,
            backtest_range=backtest_range,
            experiment_metrics=exp_metrics,
            baseline_metrics=baseline_metrics,
            uplift=uplift,
            promotion_recommended=promotion,
            approved=False,
        )

        out_path = self.output_dir / f"{experiment_id}.json"
        payload = asdict(report)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        # Also write a generic experiment_report.json for convenience (latest experiment).
        latest_path = self.output_dir / "experiment_report.json"
        latest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        # Metrics and structured log for observability.
        registry.gauge("experiment_last_sharpe", "Sharpe ratio of the last experiment").set(
            float(exp_metrics.sharpe)
        )
        registry.gauge("experiment_last_return_pct", "Return pct of the last experiment").set(
            float(exp_metrics.return_pct)
        )
        registry.gauge("experiment_last_max_drawdown_pct", "Max drawdown pct of the last experiment").set(
            float(exp_metrics.max_drawdown_pct)
        )
        registry.gauge("experiment_last_trades", "Number of trades in the last experiment").set(
            float(exp_metrics.trades)
        )
        if promotion:
            registry.counter(
                "experiments_promotion_recommended_total",
                "Count of experiments where promotion was recommended",
            ).inc()

        log_event(
            "experiment_run_finished",
            experiment_id=experiment_id,
            name=name,
            symbol=symbol,
            sharpe=exp_metrics.sharpe,
            return_pct=exp_metrics.return_pct,
            max_drawdown_pct=exp_metrics.max_drawdown_pct,
            trades=exp_metrics.trades,
            has_baseline=bool(baseline_report_path),
            promotion_recommended=promotion,
        )

        return report
