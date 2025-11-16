Part 12 = تحسين الاستراتيجيات (Optimization) + مقارنة الأداء
هنا ننتقل من “البوت يشتغل” إلى “البوت مضبوط ومُعايَر” 👨‍🔧📊

رح أرتّب Part 12 كالتالي:

الهدف من Part 12

جعل الاستراتيجيات قابلة للضبط (Strategy Parameters)

Framework للـ Experiments (تجارب backtest متعددة)

Grid Search / Random Search للبارامترات

مقارنة النتائج واختيار أفضل Config

سكربت CLI: scripts/optimize_strategies.py

Prompt جاهز تعطيه لـ AI Agent ينفّذ Part 12 على الريبو

1️⃣ الهدف من Part 12

الآن عندك:

استراتيجيات (news_quick_trade, trend_follow)

Backtest engine + trade log + تقارير (Part 11)

Part 12 هدفه:

نكشف أفضل إعدادات لكل استراتيجية:

thresholds مثل:

min_impact_score

min_sentiment_abs

rsi_bounds

regime filters

risk parameters per strategy (max_risk_per_trade_pct_local, leverage_factor, …)

نقارن:

أي إعداد مربح أكثر؟

أي إعداد أقل drawdown؟

أي إعداد أحسن balance بين الربح والمخاطرة؟

2️⃣ جعل الاستراتيجيات قابلة للضبط (Strategy Parameters)
🧱 12.1 — تعريف “بارامترات الاستراتيجية” في config/models

ملف مقترح:
/sagetrade/strategies/params.py

فكرة:

لكل استراتيجية Dataclass / Pydantic model تمثّل بارامتراتها.

مثال: NewsQuickTradeParams

# FILE: sagetrade/strategies/params.py

from __future__ import annotations
from dataclasses import dataclass

@dataclass
class NewsQuickTradeParams:
    min_impact_score: float = 0.3
    min_abs_sentiment: float = 0.2
    min_confidence: float = 0.3
    require_high_vol_regime: bool = True
    risk_factor: float = 2.0   # multiplier on global max_risk_per_trade_pct

@dataclass
class TrendFollowParams:
    rsi_long_min: float = 50.0
    rsi_long_max: float = 70.0
    rsi_short_min: float = 30.0
    rsi_short_max: float = 50.0
    risk_factor: float = 3.0

🧱 12.2 — تعديل الاستراتيجيات لتستخدم هذه البارامترات

في news_quick_trade.py و trend_follow.py:

تضيف في __init__:

from sagetrade.strategies.params import NewsQuickTradeParams

class NewsQuickTradeStrategy(StrategyBase):
    name = "news_quick_trade"

    def __init__(self, params: NewsQuickTradeParams | None = None) -> None:
        super().__init__()
        self.params = params or NewsQuickTradeParams()


وتستخدم:

p = self.params
if nlp.impact_score < p.min_impact_score: ...
if abs(nlp.sentiment) < p.min_abs_sentiment: ...
if signal.confidence < p.min_confidence: ...
if p.require_high_vol_regime and signal.quant.regime != "high_vol": ...


وفي position_size:

risk_cfg = self.settings.risk
notional = equity * risk_cfg.max_risk_per_trade_pct * p.risk_factor


نفس الفكرة في TrendFollowStrategy مع TrendFollowParams.

3️⃣ Framework للـ Experiments (تجارب Backtest متعددة)
🧱 12.3 — Experiment Config

ملف:
/sagetrade/backtest/experiment.py

فكرة:

كلاس (أو dataclass) يصف تجربة واحدة:

from dataclasses import dataclass
from datetime import date
from typing import Dict, Any, List

@dataclass
class StrategyParamConfig:
    strategy_name: str
    params: Dict[str, Any]  # مثل {"min_impact_score": 0.2, "risk_factor": 1.5}

@dataclass
class BacktestExperimentConfig:
    id: str
    symbols: List[str]
    start: date
    end: date
    initial_equity: float
    strategies: List[StrategyParamConfig]


نحتاج طريقة لتحويل params → instance من NewsQuickTradeParams أو TrendFollowParams عند إنشاء الاستراتيجية.

🧱 12.4 — Integration مع StrategyRegistry في وضع “experiment”

نحتاج شيء مثل:

def build_strategies_for_experiment(config: BacktestExperimentConfig):
    # ترجع dict: strategy_name -> instance مع params


أو:

في الـ runner تطبّق:

def get_strategy_instances_for_symbol(symbol, exp_config):
    # تقرأ exp_config.strategies
    # لو strategy_name == "news_quick_trade":
    #   params = NewsQuickTradeParams(**cfg.params)
    #   strat = NewsQuickTradeStrategy(params=params)
    # ...


