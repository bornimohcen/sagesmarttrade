المرحلة 3: Project Scaffolding (تهيئة المشروع فعليًا) 💻🏗️

الفكرة الآن:

عندك Spec (المرحلة 1) = ماذا نريد أن نبني؟

عندك Architecture Blueprint (المرحلة 2) = كيف مقسّم؟

في المرحلة 3: نحول الكلام هذا إلى كود ومجلدات حقيقية حتى لو كانت فارغة/بسيطة.

رح أعمل لك:

شرح مفصل: ماذا تعني مرحلة Scaffolding هنا؟

تفصيل المرحلة إلى مهام واضحة

شجرة مجلدات مقترحة (ملائمة لمشروعك)

خطة أوامر وملفات يجب إنشاؤها

Prompt قوي تعطيه لـ AI Agent ليكتب معظم الـ scaffolding عنك

🧠 1) ما هي مرحلة Project Scaffolding في مشروعك؟

ببساطة:

“نهيّئ هيكل المشروع بحيث يكون جاهز لإضافة المنطق الحقيقي بدون فوضى.”

يعني في النهاية بعد هذه المرحلة يكون عندك:

مجلدات واضحة لكل Module:

ingestion, signals, strategies, risk, brokers, ai, telegram, backtesting, dashboard, utils

بيئة Python مضبوطة (مثلاً عبر Poetry أو venv عادي)

ملف إعدادات أساسي config/settings.yaml

نظام Logging بسيط جاهز

سكريبتات تشغيل أولية في scripts/

Classes وواجهات (Interfaces) فاضية أو شبه فاضية مكانها جاهز

لسه ما في “ذكاء” حقيقي، بس الهيكل صار جاهز.

🧩 2) تقسيم المرحلة 3 إلى مهام صغيرة
🧱 المهمة 1: إعداد بيئة العمل (Environment & Tools)

هدفها:
كل شيء يُطوّر على أساس بيئة نظيفة ومنظمة.

خطوات مقترحة (ويندوز/بايثون):

تفعيل venv:

python -m venv .venv
.venv\Scripts\activate


إنشاء ملف متطلبات مبدئي:

pip install --upgrade pip
pip install numpy pandas pydantic rich
pip freeze > requirements.txt


لو تحب Poetry بدل هذا: عادي، لكن نركز على المفهوم الآن.

🧱 المهمة 2: إنشاء شجرة المجلدات

في جذر المشروع (عندك أصلًا sagesmarttrade لكن سنرتّب تحته):

اقترح:

sagesmarttrade/
  sagetrade/
    ingestion/
    signals/
    strategies/
    risk/
    brokers/
    ai/
    telegram/
    backtesting/
    dashboard/
    utils/
  scripts/
  config/
  data/
  logs/
  tests/
  docs/


داخل كل مجلد Python نضيف __init__.py حتى يصير Package.

🧱 المهمة 3: إنشاء ملفات Python الأساسية (Skeletons)

لكل Module، ننشئ على الأقل ملف أساسي:

1) ingestion
sagetrade/ingestion/
  __init__.py
  base.py
  market_alpaca.py
  news_rss.py
  social_twitter.py


base.py → تعريف Interfaces:

MarketIngestor

NewsIngestor

SocialIngestor

2) signals
sagetrade/signals/
  __init__.py
  quant.py
  nlp_news.py
  social.py
  composite.py


quant.py → كلاس QuantSignals

nlp_news.py → NLPNewsSignals

social.py → SocialSignals

composite.py → CompositeSignal

3) strategies
sagetrade/strategies/
  __init__.py
  base.py
  news_quick_trade.py
  trend_follow.py


base.py → StrategyBase

4) risk
sagetrade/risk/
  __init__.py
  state.py
  manager.py
  ai_risk.py

5) brokers
sagetrade/brokers/
  __init__.py
  base.py
  paper.py
  alpaca.py

6) ai
sagetrade/ai/
  __init__.py
  signal_advisor.py
  trade_explainer.py
  optimizer.py

