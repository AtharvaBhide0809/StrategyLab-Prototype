# StrategyLab Reference v1.1.1 — accounting correction

This is an AI-generated educational reference, **not independently authored assessed NEA code**.

## Changes

- Added `asset_type` / `timeframe` defaults and `annualisation_periods()` in `engine.py`. Application passes explicit settings to backtests; its optimiser uses the same timeframe-aware annualisation, fee, slippage and position allocation.
- Added open-position state, available cash, marked-to-market unrealised P&L, net realised P&L, total P&L, final account equity, gross profit/loss and completed round-trip trade records to the result dictionary.
- Added an accounting reconciliation check (`total_pnl ≈ realised_pnl + unrealised_pnl`). An open position is **not** automatically liquidated at the final candle; its unrealised P&L is valued at last close, without hypothetical closing commission.
- Updated the Performance Analysis strip with unrealised and total P&L and open-position status; the trade log now contains one row per closed entry/exit round trip. Trade fill data is still used for chart markers and database history.
- Added four deterministic accounting/annualisation regression tests.

## Cautions

- Annualised Sharpe is **illustrative**, assumes a zero risk-free rate and regularly spaced bars. For stocks, intraday periods approximate 252 regular trading days of 390 minutes. `1h` uses 6.5 equivalent bars per session, not exactly representable actual exchange candles. The metric is unreliable for very short samples (e.g., two days).
- Optimisation is still in-sample and only optimises numerical comparison thresholds.
- Charts still need interactive Windows verification; provider downloads and credentials are not tested by these automated tests.
- No live orders are placed. API keys and `user_data/` must remain out of Git.

## Installation and testing

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -p "test_*.py" -v
python app.py
```

Test the original 8–9 Jan 2025 BTCUSDT 5-minute cache backtest. Check that gross P&L, realised P&L, unrealised P&L and final equity reconcile. The Sharpe figure may differ from previously recorded screenshots if the earlier annualisation factors differed.

Extract this ZIP **outside** `StrategyLab-Prototype` and test it before copying into your `feature/v1.1` branch. Do not overwrite the separate `StrategyLab-NEA` repository.