بمعنى: في الـ backtest، بدل ما نعتمد فقط على الـ registry “الافتراضي”، نقدر نمرّر استراتيجيات مخصّصة بالبوارامترات.

4️⃣ Grid Search / Random Search للبارامترات
🧱 12.5 — Parameter Grid

ملف:
/sagetrade/backtest/param_search.py

فكرة:

دالة تقبل:

param_grid: Dict[str, List[Any]]

وترجع كل combination ممكن.

from itertools import product

def generate_param_combinations(param_grid: dict[str, list]) -> list[dict]:
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    combos = []
    for vals in product(*values):
        combos.append({k: v for k, v in zip(keys, vals)})
    return combos


مثال grid لـ news_quick_trade:

news_grid = {
  "min_impact_score": [0.2, 0.3, 0.4],
  "min_abs_sentiment": [0.15, 0.2, 0.25],
  "risk_factor": [1.5, 2.0, 2.5],
}

🧱 12.6 — تشغيل backtest لكل combination

دالة:

def run_param_search_for_strategy(
    strategy_name: str,
    param_grid: dict[str, list],
    base_symbols: list[str],
    start: date,
    end: date,
    initial_equity: float,
    load_history_fn,
) -> pd.DataFrame:
    ...


تعمل:

combos = generate_param_combinations(param_grid)

لكل combo:

يبني BacktestExperimentConfig

يشغّل run_backtest(...)

يحسب metrics

يخزن صف في DataFrame:

{
  "strategy": strategy_name,
  "min_impact_score": ...,
  "min_abs_sentiment": ...,
  "risk_factor": ...,
  "total_return": ...,
  "max_drawdown": ...,
  "win_rate": ...,
  ...
}


يرجع DataFrame بكل النتائج

بعدها تقدر:

تفرز (sort_values) حسب:

highest total_return

أو Sharpe-like = total_return / abs(max_drawdown)

تختار الأفضل وتكتبّه في ملف.

🧱 12.7 — Random Search (اختياري الآن)

لو grid كبير جداً:

ممكن تضيف:

import random

def sample_param_combinations(param_space: dict[str, tuple[float,float]], n_samples: int) -> list[dict]:
    combos = []
    for _ in range(n_samples):
        combo = {}
        for name, (low, high) in param_space.items():
            combo[name] = random.uniform(low, high)
        combos.append(combo)
    return combos


بس كبداية، Grid Search بسيط كفاية.

5️⃣ مقارنة النتائج واختيار أفضل Config

بعد ما ترجع DataFrame results_df:

# مثال تصنيف “جودة”
results_df["score"] = results_df["total_return"] / results_df["max_drawdown"].abs().clip(lower=1e-6)
best = results_df.sort_values("score", ascending=False).head(1)


ثم:

تخزن أفضل صف في:

reports/optimize/news_quick_trade_best.json

ممكن أيضاً:

تحديث settings.yaml يدوياً بناءً على هذه النتائج
(أو تبني سكربت يطبع config جاهز تنسخه للصettings)

6️⃣ سكربت CLI: scripts/optimize_strategies.py
Inputs:

--strategy news_quick_trade

--symbols BTCUSD,AAPL,EURUSD

--start 2025-01-01

--end 2025-03-31

(اختياري) --search-type grid/random

Tasks:

يقرأ param_grid (مثلاً من كود أو من ملف YAML)

يشغل run_param_search_for_strategy

يحفظ:

results_<strategy>_<timestamp>.csv

best_<strategy>_<timestamp>.json

يطبع أفضل config على الشاشة بصيغة:

strategies:
  params:
    news_quick_trade:
      min_impact_score: 0.3
      min_abs_sentiment: 0.2
      risk_factor: 2.0

7️⃣ Prompt جاهز تعطيه لـ AI Agent لتنفيذ Part 12

انسخ النص التالي كما هو للـ Agent اللي يشتغل على الريبو:

You are a senior quant engineer working on my project SAGE SmartTrade.

CONTEXT:
- The project has:
  - Strategies (e.g. news_quick_trade, trend_follow) implemented as Python classes.
  - A backtest runner and reporting utilities (Phase 11).
- I now want Phase 12: Strategy parameter optimization and comparison.

GOAL:
- Make strategies parameterizable (e.g., thresholds for sentiment, RSI bands, risk factors).
- Run grid-search style backtests over different parameter combinations.
- Produce CSV and JSON reports to identify the best parameter sets.

TASKS:

