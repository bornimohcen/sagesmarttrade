Multi-Asset Universe (Crypto, Equities, FX)

The engine is designed to support multiple asset classes (e.g. BTC, stocks, FX) via a simple instrument universe definition.

1) Universe configuration
- File: `config/universe.json`
- You can maintain it manually or auto-generate it from Alpaca.
- Example entries:
  - `BTCUSD` (crypto via Alpaca or another venue)
  - `AAPL` (US equity)
  - `EURUSD` (FX pair)
- Fields per symbol:
  - `asset_class`: `"crypto" | "equity" | "forex" | ...`
  - `venue`: logical venue name (e.g. `"alpaca-crypto"`, `"alpaca-equity"`, `"fx-broker"`)
  - `min_qty`: minimum tradable size
  - `max_leverage`: maximum leverage allowed for that instrument

2) Auto-populate universe from Alpaca
- Script: `scripts/update_universe_from_alpaca.py`
- Requirements:
  - `config/secrets.env` filled with:
    - `BROKER_API_KEY`
    - `BROKER_API_SECRET`
    - `BROKER_BASE_URL` (e.g. `https://paper-api.alpaca.markets`)
- Run:
  - `python scripts/update_universe_from_alpaca.py`
- Behavior:
  - Calls Alpaca `/v2/assets?status=active`.
  - Filters `tradable` assets.
  - Maps Alpaca `asset_class` to internal types:
    - `us_equity` → `equity`, venue `alpaca-equity`
    - `crypto` → `crypto`, venue `alpaca-crypto`
  - Writes `config/universe.json` with all tradable symbols in your account.

3) Access from code
- Module: `sagetrade/config/universe.py`
- Usage:
  - Load all instruments:
    - `from sagetrade.config.universe import load_universe`
    - `universe = load_universe()`  # dict[symbol -> Instrument]
  - Load a single instrument:
    - `from sagetrade.config.universe import get_instrument`
    - `inst = get_instrument("BTCUSD")`

4) How this ties to the rest of the system
- Ingestion, signals, strategies, risk, and execution already use a generic `symbol` field.
- To support crypto, stocks, and FX on the same engine:
  - Use `config/universe.json` to define which symbols are in scope and their asset-class-specific constraints.
  - Later phases (real broker adapters) can route orders based on `instrument.asset_class` and `instrument.venue`.
  - Risk management can be extended to set different limits per asset class or symbol using this universe file.

5) Current demos
- Many demo scripts default to `BTCUSD` but accept `--symbol`:
  - `scripts/ingest_market_sim_demo.py --symbol AAPL`
  - `scripts/signals_quant_demo.py --symbol AAPL`
  - `scripts/backtest_demo.py` (will use `--symbol` once real data for that symbol is available)
- Once you have real market data for other symbols (stocks, FX, etc.), the same pipeline can be re-used by changing the symbol and having `config/universe.json` generated/updated accordingly.