7) telegram
sagetrade/telegram/
  __init__.py
  bot.py
  handlers.py

8) backtesting
sagetrade/backtesting/
  __init__.py
  engine.py
  metrics.py

9) dashboard
sagetrade/dashboard/
  __init__.py
  api.py
  ui.py

10) utils
sagetrade/utils/
  __init__.py
  config.py
  logging.py
  time.py

🧱 المهمة 4: إعداد config و logging (بسيط في هذه المرحلة)
ملف إعدادات مبدئي

config/settings.yaml (بسيط الآن، نوسّعه لاحقاً):

app:
  name: "SAGE SmartTrade"
  env: "dev"
  base_currency: "USD"

data:
  base_dir: "data"
  market_dir: "data/market"
  text_dir: "data/text"

risk:
  max_risk_per_trade_pct: 0.005
  max_daily_loss_pct: 0.03
  max_symbol_exposure_pct: 0.2
  max_open_trades: 10

brokers:
  default: "paper"
  alpaca:
    base_url: "https://paper-api.alpaca.markets"
    key_env: "ALPACA_API_KEY"
    secret_env: "ALPACA_API_SECRET"

Config Loader

utils/config.py:

from pathlib import Path
import yaml
from pydantic import BaseModel

class RiskSettings(BaseModel):
    max_risk_per_trade_pct: float = 0.005
    max_daily_loss_pct: float = 0.03
    max_symbol_exposure_pct: float = 0.2
    max_open_trades: int = 10

class AppSettings(BaseModel):
    name: str = "SAGE SmartTrade"
    env: str = "dev"
    base_currency: str = "USD"

class Settings(BaseModel):
    app: AppSettings
    risk: RiskSettings

def load_settings(path: str | Path = "config/settings.yaml") -> Settings:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Settings(**data)

Logging Setup

utils/logging.py:

import logging
from pathlib import Path

def setup_logging(level: int = logging.INFO) -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "sagesmarttrade.log", encoding="utf-8"),
        ],
    )

🧱 المهمة 5: سكريبتات تشغيل أولية في scripts/

نجهز 2–3 سكريبتات بسيطة فقط لبدء التشغيل (حتى لو لا تعمل كل شيء بعد):

scripts/run_paper_loop.py

هدفه مستقبلاً: تشغيل paper trading loop.

scripts/ingest_market_demo.py

يجرب MarketIngestor.

scripts/ingest_news_demo.py

يجرب NewsIngestor.

مثال مبدئي لـ scripts/run_paper_loop.py:

#!/usr/bin/env python
from sagetrade.utils.logging import setup_logging
from sagetrade.utils.config import load_settings

def main() -> None:
    setup_logging()
    settings = load_settings()
    # TODO: هنا لاحقاً سنضيف:
    # - تحميل broker
    # - تحميل strategies
    # - بدء loop
    print(f"Starting SAGE SmartTrade paper loop with base currency {settings.app.base_currency}")

if __name__ == "__main__":
    main()

🧱 المهمة 6: إنشاء واجهات (Interfaces) فارغة/بسيطة

مثلاً:

brokers/base.py:

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Order:
    symbol: str
    side: str  # "buy" / "sell"
    qty: float

class BrokerBase(ABC):
    @abstractmethod
    def submit_order(self, order: Order) -> None:
        ...

    @abstractmethod
    def get_positions(self) -> list:
        ...

    @abstractmethod
    def get_account_summary(self) -> dict:
        ...


strategies/base.py:

from abc import ABC, abstractmethod
from sagetrade.signals.composite import CompositeSignal
from sagetrade.risk.state import RiskState

class StrategyBase(ABC):
    name: str = "base"

    @abstractmethod
    def should_enter(self, signal: CompositeSignal, risk: RiskState) -> bool:
        ...

    @abstractmethod
    def should_exit(self, position, signal: CompositeSignal, risk: RiskState) -> bool:
        ...


risk/state.py:

from dataclasses import dataclass, field

