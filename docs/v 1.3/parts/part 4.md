المرحلة 4 🔥

بما إننا في:

Part 1 → تعريف النظام (spec)

Part 2 → Architecture Blueprint

Part 3 → Scaffolding (المجلدات + الملفات + stubs)

فالآن Part 4 = بناء نظام Configuration حقيقي ومرن (Settings & Profiles & Overrides)
يعني: كيف يتحكم البوت في كل شيء من ملفات إعدادات بدل ما تغيّر الكود كل مرة.

🧱 المرحلة 4 — نظام الإعدادات (Configuration System)
🎯 هدف المرحلة

إنتاج نظام إعدادات واحد واضح يمكن من خلاله:

تغيير:

الوسيط (broker: paper / alpaca)

حدود المخاطر

قائمة الرموز

الإطار الزمني

مفاتيح الـ API

إعدادات تيليغرام، إلخ

بدون تعديل الكود، فقط عن طريق:

config/*.yaml

متغيرات البيئة (Environment Variables)

ربما arguments من CLI لاحقًا

وفي النهاية يكون عندك:

config/settings.yaml رئيسي

(اختياري لاحقًا) config/settings.dev.yaml, config/settings.prod.yaml

كلاس Settings (Pydantic أو dataclass) يحمل الإعدادات كلها ويمر عبر النظام.

1️⃣ شرح مفصل لما نحتاجه من الـ Config System

نريد Configuration System يحقق:

هيكل واضح:

app

data

risk

brokers

strategies

telegram

symbols

فصل بين الكود والقيم الحساسة:

مفاتيح API تُقرأ من Environment، وليس مكتوبة في YAML مباشرة.

إمكانية وجود Profiles:

env: dev / staging / prod

التحقق (Validation):

مثلاً:

max_risk_per_trade_pct بين 0 و 0.05

max_daily_loss_pct بين 0 و 0.2

لو فيه خطأ → نرمي Exception مبكّرًا.

سهولة الاستخدام:

استدعاء بسيط في الكود:

from sagetrade.utils.config import get_settings

settings = get_settings()
print(settings.risk.max_risk_per_trade_pct)

2️⃣ تقسيم المرحلة 4 إلى مهام صغيرة
🧱 المهمة 4.1 — تصميم شكل settings.yaml

نحتاج ملف YAML رئيسي منظم، مثال:

app:
  name: "SAGE SmartTrade"
  env: "dev"
  base_currency: "USD"
  timezone: "Africa/Algiers"

data:
  base_dir: "data"
  market_dir: "data/market"
  text_dir: "data/text"
  logs_dir: "logs"

risk:
  max_risk_per_trade_pct: 0.005      # 0.5%
  max_daily_loss_pct: 0.03           # 3%
  max_symbol_exposure_pct: 0.2       # 20%
  max_open_trades: 10

brokers:
  default: "paper"
  paper:
    starting_equity: 10000
  alpaca:
    base_url: "https://paper-api.alpaca.markets"
    key_env: "ALPACA_API_KEY"
    secret_env: "ALPACA_API_SECRET"

strategies:
  enabled:
    - "news_quick_trade"
    - "trend_follow"
  per_symbol:
    BTCUSD:
      - "news_quick_trade"
    AAPL:
      - "trend_follow"

symbols:
  default_universe:
    - "BTCUSD"
    - "AAPL"
    - "EURUSD"

telegram:
  enabled: false
  bot_token_env: "TELEGRAM_BOT_TOKEN"
  chat_id_env: "TELEGRAM_CHAT_ID"


هذا مجرد مثال، تقدر تزيد/تنقص حسب احتياجك.

🧱 المهمة 4.2 — بناء كلاس Settings (Pydantic)

ننشئ كلاس Settings مع Sub-models:

AppSettings

DataSettings

RiskSettings

BrokerSettings

StrategiesSettings

SymbolsSettings

TelegramSettings

مثال مبسط (قابل للتوسيع):

# FILE: sagetrade/utils/config.py

from pathlib import Path
from functools import lru_cache
from typing import List, Dict, Optional
import os
import yaml
from pydantic import BaseModel, Field, validator

class AppSettings(BaseModel):
    name: str = "SAGE SmartTrade"
    env: str = "dev"
    base_currency: str = "USD"
    timezone: str = "Africa/Algiers"

class DataSettings(BaseModel):
    base_dir: str = "data"
    market_dir: str = "data/market"
    text_dir: str = "data/text"
    logs_dir: str = "logs"

class RiskSettings(BaseModel):
    max_risk_per_trade_pct: float = Field(0.005, ge=0.0, le=0.05)
    max_daily_loss_pct: float = Field(0.03, ge=0.0, le=0.2)
    max_symbol_exposure_pct: float = Field(0.2, ge=0.0, le=1.0)
    max_open_trades: int = Field(10, ge=1, le=1000)

class PaperBrokerSettings(BaseModel):
    starting_equity: float = 10000.0

class AlpacaBrokerSettings(BaseModel):
    base_url: str
    key_env: str = "ALPACA_API_KEY"
    secret_env: str = "ALPACA_API_SECRET"

    @property
    def key(self) -> Optional[str]:
        return os.getenv(self.key_env)

    @property
    def secret(self) -> Optional[str]:
        return os.getenv(self.secret_env)

class BrokersSettings(BaseModel):
    default: str = "paper"
    paper: PaperBrokerSettings = PaperBrokerSettings()
    alpaca: AlpacaBrokerSettings

class StrategiesSettings(BaseModel):
    enabled: List[str] = ["news_quick_trade"]
    per_symbol: Dict[str, List[str]] = {}

class SymbolsSettings(BaseModel):
    default_universe: List[str] = ["BTCUSD", "AAPL", "EURUSD"]

class TelegramSettings(BaseModel):
    enabled: bool = False
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id_env: str = "TELEGRAM_CHAT_ID"

    @property
    def bot_token(self) -> Optional[str]:
        return os.getenv(self.bot_token_env)

    @property
    def chat_id(self) -> Optional[str]:
        return os.getenv(self.chat_id_env)

class Settings(BaseModel):
    app: AppSettings
    data: DataSettings
    risk: RiskSettings
    brokers: BrokersSettings
    strategies: StrategiesSettings
    symbols: SymbolsSettings
    telegram: TelegramSettings


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache
def get_settings(path: str | Path = "config/settings.yaml") -> Settings:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    raw = _load_yaml(p)
    return Settings(**raw)


استخدمت @lru_cache حتى لا نقرأ الملف كل مرة (نفس الـ settings مشتركة).

🧱 المهمة 4.3 — دعم الـ Environment Profiles (dev / prod)

يمكنك لاحقًا (اختياري في هذه المرحلة) تضيف:

ملف config/settings.dev.yaml

ملف config/settings.prod.yaml

وكود صغير يقرأ بناءً على:

متغير APP_ENV أو قيمة app.env:

def get_settings() -> Settings:
    env = os.getenv("APP_ENV", "dev")
    base = Path("config")
    path = base / f"settings.{env}.yaml"
    if not path.exists():
        path = base / "settings.yaml"
    raw = _load_yaml(path)
    return Settings(**raw)

🧱 المهمة 4.4 — توصيل الـ Settings بباقي النظام

بدل ما تكتب أرقام مش ثابتة في الكود، تستخدم Settings:

مثلاً في broker:

from sagetrade.utils.config import get_settings

settings = get_settings()
starting_equity = settings.brokers.paper.starting_equity


في RiskManager:

risk_settings = get_settings().risk
max_risk_per_trade = risk_settings.max_risk_per_trade_pct


في Trading Loop:

symbols = get_settings().symbols.default_universe
strategies = get_settings().strategies.enabled


بهذا الشكل، أي تغيير مستقبلاً يكون في YAML فقط.

🧱 المهمة 4.5 — ربط الـ Logging مع الـ Settings (اختياري هنا)

في utils/logging.py بدل hardcode لمسار اللوج:

from pathlib import Path
import logging
from sagetrade.utils.config import get_settings

def setup_logging(level: int = logging.INFO) -> None:
    settings = get_settings()
    logs_dir = Path(settings.data.logs_dir)
    logs_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(logs_dir / "sagesmarttrade.log", encoding="utf-8"),
        ],
    )

3️⃣ ما الذي يجب أن يكون جاهزًا في نهاية المرحلة 4؟

ملف config/settings.yaml منظم، وفيه:

app

data

risk

brokers

strategies

symbols

telegram

ملف sagetrade/utils/config.py فيه:

موديل Settings كامل (Pydantic)

get_settings() جاهز للاستعمال

أجزاء من الكود تستخدم Settings بدل أرقام/نصوص ثابتة

Trading loop يأخذ symbols من config

RiskManager يأخذ الحدود من config

Broker يأخذ الـ base_url ومفاتيح env من config

🤖 4️⃣ Prompt جاهز تعطيه لـ AI Agent لتنفيذ المرحلة 4

هذا الـ prompt تقدر تعطيه مباشرة لذكاء آخر (أو حتى لي في جلسة منفصلة) ليولّد لك كل ما تحتاجه:

You are a senior Python backend engineer.

CONTEXT:
- I have a trading project called SAGE SmartTrade.
- I already created project scaffolding with modules: ingestion, signals, strategies, risk, brokers, ai, telegram, backtesting, dashboard, utils.
- I now want to build a robust configuration system (phase 4).

TASK:
1. Design a main YAML configuration file `config/settings.yaml` that includes:
   - app: name, env, base_currency, timezone
   - data: base_dir, market_dir, text_dir, logs_dir
   - risk: max_risk_per_trade_pct, max_daily_loss_pct, max_symbol_exposure_pct, max_open_trades
   - brokers: default, paper (starting_equity), alpaca (base_url, key_env, secret_env)
   - strategies: enabled list, per_symbol mapping
   - symbols: default_universe
   - telegram: enabled, bot_token_env, chat_id_env

2. Implement `sagetrade/utils/config.py` with:
   - Pydantic models: AppSettings, DataSettings, RiskSettings, PaperBrokerSettings, AlpacaBrokerSettings, BrokersSettings, StrategiesSettings, SymbolsSettings, TelegramSettings, Settings.
   - A `get_settings()` function that:
     - reads YAML from `config/settings.yaml`
     - validates it via Pydantic
     - caches the result using `functools.lru_cache`.

3. Add convenience properties in broker and telegram settings to read secrets from environment variables.

4. Show example usage snippets:
   - In a trading loop, how to get symbols and enabled strategies from settings.
   - In a risk manager, how to get risk limits from settings.

STYLE:
- Use Python 3.11+ type hints and Pydantic BaseModel.
- Keep the code clean and realistic.
- Output code blocks with clear file path comments, for example:
  # FILE: config/settings.yaml
  ...
  # FILE: sagetrade/utils/config.py
  ...


انسخ هذا الـ Prompt، أعطه لـ Agent، انسخ الملفات الناتجة لمشروعك، جرّب:

python scripts/run_paper_loop.py


وتأكد أنه:

يقرأ الـ settings بدون مشاكل

يطبع القيم أو يستخدمها (حتى لو لسه ما في تداول فعلي)