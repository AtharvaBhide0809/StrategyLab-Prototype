# StrategyLab v2.0 — Consolidated Stage 1 candidate

This is an AI-assisted educational reference for independent study, not authenticated NEA coursework.

## Changes from the GUI-audit candidate
- Added Strategy Analytics tabs for **Risk and benchmarking** (strategy versus gross buy-and-hold return) and **Periodic returns** (end-of-month compounded returns).
- Added a reusable pure-Python `advanced_report` routine: period returns, approximate Sortino, greatest and least completed trade, streaks, underwater duration, and relative return.
- Added a directional Qt wheel-event handler for the historical slider. Wheel up advances toward later candles and wheel down toward earlier candles; scrollbar dragging remains unchanged.
- Added five new numerical regression tests. Existing testing suite remains intact.

## Verification
- `python -m unittest discover -p "test_*.py" -q`: **45 tests passing** in the build environment.
- Python syntax compilation succeeded.
- PyQt6 not available in this environment: actual GUI launch, visual inspection, mouse wheel behaviour, clipping/layout, and Windows performance are **not** verified here.

## Important limitations
- Stage 1 is not yet a fully accepted or pixel-perfect TradingView-like UI. It retains the prior dark-theme layout and Matplotlib charts; the advanced reporting is a focused expansion, not a complete implementation of every screenshot metric.
- Sortino is indicative and annualised with approximate candle frequency; monthly returns use available calendar-month endpoints. These figures are historical simulations, not forecasts.
- Buy-and-hold comparison does not apply fees, splits, dividends or leverage.
- No live trade execution.

## Windows test commands
Open the folder containing `app.py` and run:

```powershell
python -m unittest discover -p "test_*.py" -v
python app.py
```

Verify the two new analytics tabs after a backtest and try scrolling the price-history slider in both directions. Keep your stable v1.1.1 repository untouched until all release checks pass.
