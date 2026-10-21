# StrategyLab v2.0 — TradingView-inspired Stage 1 candidate

This is an educational reference application; no live trading or brokerage orders.

## Changes
- Strategy Analytics shows prominent grouped metrics for account results, equity, realised/unrealised P/L, win/loss statistics, risk and periodic performance.
- The original six analytics report tabs are preserved. Trade Distribution now has three modes: distribution, streaks, and entry-hour patterns.
- Periodic Returns supports daily, weekly and monthly groupings. Small datasets use narrow bars rather than stretching one month across an entire chart.
- Improved tab styling and consistent summary cards.
- The history slider wheel handler is exercised with positive and negative Qt wheel events, although physical Windows hardware behaviour must still be checked.
- The previously tested genetic optimiser, out-of-sample validation, next-open backtester and SQLite persistence remain present.

## Independent checks (Linux/PyQt6 virtual display)
- 54 unittest cases passed, including new calendar-return and GUI interaction checks.
- Application launched; backtest executed on bundled *synthetic* 950-candle data; all six analytics tabs rendered to images.
- Daily/weekly/monthly frequency selections and trade-analysis modes were exercised.
- Wheel event simulation from midpoint: 265 -> 307 on positive delta, then 307 -> 265 on negative delta.
- Python syntax compilation passed.

## Important limitations
- GUI screenshots originate from a virtual Linux Qt platform rather than Windows. Font rendering, sizing and wheel devices can behave differently on Windows.
- This is a TradingView-inspired original interface, not an exact replica and not a guarantee of feature parity.
- 54 passing tests do not establish accuracy of all market assumptions; provider network calls and brokerage connections are not validated.
- Intraday entry-hour breakdown uses source timestamps and should not be interpreted as exchange-local time when the source is UTC.
- Monthly/weekly periods may be incomplete at sample boundaries.
- No margin/leveraged trading model is included. Do not infer live trading suitability.
- The interface still uses Matplotlib; physical responsiveness must be measured on Windows.

## Windows quick start
Extract the ZIP, open the inner StrategyLab_v2.0_chart_fix directory:

```powershell
python -m unittest discover -p "test_*.py" -v
python app.py
```

## Targeted Windows acceptance checks
1. Backtest on cached BTCUSDT candles; verify the six analytics tabs, their metric cards and no errors.
2. Try Daily/Weekly/Monthly aggregation and the three trade analysis modes.
3. Use the history slider wheel both directions from the middle, as well as drag/Older/Newer/Latest; report any reversed or one-way movement.
4. Run genetic optimisation, apply rules and save/reload a strategy; verify results persist.
5. Note any clipped text, lag or oversized charts at your actual screen scaling.

Do not overwrite the tagged v1.1.1 repository until the Windows acceptance pass succeeds.
