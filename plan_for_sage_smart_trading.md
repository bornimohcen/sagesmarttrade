خطة تفصيلية متعددة المراحل لـ AI AGENT (قابلة للإعطاء للـ Agent مباشرة)

هذه الخطة مكتوبة كـ «مواصفات تنفيذية» — كل مرحلة تحتوي على هدف، مهمات مفصّلة، خطوات تنفيذيّة، مدخلات/مخرجات، معايير قبول (Acceptance Criteria)، اختبارات، ونقاط كشف أمان/تحكم بشري. صيغتها تسمح لوكيل الـAI أن يتبعها وينفذها آليًا (مع قواعد مـنـع/موافقة صريحة للبشر عند نقاط حسّاسة).

المرحلة 0 — التجهيز والضمانات الأمنية (Prep & Safety)

الهدف: تجهيز بيئة آمنة قابلة للتكرار، حماية أسرار، وقواعد واضحة لعمل الـAI (no-automerge، kill-switch، مراجعات).

مهمات

0.1. إعداد إدارة الأسرار

خطوات: تحقق من وجود config/secrets.env، أضفها إلى .gitignore، إذا في CI أضف GitHub Secrets.

مدخلات: مفاتيح API، config files.

مخرجات: ملف secrets آمن، قائمة سرية في GitHub Secrets.

قبول: verify_installation يطبع أن المفاتيح موجودة دون تسريبها.

0.2. إعداد قواعد سلوك الـAI (Governance)

خطوات: إنشئ ملف AI_POLICY.md يحدد: generate-only mode، لا دمج تلقائي، PR مع وسم ai-proposed, requires at least 1 human approver.

قبول: وجود AI_POLICY.md في repo وملف .github/PULL_REQUEST_TEMPLATE.md ينبه للمراجعة اليدوية.

0.3. Kill-switch و emergency stop

خطوات: إضافة endpoint أو أمر في Telegram لإيقاف جميع التداولات فورًا (/emergency_stop).

قبول: أمر يقطع تنفيذ الأوامر ويقفل كل الـ agents.

0.4. Health & Startup check

خطوات: ملف startup_check.py يشغّل قبل أي execution، يعيد non-zero إذا فشل الاتصال أو الحساب غير ACTIVE.

اختبار: تشغيل python startup_check.py ببيئة حقيقية وبيئة مغلقة.

مدة مقترحة: 1–2 أيام.
نقطة توقّف (Gate): لا تبدأ المرحلة 1 إلا بعد الموافقة اليدوية على AI_POLICY.md وإثبات أن kill-switch يعمل.

المرحلة 1 — البنية الأساسية للبيانات والمراسلة (Data & Messaging)

الهدف: تأسيس خطوط بيانات موثوقة ووسيط رسائل (queue) لفصل المكونات.

مهمات

1.1. اختيار وتثبيت وسيط الرسائل

خيارات: Redis Streams أو RabbitMQ أو Kafka (MVP: Redis).

خطوات تنفيذية: نشر محلي/حاوية، إعداد namespace sagetrade, اختبار نشر/استقبال رسالة.

1.2. Market data ingestion

خطوات: إنشاؤer module market_fetcher يدعم: REST historical fetch + websocket live feed.

اختبارات: replay local historical data, verify time-sync.

1.3. News & Social ingestion

خطوات: scrapers/API connectors لـ Twitter/X, Reddit, RSS, Telegram channels (read-only).

حاجة rate-limit handling و dedupe.

قبول: pipeline قادر على إدخال 100 msgs/second مع dedupe.

1.4. Storage & Layering

