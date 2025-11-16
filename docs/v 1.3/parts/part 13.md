Part 13 = إدارة المحفظة (Portfolio) + Walk-Forward Optimization
هنا نطلع من مستوى “صفقة واحدة” إلى مستوى “محفظة كاملة من الأصول والاستراتيجيات”.

رح أرتّب Part 13 كذا:

الهدف من Part 13

Portfolio Model (كيف نوزّع رأس المال بين الأصول والاستراتيجيات)

تطوير RiskManager ليصبح Portfolio-Aware

Portfolio Backtester (اختبار أداء المحفظة، مش استراتيجية واحدة فقط)

Walk-Forward Optimization (تقسيم التاريخ In-Sample / Out-of-Sample)

سكربتات CLI المقترحة

Prompt جاهز تعطيه لـ AI Agent ينفّذ Part 13 في الريبو

1️⃣ الهدف من Part 13

الآن عندك:

استراتيجيات متعددة (news_quick_trade, trend_follow, وغيرها مستقبلاً)

Backtesting + Optimization على مستوى استراتيجية واحدة (Part 11–12)

في Part 13 نريد:

Portfolio-level control:

كم رأس المال يروح لكل:

أصل (symbol)

استراتيجية (strategy)

حدود مثل:

max % per symbol

max % per asset_class (equities / crypto / forex)

max % per strategy

Walk-forward optimization:

تقسيم التاريخ إلى:

فترة تدريب (In-Sample) → نضبط البارامترات

فترة اختبار (Out-of-Sample) → نختبر بدون لمس الإعدادات

تكرار العملية على نوافذ متحركة (rolling windows)

قياس الأداء الحقيقي بعد التحسين (لمنع overfitting)

2️⃣ Portfolio Model (توزيع رأس المال)
🧱 13.1 — تعريف PortfolioConfig

ملف جديد: sagetrade/portfolio/config.py

نعرّف:

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class SymbolAllocation:
    # نسبة رأس المال المستهدفة لهذا الرمز من إجمالي المحفظة
    target_weight: float              # مثلاً 0.2 = 20%
    max_weight: float = 0.3           # حد أقصى
    max_concurrent_trades: int = 3    # أقصى عدد صفقات مفتوحة على هذا الرمز

@dataclass
class StrategyAllocation:
    # نسبة رأس المال المستهدفة لهذه الاستراتيجية
    target_weight: float
    max_weight: float

@dataclass
class AssetClassAllocation:
    target_weight: float
    max_weight: float

@dataclass
class PortfolioConfig:
    symbols: Dict[str, SymbolAllocation] = field(default_factory=dict)
    strategies: Dict[str, StrategyAllocation] = field(default_factory=dict)
    asset_classes: Dict[str, AssetClassAllocation] = field(default_factory=dict)

    max_total_leverage: float = 1.0
    max_positions: int = 50


وتربطه بالـ settings:

portfolio:
  max_total_leverage: 1.5
  max_positions: 30

  symbols:
    BTCUSD:
      target_weight: 0.2
      max_weight: 0.3
      max_concurrent_trades: 5
    AAPL:
      target_weight: 0.2
      max_weight: 0.25

  strategies:
    news_quick_trade:
      target_weight: 0.3
      max_weight: 0.5
    trend_follow:
      target_weight: 0.7
      max_weight: 0.9

  asset_classes:
    crypto:
      target_weight: 0.3
      max_weight: 0.5
    equity:
      target_weight: 0.5
      max_weight: 0.7
    forex:
      target_weight: 0.2
      max_weight: 0.3

3️⃣ تطوير RiskManager ليصبح Portfolio-Aware
🧱 13.2 — PortfolioExposureState

ملف: sagetrade/portfolio/state.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class PortfolioExposure:
    total_notional: float = 0.0
    by_symbol: Dict[str, float] = field(default_factory=dict)
    by_strategy: Dict[str, float] = field(default_factory=dict)
    by_asset_class: Dict[str, float] = field(default_factory=dict)

🧱 13.3 — تحديث RiskManager ليحسب هذه الـ exposures

في RiskManager.refresh_from_broker():

بدل ما يحسب فقط open_notional_by_symbol → نضيف:

by_strategy (من الـ position.strategy_name)

by_asset_class (من universe: symbol -> asset_class مثل equity / crypto / forex)

🧱 13.4 — دالة can_open_trade تأخذ في الاعتبار الـ PortfolioConfig

في RiskManager.can_open_trade(symbol, notional, strategy_name, asset_class):

بالإضافة إلى checks الحالية (max_trade_risk_pct, max_daily_loss, …):

نضيف:

