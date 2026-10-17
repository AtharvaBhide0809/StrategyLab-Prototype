# StrategyLab — A-level NEA working prototype

This is a **teaching prototype**, not trading or investment software.

## Start on Windows / macOS / Linux

Install Python 3.12. From this folder, run:

```bash
python -m pip install -r requirements.txt
python app.py
```

Run core tests without installing a GUI library:

```bash
python -m unittest test_core.py -v
```

If needed, recreate the included **synthetic** demonstration dataset:

```bash
python create_demo.py
```

## Input language

One `BUY IF` line and one `SELL IF` line. `AND`, `OR`, `NOT`, parentheses, numeric comparisons and indicators `CLOSE`, `VOLUME`, `RSI`, `RSI_14`, `SMA_20` (any positive integer period), `MACD`, and `MACD_SIGNAL` are supported. Keywords are case insensitive. `RSI` means RSI with period 14. Examples:

```
BUY IF RSI < 30 OR CLOSE > SMA_20
SELL IF RSI > 70
```

## Historical CSV format

`Date,Open,High,Low,Close,Volume` with ISO dates such as `2024-02-01`, and at least 35 unique rows. Import a real historic OHLCV file through the GUI if desired. The included data is *fabricated* and serves only to demonstrate code execution.

## Simplifications and limitations

- **Daily bars, not genuine intraday/day-trading data.** No live prices or broker connections.
- Signals are based on bar close; trades execute at the *following bar's open*. This eliminates the most basic same-bar lookahead error.
- Long only, one full-capital position at a time, fractional shares, fixed 0.1% entry and exit commission; no shorting, leverage, slippage or dividends.
- MACD uses 12/26 EMAs and 9 EMA signal; RSI uses Wilder smoothing.
- Trade logs show realised P/L only on sells; an open position remains marked to market at final close.
- Buy-and-hold uses first to last closing price and excludes fees; this is an illustrative comparison, not a matching execution model.
- Sharpe uses daily equity returns, zero risk-free rate, 252 annualisation and sample volatility.
- The app does *not yet* have SQLite persistence, online downloads/cache, genetic optimisation, live syntax suggestions, or ticker lookups. These are sensible follow-up iterations for the NEA.
- Indicator values that have not finished their warm-up period suppress both entry and exit checks.

## Layout

- `strategy.py`: lexer, recursive-descent parser, AST and evaluator
- `engine.py`: OHLCV loading, native-Python indicator algorithms, simulation and performance metrics
- `app.py`: PyQt6/Matplotlib interface
- `create_demo.py`: deterministic synthetic OHLCV dataset generator
- `test_core.py`: reproducible initial unit tests

Read and understand all code before incorporating it into assessed work. Document design decisions, your own changes and your testing honestly.