وضع بيانات السوق كـ Parquet يومي في data/market/YYYY-MM-DD/*.parquet.

تخزين النصوص الخام + metadata (source, timestamp, url).

مدة مقترحة: 1–2 أسابيع.
Gate: تحقق من قدرة الاسترجاع بالـ replay engine وتشغيل consumer واحد يقرأ الرسائل.

المرحلة 2 — التحليل الكمي وNLP (Signals)

الهدف: بناء طبقتي التحليل: كمّي (indicators, regimes) و NLP (sentiment/event detection).

مهمات

2.1. Quant indicators module

خطوات: implement indicators (SMA, EMA, ATR, RSI, volatility measures), regime classifier (low/high vol).

مخرجات: API quant.signals.get_signals(symbol, window).

2.2. NLP pipeline (مبدئي)

خطوات:

preproc (cleaning, language detection),

embeddings (use local SBERT or hf),

sentiment model & event classifier (earnings, M&A, guidance).

مخرجات: nlp.signals.get_signals(entity, timeframe) مع: sentiment, event, impact_score (0..1).

2.3. Signal aggregator

خطوات: aggregate quant + nlp signals → produce weighted composite_signal (score, direction, confidence).

قبول: aggregator يعطي نفس النتيجة عند إعادة التشغيل على نفس البيانات.

اختبار: backtest بسيط لإظهار أن composite_signal يرتبط بتحركات السعر في نافذة زمنية قصيرة.
مدة: 2–4 أسابيع.

المرحلة 3 — Strategy Manager و Strategy Plugins

الهدف: تصميم معماري plugin للاستراتيجيات بحيث يسهّل إضافة/اختبار/تعطيل استراتيجيات.

مهمات

3.1. تعريف واجهة Strategy

واجهة (API): initialize(config), on_new_signal(signal) -> Decision, on_tick(market_state) -> manage_positions.

Decision يحتوي: side, size_pct, order_type, tp, sl, target_duration.

3.2. استراتيجيات أولية (MVP)

Momentum scalper, Mean-reversion scalper, News-driven quick-trade.

كل استراتيجية ملف مستقل في strategies/.

3.3. Strategy registry & selector

Policy engine يختار الاستراتيجيات بناءً على regime وـ confidence و risk budget.

قبول: ability to enable/disable strategy via config and via Telegram.

اختبار: paper-trade كل استراتيجية على بيانات 30 يوم مع metrics.
مدة: 2 أسابيع.

المرحلة 4 — Execution Engine و Risk Manager

الهدف: تنفيذ أوامر آمن وموثوق مع تحكّم مخاطرة صارم.

مهمات

4.1. Order Manager (abstraction)

واجهة: create_order(symbol, side, qty, type, params) يدير retries, timeouts, partial fills.

تسجيل trade lifecycle (created, filled, partial, cancelled).

4.2. Position Sizing module

algorithms: fixed fraction, volatility scaled, kelly-lite.

مدخلات: account_balance, max_trade_risk_pct, volatility.

4.3. Risk Manager

قواعد: max_open_trades, max_exposure, max_intraday_loss, per-symbol limit.

circuit-breaker (global stop when max_daily_loss exceeded).

4.4. Execution for micro-trades

policies: allowed slippage threshold, max order lifetime, auto-close after N seconds if unfilled.

اختبار: run paper-trading simulation with injected latencies and partial fills.
مدة: 2–3 أسابيع.
Gate: لا استخدام live until canary & human approval.

المرحلة 5 — Backtest / Paper Trading & Replay Engine

الهدف: أدوات صارمة لمقارنة أداء استراتيجيات قبل نشرها live.

مهمات

5.1. Deterministic backtest framework

محاكاة رسوم/عمولات/slippage، استيراد data/parquet، output trade logs & metrics.

5.2. Replay engine (historical + live speed)

يشغل البيانات التاريخية مع نفس الـ latencies لدراسة behavior.

5.3. Metrics dashboard (local)

PnL, Sharpe, drawdown, winrate, trade_duration, avg_slippage.

اختبار: لكل استراتيجية، run backtest على 6 أشهر وفِر report.
مدة: 2 أسابيع.

المرحلة 6 — Experimentation & Self-Improvement Pipeline (AI-driven)

الهدف: تمكين الـAgent من اقتراح تغييرات/استراتيجيات وتشغيلها في sandbox وإدارتها بشكل آمن.

مهمات

6.1. Experiment Manager

ينشأ تجربة، يحدد الفرضية، يخلق برانش/PR يحتوي الكود المعدّل + اختبارات + config، يربط تجربة ببيانات الاختبار.

6.2. Sandbox evaluation

تلقائيًا: run backtest + paper trading on canary allocation (1% capital simulated).

تسجيل metrics وملف تقرير experiment_report.json.

6.3. Promotion policy

قواعد صعود: تحقق من شروط (مثلاً Sharpe +0.2 و return +5% مع نفس/higher drawdown tolerance) → توليد توصية دمج.

دمج فعلي يتطلب: 1) موافقة بشرية، 2) موافقة CI (lint + tests) و 3) canary deploy.

6.4. Auto-PR generation template

قالب PR يجب أن يحتوي: description, tests ran, metrics baseline vs experiment, canary plan, rollback criteria.

اختبار: run end-to-end تجربة واقعية مقترحة من الـAI، تأكد أن كل خطوة تولّد artifacts قابلة للتدقيق.
مدة: 4–8 أسابيع (متوازي مع مراحل سابقة).

المرحلة 7 — Telegram Bot & User Interaction (Advisor)

الهدف: واجهة تواصل تفصيلية للمستخدم تعرض توقعات، نتائج، وتُتيح أوامر تحكم.

مهمات

7.1. Bot MVP

أوامر: /status, /portfolio, /open_positions, /pause, /resume, /explain <trade_id>, /emergency_stop.

7.2. Advisor Mode (NLP)

الـBot يجيب على استفسارات مثل: "هل أدخل صفقة BTC الآن؟" → يرد بتحليل مختصر (signals used, confidence, risk).

7.3. Notifications & Summaries

إشعارات: كل عملية فتح/إغلاق، تجميع يومي/أسبوعي للأداء، تنبيهات عند تجاوز حدود الخسارة.

7.4. Auth & Authorization

ربط Telegram IDs بالمستخدمين، كل أمر تنفيذي يحتاج رمز تأكيد للمستخدِم أو إعدادات auto-approve.

اختبار: محاكاة جلسات مستخدم، تحقق من أن أوامر pause/resume تعمل فوريًا.
مدة: 1–3 أسابيع.

المرحلة 8 — Hardening, Monitoring & Ops

الهدف: تحويل النظام إلى قابلية تشغيل طويلة المدى مع مراقبة وتنبيهات.

مهمات

8.1. Observability

إعداد Prometheus metrics + Grafana dashboards: PnL, trades/sec, errors, latencies.

structured logs (json) إلى ELK.

8.2. Alerts & On-call

إعداد قواعد تنبيه: circuit-breaker triggered, more than X failed orders in Y minutes, experiment regression.

8.3. Backup & Rollback

آلية snapshot للـmodels/code والقدرة على استرجاع نسخة سابقة فورًا.

8.4. Autoscaling & Infra

تحضير Docker images، readiness/liveness probes، K8s manifests (مبدئيًّا docker-compose ثم K8s).

مدة: 3–8 أسابيع.

قواعد وسياسات تشغيلية حرجة (لا تتجاوزها الـAgent)

لا تنفذ تغييرات كود تلقائيًا في production. فقط PRs مع وسم ai-proposed.

كل تجربة جديدة => test-suite + backtest + paper-canary قبل أي نشر.

حد أعلى للخسارة اليومية (مثلاً 3% من AUM) يوقف كل التداولات تلقائياً.

التفاعل مع المستخدم: أي أمر يقوم بتعديل allocation أو مستوى المخاطرة يتطلب تأكيد مزدوج (Telegram + password).

تسجيل كامل: جميع قرارات الـAgent يجب أن تُسجّل (سبب، إشارات، confidence, source data).

قوالب معيارية وملفات جاهزة (تسليم للـAgent)
قالب PR مختصر (auto-generated by Agent)
Title: [AI-PROPOSED] <short description>

Description:
- What changed:
- Rationale:
- Tests run: (pytest, lint)
- Backtest results: baseline vs experiment (attach experiment_report.json)
- Canary plan: allocate 1% of capital for 72 hours, metrics to watch: PnL, drawdown, avg slippage
- Rollback criteria: negative return > X% in 24h OR drawdown > Y%

Requires: @human_approver

قالب Experiment Report (experiment_report.json)
{
  "experiment_id": "exp-20251113-001",
  "branch": "ai-experiment/exp-20251113-001",
  "hypothesis": "increase sharpe by +0.2",
  "baseline_metrics": {"sharpe":0.8,"return":0.12,"drawdown":0.07},
  "experiment_metrics": {"sharpe":1.05,"return":0.18,"drawdown":0.09},
  "backtest_range": "2025-01-01..2025-10-31",
  "paper_simulation": {"allocated_capital_pct":1,"duration_hours":72},
  "artifacts": ["backtest_report.csv","trades.log"],
  "approved": false
}

Trade Log Schema (per trade)
{
 "trade_id":"trade-0001",
 "timestamp":"2025-11-13T12:34:56Z",
 "symbol":"BTCUSD",
 "side":"buy",
 "size_pct":0.1,
 "entry_price":61000,
 "exit_price":61060,
 "duration_seconds":300,
 "strategy":"news_scalper_v1",
 "signals":[{"type":"nlp","score":0.85},{"type":"momentum","score":0.4}],
 "outcome":"win",
 "pnl_pct":0.098
}

تعليمات تنفيذية جاهزة للـ AI AGENT (Prompts/Tasks قصيرة)

استخدم هذه المهام كنقاط عمل مباشرة:

Task: Create retry util and apply to Alpaca adapter

Action: Add connectors/common/retry.py, decorate all external API calls with @retry(max_attempts=3, backoff_seconds=2).

Output: PR with changes + unit tests mocking Alpaca errors.

Task: Implement startup_check

Action: Create startup_check.py that fails if account status != ACTIVE.

Output: script + CI step that runs it on verify_installation.py stage.

Task: Create Strategy Plugin skeleton

Action: scaffolding in strategies/ with docs & tests.

Output: example strategy momentum_scalper.py with unit tests.

Task: Implement Experiment Manager basic flow

Action: CLI sagetool experiment create --name "..." that: branches, runs tests, runs backtest, stores report.

Output: experiment_report.json + PR.

Task: Build Telegram MVP

Action: simple bot with /status, /pause, /resume, /explain <id>.

Output: bot code + instructions to configure token via secrets.env.

لكل مهمة: سجل جميع الأوامر، شغّل اختبارات، سجّل أي أخطاء. إن وجدت تغييرات خطِرة (تعدل حجم المال الذي يُستعمل أو تغير قواعد الإيقاف) — ضعها كـ draft PR واطلب موافقة يدوية.

معايير الإنجاز العامة (Definition of Done)

الكود مغطى بالـ unit tests الأساسية (≥ 70% coverage للـ modules الحرجة مثل execution, risk, strategy).

كل PR من الـAgent يملك تقرير تجربة (إن كان متعلقاً باستراتيجية) وقائمة بالاختبارات والنتائج.

وجود dashboard تعرض: PnL، drawdown، live exposure، number of active experiments.

وجود kill-switch واختباره مرة واحدة علنًا.

وثائق (README، API docs) محدثة لكل مكوّن رئيسي.

نقاط قرار نهائية ونقاط تفتيش بشرية (Human Gates)

Gate A: الموافقة على AI_POLICY.md و kill-switch قبل بدء تطوير التداول الآلي.

Gate B: قبل أي تنفيذ live لأول مرة — مراجعة من مهندس + مالك المنتج + اختبار canary plan.

Gate C: كل تجربة تحقّق شروط الترويج تلقائيًا تُعرض للمراجع البشري ويجب الموافقة اليدوية للدمج.