حد عدد الصفقات المفتوحة:

if total_positions >= portfolio_cfg.max_positions:
    return False, "portfolio_max_positions_reached"


وزن الرمز:

current_symbol_notional = exposure.by_symbol.get(symbol, 0.0)
new_symbol_weight = (current_symbol_notional + notional) / equity

cfg_sym = portfolio_cfg.symbols.get(symbol)
if cfg_sym:
    if new_symbol_weight > cfg_sym.max_weight:
        return False, "symbol_max_weight_exceeded"


وزن الاستراتيجية:

current_strat_notional = exposure.by_strategy.get(strategy_name, 0.0)
new_strat_weight = (current_strat_notional + notional) / equity

cfg_str = portfolio_cfg.strategies.get(strategy_name)
if cfg_str:
    if new_strat_weight > cfg_str.max_weight:
        return False, "strategy_max_weight_exceeded"


وزن الـ asset_class (equity / crypto / forex):

current_ac_notional = exposure.by_asset_class.get(asset_class, 0.0)
new_ac_weight = (current_ac_notional + notional) / equity

cfg_ac = portfolio_cfg.asset_classes.get(asset_class)
if cfg_ac:
    if new_ac_weight > cfg_ac.max_weight:
        return False, "asset_class_max_weight_exceeded"


leverage على مستوى المحفظة:

new_total_notional = exposure.total_notional + notional
leverage = new_total_notional / equity
if leverage > portfolio_cfg.max_total_leverage:
    return False, "portfolio_max_leverage_exceeded"


كذا الـ RiskManager يصير “Portfolio-aware” بدون ما تغيّر كثير في الاستراتيجيات نفسها.

4️⃣ Portfolio Backtester

الـ backtest الحالي في Part 11 يشتغل per symbol؛ الآن نريد:

نفس الـ runner لكن مع:

استراتيجيات متعددة

PortfolioConfig

RiskManager محدث

الخطوات:

داخل run_backtest:

نقرأ PortfolioConfig من settings

نمررها للـ RiskManager

عند حساب qty في الاستراتيجية:

الاستراتيجية تقترح qty_raw = strat.position_size(...)

ثم نطبّق scaling حسب التخصيص:

# equity, portfolio_cfg, exposure موجودين
symbol_cfg = portfolio_cfg.symbols.get(symbol)
strategy_cfg = portfolio_cfg.strategies.get(strat.name)

symbol_target_weight = symbol_cfg.target_weight if symbol_cfg else None
strategy_target_weight = strategy_cfg.target_weight if strategy_cfg else None

# مثال بسيط: لو exposure أقل من target_weight نسمح بصفقة كاملة،
# لو قريب من target، نخفّض الحجم.
# كبداية: نقدر نخلي qty_raw كما هو، ونعتمد فقط على can_open_trade لمنع تجاوز max_weight.


كبداية خليه بسيط: الاستراتيجية تحدد الحجم، والـ RiskManager + PortfolioConfig يمنعون الأوفر إكسبوجر. لو حبيت later نضيف “smart scaling”.

5️⃣ Walk-Forward Optimization

هذا أهم جزء علمياً 👇

🧱 13.5 — تعريف WalkForwardSegment & Result

ملف: sagetrade/backtest/walk_forward.py

from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Any

@dataclass
class WalkForwardSegment:
    train_start: date
    train_end: date
    test_start: date
    test_end: date

@dataclass
class WalkForwardResult:
    segments: List[WalkForwardSegment]
    per_segment_metrics: List[Dict[str, Any]]  # metrics لكل segment
    overall_metrics: Dict[str, Any]

🧱 13.6 — بناء segments rolling

مثال:

لديك بيانات من 2024-01-01 إلى 2024-12-31

تريد:

Train 3 أشهر + Test شهر 1

متحرّكة شهر بشهر

دالة:

def build_walk_forward_segments(
    start: date,
    end: date,
    train_months: int,
    test_months: int,
) -> list[WalkForwardSegment]:
    ...


تُنتج segments مثل:

Train: Jan–Mar / Test: Apr

Train: Feb–Apr / Test: May

Train: Mar–May / Test: Jun
…إلخ

🧱 13.7 — تشغيل optimization ثم test لكل segment

Workflow لكل segment:

In-Sample (Train):

تشغّل run_param_search_for_strategy (من Part 12)

تستخرج أفضل params لكل استراتيجية

Out-of-Sample (Test):

تبني استراتيجيات بهذه الـ params

تشغّل run_backtest على فترة test فقط

تخزّن metrics في per_segment_metrics

