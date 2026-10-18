# StrategyLab Reference v1.0

**AI-generated / AI-assisted learning reference, not independently authored OCR NEA submission.**

A PyQt6 desktop prototype demonstrating a rule-driven historical market backtester, a simple genetic optimiser and a TradingView-inspired layout. The synthetic dataset is intentionally **not real market data**. No live orders are placed.

## Quick start (Windows / VS Code)

1. Extract this archive somewhere outside your existing Git repository first.
2. Open the `StrategyLab_Reference_v1.0` folder in VS Code.
3. In the terminal run:

```powershell
python -m pip install -r requirements.txt
python app.py
```

Python 3.11 or newer is recommended. If the first launch fails, copy the **entire traceback** from VS Code. The desktop GUI has not been interactively verified in the build environment; underlying tests were executed.

## Main workflow

1. On **Dashboard**, run the demo rules against bundled synthetic data.
2. On **Strategy editor**, create `BUY IF ...` and `SELL IF ...` rules, validate and save them.
3. On **Parameters**, set starting cash, per-order fees, slippage and fraction invested.
4. On **Dashboard**, download Binance crypto spot historical data or Alpaca US stock IEX data. Select range, ticker and timeframe. Use Offline if already cached.
5. On **Optimisation**, optimise numeric thresholds (e.g. RSI < 30) using a small genetic search.
6. Use **Saved strategies** to restore and delete definitions; **History** records summary stats for each completed run.
7. Trade events are marked on the candlestick chart and listed in **Trade log**.

The provider adapters use `urllib` only. Alpaca needs free historical market-data API credentials:

```powershell
$env:APCA_API_KEY_ID = "YOUR_KEY"
$env:APCA_API_SECRET_KEY = "YOUR_SECRET"
python app.py
```

Never commit tokens or `.env` files. The user data directory is excluded by `.gitignore`. Binance data archive behaviour and Alpaca API limits may change. Data providers are not guaranteed available everywhere.

## Python modules

| Module | Purpose |
|---|---|
| `strategy.py` | Custom lexer, recursive descent parser with AND/OR/NOT precedence, AST nodes, safe evaluator |
| `engine.py` | CSV loading, native SMA/EMA/Wilder RSI/MACD, chronological next-open trading simulation, performance metrics |
| `data_sources.py` | Binance public ZIP archives, Alpaca IEX HTTP requests, UTC-normalised OHLCV candles, SQLite caching |
| `storage.py` | SQLite profiles, saved strategy sources, runs and execution records |
| `optimizer.py` | Population, ranking, elite preservation, crossover, mutation, optimisation progress; modifies numerical **comparison thresholds**, not indicator periods |
| `app.py` | PyQt6 stacked-pages UI, async provider fetch and optimiser threads, Matplotlib plots |
| `test_*.py` | Unit tests for parsing, backtesting, providers, cache, optimiser and persistence |

## Running tests

```powershell
python -m unittest discover -p "test_*.py" -v
```

## Limitations and missing/partial NEA features

This is an **integrated reference milestone**, not a verified feature-complete product. Important gaps relative to the Analysis:

- **No custom formula indicator parser** or indicator weighting editor; built-in RSI, SMA, MACD and raw Volume are supported.
- **No configurable genetic search bounds UI**, multi-objective fitness or automated out-of-sample validation. Parameter search changes numeric rule thresholds only. It cannot optimise indicator *periods* yet.
- **Basic error handling only**; live debounced syntax checking is implemented, but automatic spelling suggestions and semantic linter are not comprehensive.
- **Trade log is a list of fills**, not matched position-level entry/exit rows; sorting/filtering and clicking fills to highlight candles are not yet implemented.
- **Performance metrics are simplified.** Sharpe uses naive per-candle annualisation and risk-free rate 0; stocks do not comprehensively account for irregular exchange sessions. Fees, slippage and fraction of available cash are modelled, but spreads, market impact, splits and dividends are not.
- **Buy-and-Hold comparison excludes trading fees**, and includes its own simplified price assumptions.
- **Unrealised open positions remain open at the end**, and realised win rate counts closing sells only.
- **Candlestick chart samples bars** for rendering speed at large data sizes. Markers are placed using original timestamp indices.
- **Market data is retrieved online then cached for offline runs**; only cached intervals can be used fully offline. Some API/archive gaps, data quality and provider restrictions are expected.
- **The UI is a dark-theme functional first pass**, not a pixel-matched TradingView clone. No standalone EXE is included. Package manually with PyInstaller if desired.
- **No claim of achieving NEA timing targets, 3NF proof, mathematical reference accuracy or full integration on Windows**. Those require additional tests.

## How to put it into your reference repository

Keep your existing local reference prototype safely committed. Unzip elsewhere first, inspect changes, then **copy the contents of this folder** into your local `StrategyLab-Prototype` repository (not into `StrategyLab-NEA`). Existing source filenames will be replaced. It is safest to create a temporary Git branch:

```powershell
cd "$HOME\Documents\Computer Science NEA\StrategyLab-Prototype"
git status
git switch -c reference-v1
# Copy in the extracted new files from File Explorer.
python -m pip install -r requirements.txt
python -m unittest discover -p "test_*.py" -v
python app.py
# After testing and checking the result:
git add .
git commit -m "Add integrated StrategyLab reference v1.0"
git push -u origin reference-v1
```

No code in this archive modifies your repository or GitHub account by itself.

## AI and coursework provenance

This entire reference application builds on the AI-generated v0.1/v0.2 demonstrations with further AI-generated modules. It is for reference, learning and experimentation. Keep a record of the prompts, generated artifacts, and any assistance or code actually reused in assessed work. The separate NEA repository should be independently authored and comply with your teacher's/OCR's authentication rules.
