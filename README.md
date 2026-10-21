# StrategyLab v2.0 — integrated testing candidate

**Educational historical backtesting reference; no live brokerage orders.** This is an AI-assisted reference package, not independently authored assessed NEA coursework. Review and independently develop/document any material submitted for assessment with your teacher's guidance.

## What's new compared with v1.1.1

- Chronological in-sample / out-of-sample validation, default 70%/30%, with indicator warmup on earlier candles and *no training-window trade fills* in held-out results.
- Optimiser ranks candidates using **training data only** and evaluates the selected winner against the held-out period after search. Holdout fitness does not influence selection.
- Minimum completed-trade fitness threshold; optional manual min/max bounds for numeric rule thresholds; configurable complexity penalty; drawdown-adjusted objective in addition to return and Sharpe.
- Dashboard Matplotlib navigation toolbar (zoom/pan/save), optional SMA-20/SMA-50 candle overlays, clickable completed-trade rows highlighting entry/exit points, and table sorting.
- Strategy editor has starter templates for RSI, SMA, MACD and RSI+volume conditions.
- **28** automated tests (18 inherited and 10 v2.0); see below.
- App no longer automatically launches the synthetic-data backtest at startup: press Run backtest when ready.

- **Structural analytics update:** the dashboard is now chart-focused, with a separate Strategy analytics navigation page for existing equity, trade, performance and distribution reports. See `ANALYTICS_LAYOUT_NOTES.md`.

## Installation/testing on Windows (no virtual environment required)

Unzip **outside** your existing repository and open `StrategyLab_v2.0` in VS Code. Run with the *same working Python interpreter* used previously:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -p "test_*.py" -v
python app.py
```

Use the PyQt6 GUI to check plots, downloads, saved strategies, strategy changes, opening CSV, and optimisation. The application requires an interactive Windows desktop. If the GUI fails, capture the complete traceback. The synthetic sample data is not genuine market history. No `pytest` or virtual environment is required.

## Recommended desktop acceptance scenarios

1. Launch the GUI and confirm it displays the dashboard **without** starting an automatic backtest or creating a run record.
2. With demo data, press **Run backtest**; verify a plotted equity curve, metrics and reconciled fills.
3. Tick **Overlay SMA 20 / 50**; use chart zoom/pan and ensure markers remain correctly located.
4. Edit a strategy, use **Insert template**, validate and backtest. Verify saved strategy and history survive a restart.
5. Use optimisation with 70% training, 2 minimum trades and 4 population / 2 generations. Verify the training and holdout start dates, metrics, and candidate script. Increase minimum trades until candidates are rejected with an informative error.
6. Test search bounds using two lines such as `10,40` and `60,90` when there are exactly two numeric thresholds.
7. Load a local CSV, then select another watchlist ticker; confirm old candles are never shown for the new symbol.
8. Test a short Binance download (subject to location/network access) and Alpaca IEX with user-provided credentials, including offline reloading. Do not put credentials into the repo.
9. Re-run all tests, review `git status`, and manually compare chosen v1.1.1 results before committing v2.0.

## Important limitations and methodological cautions

- Optimiser still modifies numeric **comparison thresholds**, not indicator periods, custom indicator formulas, or weights. Bounds apply only to detected threshold numbers.
- Only a single chronological holdout is supported; no rolling walk-forward search, purged CV, position sizing optimisation, cancellation, or market-impact simulation.
- Reusing a held-out set to guide repeated parameter changes leaks information. Treat the first OOS check as the meaningful one; repeated tuning requires a fresh final test interval.
- Sharpe annualisation is approximate. The backtester does not model corporate actions, exchange calendars, real spreads, intrabar execution or live trading.
- Some plotting features rely on Matplotlib/PyQt; they cannot be verified using these headless unit tests.
- This package has not been independently tested with external Binance/Alpaca endpoints or fully GUI-tested on Windows in this environment.
- `user_data/`, API credentials and `.env` files must never be committed.

## Updating your Git branch AFTER successful testing

Do **not** delete `.git`, change your `master` branch, or overwrite your tagged v1.1.1 copy. Compare the candidate with your own repository and copy the tested source files to your existing `feature/v2.0` branch. Do not copy any `user_data`, cache databases, local secrets, or old `__pycache__` directories. Run `git diff` and tests before committing. A new release tag should be created only after GUI/network acceptance testing.

## Consolidated v2.0 Stage 1 extension
See `STAGE1_NOTES.md` for new Strategy Analytics reports, testing results, and remaining Windows acceptance tasks.