@dataclass
class RiskState:
    equity_start: float
    equity: float
    realized_pnl: float = 0.0
    open_trades: int = 0
    open_notional_by_symbol: dict[str, float] = field(default_factory=dict)


الهدف هنا:
يكون عندك مكان واضح لإضافة المنطق لاحقًا بدون ما تعيد تنظيم المشروع.

🧾 3) ما الذي يجب أن تمتلكه في نهاية المرحلة 3؟

مجلدات المشروع كلها موجودة

__init__.py في كل Package

config/settings.yaml مبدئي

utils/config.py و utils/logging.py

واجهات أساسية:

BrokerBase, StrategyBase, RiskState, CompositeSignal (حتى لو minimal)

سكريبت تشغيل واحد على الأقل في scripts/ يعمل بدون أخطاء

🤖 4) Prompt قوي تعطيه لـ AI Agent لينفّذ مرحلة 3 عنك

هذا Prompt شامل، خذه كوبي بيست:

You are a senior Python backend engineer.

I already have:
- A system specification for my trading system SAGE SmartTrade.
- An architecture blueprint that defines all modules: ingestion, signals, strategies, risk, brokers, ai, telegram, backtesting, dashboard, utils.

Now I want you to implement the PROJECT SCAFFOLDING (phase 3).

TASK:
Generate the initial code scaffolding for the project, assuming the repo root is `sagesmarttrade/`.

1. Create the following folder structure (as Python packages with __init__.py files):

- sagetrade/
    - ingestion/
    - signals/
    - strategies/
    - risk/
    - brokers/
    - ai/
    - telegram/
    - backtesting/
    - dashboard/
    - utils/
- scripts/
- config/
- data/
- logs/
- tests/
- docs/

2. For each module, create minimal Python files with EMPTY or minimal implementations:

- `sagetrade/ingestion/base.py` with abstract base classes:
    - MarketIngestor
    - NewsIngestor
    - SocialIngestor

- `sagetrade/signals/quant.py` with a QuantSignals dataclass and stub compute functions.
- `sagetrade/signals/nlp_news.py` with NLPNewsSignals dataclass.
- `sagetrade/signals/social.py` with SocialSignals dataclass.
- `sagetrade/signals/composite.py` with CompositeSignal dataclass.

- `sagetrade/strategies/base.py` with StrategyBase abstract class.
- `sagetrade/risk/state.py` with RiskState dataclass.
- `sagetrade/risk/manager.py` with a RiskManager class stub.
- `sagetrade/brokers/base.py` with BrokerBase abstract class and a simple Order dataclass.
- `sagetrade/brokers/paper.py` with a minimal PaperBroker implementation (no real logic yet).
- `sagetrade/ai/signal_advisor.py` with a placeholder AISignalAdvisor class.
- `sagetrade/utils/config.py` with a Settings loader using YAML and Pydantic.
- `sagetrade/utils/logging.py` with a basic logging setup (console + file handler).
- `sagetrade/telegram/bot.py` with a placeholder Telegram bot class.
- `sagetrade/backtesting/engine.py` with a BacktestEngine stub.
- `sagetrade/dashboard/api.py` with a placeholder FastAPI app stub.

3. Create a basic `config/settings.yaml` file with:
- app name, env
- basic risk configuration
- basic broker configuration (paper + alpaca).

4. Create one script in `scripts/run_paper_loop.py` that:
- sets up logging
- loads settings
- prints a startup message
- (no real trading logic yet)

5. Ensure all imports are relative and consistent (`from sagetrade.utils.config import load_settings`, etc).

STYLE:
- Use Python 3.11+ features (dataclasses, type hints).
- Keep implementations minimal and clearly marked with TODO comments.
- Output all code as a set of file blocks, each starting with a comment indicating the file path, like:
  # FILE: sagetrade/utils/config.py
  <code here>


تعطي هذا الـ Prompt لــ AI Agent، يأخذ blueprint اللي عندك، ويولّد لك:

كل المجلدات

الملفات الأساسية

الكلاسات والـ dataclasses جاهزة للتطوير

وأنت فقط تنسخ/تلصق الملفات في مشروعك.