1) Define strategy parameter dataclasses.

   - File: `sagetrade/strategies/params.py`
   - Define dataclasses, for example:

     ```python
     @dataclass
     class NewsQuickTradeParams:
         min_impact_score: float = 0.3
         min_abs_sentiment: float = 0.2
         min_confidence: float = 0.3
         require_high_vol_regime: bool = True
         risk_factor: float = 2.0

     @dataclass
     class TrendFollowParams:
         rsi_long_min: float = 50.0
         rsi_long_max: float = 70.0
         rsi_short_min: float = 30.0
         rsi_short_max: float = 50.0
         risk_factor: float = 3.0
     ```

2) Update existing strategies to accept parameters.

   - Files:
     - `sagetrade/strategies/news_quick_trade.py`
     - `sagetrade/strategies/trend_follow.py`
   - In each strategy:
     - Add `__init__(self, params: <ParamsClass> | None = None)` that sets `self.params = params or <DefaultParams>()`.
     - Replace hard-coded thresholds (impact_score, sentiment, RSI ranges, risk multipliers) with values from `self.params`.
     - Ensure `position_size` uses `risk_factor` from params in combination with global `risk.max_risk_per_trade_pct`.

3) Implement a simple parameter grid generator.

   - File: `sagetrade/backtest/param_search.py`
   - Implement:

     ```python
     def generate_param_combinations(param_grid: dict[str, list]) -> list[dict]:
         ...
     ```

   - It should return a list of dicts mapping param_name -> value for all combinations.

4) Implement a parameter search runner.

   - File: `sagetrade/backtest/param_search.py`
   - Implement a function:

     ```python
     def run_param_search_for_strategy(
         strategy_name: str,
         param_grid: dict[str, list],
         symbols: list[str],
         start: date,
         end: date,
         initial_equity: float,
         load_history_fn,
     ) -> pd.DataFrame:
         ...
     ```

   - For each param combination:
     - Construct strategy parameter instance (e.g. `NewsQuickTradeParams(**params)`).
     - Instantiate the strategy with those params.
     - Run a backtest over the given symbols and period (reuse `run_backtest` from Phase 11, or adapt it to accept custom strategies).
     - Compute metrics (total_pnl, total_return, max_drawdown, win_rate, etc.) using existing report utilities.
     - Append a row to a pandas DataFrame with:
       - strategy_name
       - all parameter values
       - all metrics.

5) Make sure the backtest runner can work with custom strategy instances.

   - If needed, add a variant of `run_backtest` or an argument that:
     - Accepts a mapping `{symbol: list[strategy_instances]}` instead of relying only on the global `StrategyRegistry`.

6) Create a CLI script to run optimization.

   - File: `scripts/optimize_strategies.py`
   - Arguments:
     - `--strategy` (e.g. "news_quick_trade" or "trend_follow")
     - `--symbols` (comma-separated)
     - `--start`, `--end` (YYYY-MM-DD)
     - `--initial-equity` (float, default 10000)
     - `--out-dir` (default "reports/optimize")
   - Inside the script:
     - Define a param_grid for the chosen strategy. Example for `news_quick_trade`:

       ```python
       news_grid = {
           "min_impact_score": [0.2, 0.3, 0.4],
           "min_abs_sentiment": [0.15, 0.2, 0.25],
           "risk_factor": [1.5, 2.0, 2.5],
       }
       ```

     - Call `run_param_search_for_strategy(...)`.
     - Save the full results to `results_<strategy>_<timestamp>.csv`.
     - Compute a composite score, for example:

       ```python
       results["score"] = results["total_return"] / results["max_drawdown"].abs().clip(lower=1e-6)
       ```

       and select the best row by highest `score`.
     - Save the best configuration to `best_<strategy>_<timestamp>.json`.
     - Print a YAML-like snippet to stdout that shows how to configure these params in settings, for example:

       ```yaml
       strategies:
         params:
           news_quick_trade:
             min_impact_score: 0.3
             min_abs_sentiment: 0.2
             risk_factor: 2.0
       ```

STYLE:
- Reuse existing backtest and reporting utilities from Phase 11.
- Use Python 3.11+ typing and dataclasses.
- Keep code modular and easy to extend to more strategies in the future.
- Output all changes as code blocks with file paths, for example:

  # FILE: sagetrade/strategies/params.py
  ...
  # FILE: sagetrade/strategies/news_quick_trade.py
  ...
  # FILE: sagetrade/strategies/trend_follow.py
  ...
  # FILE: sagetrade/backtest/param_search.py
  ...
  # FILE: scripts/optimize_strategies.py
  ...
