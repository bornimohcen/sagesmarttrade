Phase 2 — Quant & NLP Signals

1) Quant indicators module
- File: `sagetrade/signals/quant.py`
- Key functions:
  - `sma`, `ema`, `rsi`, `atr`, `volatility`, `classify_regime`
  - `get_signals_from_bars(symbol, bars, window)` returns a `QuantSignals` object (including regime).
- Quick test:
  - Ensure market data exists in `data/market/...`:
    - `python3 scripts/ingest_market_sim_demo.py --symbol BTCUSD --publish --store`
  - Then:
    - `python3 scripts/signals_quant_demo.py --symbol BTCUSD --window 20`

2) NLP pipeline (initial)
- File: `sagetrade/signals/nlp.py`
- Core utilities:
  - `clean_text`, `detect_language`, `sentiment_score`, `detect_events`
  - `get_signals(entity, items)` returns `NLPSignals` with:
    - `sentiment` ∈ [-1, 1]
    - `event_flags` (earnings, ma, guidance)
    - `impact_score` ∈ [0, 1]
- Quick test:
  - Ensure RSS news exists in `data/text/...`:
    - `python3 scripts/ingest_rss_demo.py --publish --store`
  - Then:
    - `python3 scripts/signals_nlp_demo.py --entity market`

3) Signal aggregator
- File: `sagetrade/signals/aggregator.py`
- Function:
  - `aggregate(symbol, quant, nlp, w_quant=0.6, w_nlp=0.4)` → `CompositeSignal`
  - Output fields: `score`, `direction` (long/short/flat), `confidence`.
- Quick test:
  - After preparing both market and text data:
    - `python3 scripts/signals_aggregate_demo.py`

4) Notes
- All computations are deterministic: same inputs → same signals.
- The NLP model is rule-based and intentionally simple; later it can be swapped for a transformer/embeddings model while keeping the same `NLPSignals` interface.