دالة رئيسية:
def run_walk_forward(
    symbols: list[str],
    start: date,
    end: date,
    initial_equity: float,
    train_months: int,
    test_months: int,
    strategy_param_grids: dict[str, dict[str, list]],
    load_history_fn,
) -> WalkForwardResult:
    """
    strategy_param_grids: مثل:
    {
      "news_quick_trade": {"min_impact_score": [...], "risk_factor": [...]},
      "trend_follow": {...}
    }
    """
    segments = build_walk_forward_segments(start, end, train_months, test_months)
    per_segment_metrics: list[dict[str, Any]] = []

    for seg in segments:
        # 1) optimization على seg.train_start -> seg.train_end
        #   لكل strategy_name في strategy_param_grids
        best_params_per_strategy = {}
        for strat_name, grid in strategy_param_grids.items():
            res_df = run_param_search_for_strategy(
                strat_name,
                grid,
                symbols,
                seg.train_start,
                seg.train_end,
                initial_equity,
                load_history_fn,
            )
            # اختيار أفضل row حسب "score"
            ...

        # 2) backtest على test segment باستعمال best_params_per_strategy
        #   تحتاج runner يقبل strategies مع params
        #   ترجع trades و metrics
        test_trades = run_backtest_with_custom_strategies(...)

        metrics = compute_metrics(test_trades, initial_equity)
        metrics["train_start"] = seg.train_start.isoformat()
        metrics["train_end"] = seg.train_end.isoformat()
        metrics["test_start"] = seg.test_start.isoformat()
        metrics["test_end"] = seg.test_end.isoformat()

        per_segment_metrics.append(metrics)

    # overall metrics: ممكن total PnL + curve على كل الفترات test
    # أو متوسط win_rate & max_drawdown بحساب حسب الحجم
    overall = {...}

    return WalkForwardResult(
        segments=segments,
        per_segment_metrics=per_segment_metrics,
        overall_metrics=overall,
    )


الهدف: يكون عندك performance Out-of-Sample حقيقي بعد كل مرحلة tuning.

6️⃣ سكربتات CLI مقترحة
1) scripts/portfolio_backtest.py

شبيه بـ backtest.py لكن:

يقرأ portfolio.* من settings

يطبع:

exposure per symbol/strategy/asset class

metrics على مستوى المحفظة

2) scripts/walk_forward.py

Args مثال:

python scripts/walk_forward.py \
  --symbols BTCUSD,AAPL,EURUSD \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --train-months 3 \
  --test-months 1


الناتج:

walk_forward_<timestamp>.json فيه:

per segment metrics

overall_metrics

walk_forward_<timestamp>.csv

ربما equity curve لكل test segment

7️⃣ Prompt جاهز لـ AI Agent لتنفيذ Part 13 على الريبو

انسخ هذا الكلام كما هو لوكيل AI اللي يعدّل الكود:

You are a senior quant and portfolio engineer working on my project SAGE SmartTrade.

CONTEXT:
- The project already has:
  - Multiple strategies (e.g. news_quick_trade, trend_follow).
  - A RiskManager and RiskState.
  - Backtest runner + reporting (Phase 11).
  - Parameter optimization for single strategies (Phase 12).

GOAL (Phase 13):
- Introduce portfolio-level controls (capital allocation per symbol, strategy, and asset class).
- Extend RiskManager to be portfolio-aware.
- Add walk-forward optimization (train/test segments) that uses the existing backtest and param-search tools.

TASKS:

1) Portfolio configuration.

   - File: `sagetrade/portfolio/config.py`
   - Define dataclasses:

     ```python
     @dataclass
     class SymbolAllocation:
         target_weight: float
         max_weight: float = 0.3
         max_concurrent_trades: int = 3

     @dataclass
     class StrategyAllocation:
         target_weight: float
         max_weight: float

     @dataclass
     class AssetClassAllocation:
         target_weight: float
         max_weight: float

     @dataclass
     class PortfolioConfig:
         symbols: Dict[str, SymbolAllocation] = field(default_factory=dict)
         strategies: Dict[str, StrategyAllocation] = field(default_factory=dict)
         asset_classes: Dict[str, AssetClassAllocation] = field(default_factory=dict)
         max_total_leverage: float = 1.0
         max_positions: int = 50
     ```

   - Integrate with config/settings.yaml under a new `portfolio` section, e.g.:

     ```yaml
     portfolio:
       max_total_leverage: 1.5
       max_positions: 30
       symbols:
         BTCUSD:
           target_weight: 0.2
           max_weight: 0.3
           max_concurrent_trades: 5
       strategies:
         news_quick_trade:
           target_weight: 0.3
           max_weight: 0.5
       asset_classes:
         crypto:
           target_weight: 0.3
           max_weight: 0.5
     ```

