# Build notes — 2026-10-18

## Reference v1.0 changes

- Inherited the v0.2 custom lexer/parser, indicator engine, next-open backtester and Binance/Alpaca data adapters.
- Added SQLite saved strategies, user profile record, run history and individual trade fills.
- Added an illustrative genetic search over parsed numerical comparison thresholds with tournament-like top-half parent pool, elitism, uniform crossover and Gaussian mutation.
- Added a six-page PyQt6 GUI with left navigation, right asset watchlist, candlestick plotting and trade event markers.
- Added parameters, saved strategy management and threaded optimisation/data downloads.
- Extended backtest to model per-order slippage and configurable percentage cash allocation.
- Added tests for no-trade results, partial capital allocation, optimisation and SQLite persistence.

## Verification at packaging

- Python modules syntax-compiled.
- `python -m unittest discover -p 'test_*.py' -q` → 12 tests passed.
- Optimiser and Store independently smoke-tested using sample prices and a temporary SQLite file.
- **PyQt6 could not be installed or launched in the isolated build environment (network unavailable).** Visual/Windows application integration must be tested by the recipient.
- Remote market feeds were not contacted or live-tested; provider tests use mocks.

## Noteworthy implementation details

- Rule expressions are interpreted using AST traversal rather than Python `eval`.
- Signals use completed candle values and execute at the *next* candle's open.
- The optimiser modifies literal numeric comparison thresholds, and does not yet optimise indicator periods.
- No trading or brokerage order functionality is included.