2) Portfolio exposure state and RiskManager integration.

   - File: `sagetrade/portfolio/state.py`
     - Define a `PortfolioExposure` dataclass with:
       - total_notional: float
       - by_symbol: dict[str, float]
       - by_strategy: dict[str, float]
       - by_asset_class: dict[str, float]
   - In `RiskManager.refresh_from_broker()`:
     - Compute and store portfolio exposures:
       - total_notional
       - per symbol
       - per strategy (using position.strategy_name)
       - per asset class (using `universe` mapping symbol → asset_class).
   - Extend `RiskManager.can_open_trade(...)` to accept:
     - `symbol`, `notional`, `strategy_name`, `asset_class`.
   - Within `can_open_trade`, in addition to existing checks:
     - Enforce:
       - portfolio.max_positions
       - per-symbol max_weight
       - per-strategy max_weight
       - per-asset-class max_weight
       - max_total_leverage (total_notional / equity).

3) Make the backtest runner portfolio-aware.

   - In `sagetrade/backtest/runner.py`:
     - Load `PortfolioConfig` from settings.
     - Initialize `RiskManager` with both `RiskState` and `PortfolioConfig` (or make PortfolioConfig accessible).
     - When calling `risk_manager.can_open_trade(...)`, pass `symbol`, `notional`, `strategy_name`, and `asset_class`.
     - Keep strategy-level position sizing logic unchanged for now, but rely on RiskManager+PortfolioConfig to block trades that exceed weights or leverage limits.

4) Walk-forward optimization framework.

   - File: `sagetrade/backtest/walk_forward.py`
   - Define:

     ```python
     @dataclass
     class WalkForwardSegment:
         train_start: date
         train_end: date
         test_start: date
         test_end: date

     @dataclass
     class WalkForwardResult:
         segments: list[WalkForwardSegment]
         per_segment_metrics: list[dict[str, Any]]
         overall_metrics: dict[str, Any]
     ```

   - Implement a helper:

     ```python
     def build_walk_forward_segments(
         start: date,
         end: date,
         train_months: int,
         test_months: int,
     ) -> list[WalkForwardSegment]:
         ...
     ```

     that creates rolling train/test windows (e.g. 3-month train, 1-month test, stepped by test window).

   - Implement:

     ```python
     def run_walk_forward(
         symbols: list[str],
         start: date,
         end: date,
         initial_equity: float,
         train_months: int,
         test_months: int,
         strategy_param_grids: dict[str, dict[str, list]],
         load_history_fn,
     ) -> WalkForwardResult:
         ...
     ```

     For each `WalkForwardSegment`:
       1. TRAIN:
          - For each strategy in `strategy_param_grids`:
            - Call `run_param_search_for_strategy(...)` (from Phase 12) on [train_start, train_end].
            - Select the best param combination based on a score (e.g. total_return / abs(max_drawdown)).
       2. TEST:
          - Build strategy instances with the best params.
          - Run a backtest on [test_start, test_end] using these strategies and the portfolio-aware RiskManager.
          - Compute metrics for the test period and append to `per_segment_metrics`.

     - Compute `overall_metrics` by aggregating all test-period trades (e.g. total PnL, overall win_rate, overall max_drawdown).

5) CLI for walk-forward.

   - File: `scripts/walk_forward.py`
   - Arguments:
     - `--symbols`
     - `--start`, `--end`
     - `--train-months`, `--test-months`
     - `--initial-equity`
     - `--out-dir`
   - Inside:
     - Define `strategy_param_grids` (can be hard-coded for now for strategies like news_quick_trade, trend_follow).
     - Call `run_walk_forward(...)`.
     - Save:
       - `walk_forward_<timestamp>.json` containing:
         - segments
         - per_segment_metrics
         - overall_metrics
       - Optionally `walk_forward_<timestamp>.csv` with per-segment metrics.
     - Print a human-readable summary:
       - overall total_return, max_drawdown, win_rate
       - best and worst segments by performance.

STYLE:
- Reuse existing backtest / param_search / reporting utilities.
- Use Python 3.11+ typing and dataclasses.
- Keep functions modular and separate:
  - portfolio config
  - risk extensions
  - walk-forward logic
  - CLI script.

OUTPUT:
- Provide updated/new files as code blocks, e.g.:

  # FILE: sagetrade/portfolio/config.py
  ...
  # FILE: sagetrade/portfolio/state.py
  ...
  # FILE: sagetrade/risk/manager.py
  ...
  # FILE: sagetrade/backtest/walk_forward.py
  ...
  # FILE: scripts/walk_forward.py
  ...
