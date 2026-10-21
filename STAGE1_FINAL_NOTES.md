# StrategyLab v2.0 — consolidated Stage 1 acceptance candidate

This is an educational reference app. No live trades or brokerage execution.

## Integrated changes
- Dedicated uncluttered dashboard and a separate Strategy Analytics page.
- Completed six Strategy Analytics report tabs: Equity and drawdown, Completed trades, Performance analysis, Trade distribution, Risk and benchmarking, Periodic returns.
- **Critical fix:** the previous Stage 1 archive called `plot_advanced()` after a backtest without constructing `risk_metrics`, `risk_plot`, `periodic_metrics`, and `periodic_plot`. Those widgets are now created and wired.
- Optimisation settings are captured before creating the worker. Failed runs reset the status, and stale optimised strategy text is cleared.
- Chart wheel handler is installed on the history slider. Wheel-up advances, wheel-down moves backward; endpoints are clamped automatically by Qt. Physical-wheel direction still requires Windows verification.
- SMA overlays are cached across viewport changes to avoid recalculating indicators for every history-window move.
- Switching market selections resets analytics and prevents stale reports from appearing under new market data.
- Additional static source contracts catch omissions in analytics/widget creation and essential UI wiring.

## Verification
- `python -m unittest discover -p "test_*.py" -v`: 50 tests passed in the build environment.
- `python -m compileall -q .`: passed.
- Qt was not installed in the build environment, so real PyQt6 rendering, screenshot inspection, mouse wheel, and Windows UI interactions **have not** been verified. No claim of full GUI acceptance is made.
- Historical provider network integration remains unavailable for live validation; existing provider tests use mocks.

## Single Windows acceptance pass
1. Extract ZIP **outside** your Git repository, open the inner `StrategyLab_v2.0_chart_fix` directory in VS Code.
2. Execute `python -m unittest discover -p "test_*.py" -v`; expect **50 tests**, not 0.
3. Execute `python app.py` and ensure the application launches without exception.
4. In Dashboard, load cached BTCUSDT/5m data (or open `sample_prices.csv`), run a backtest, and verify summary and candlestick markers.
5. In Strategy Analytics, open **all six** tabs; the **Risk and benchmarking** and **Periodic returns** tabs must populate without an error message.
6. Select another market/symbol: previous performance and risk reports must no longer appear as if they belong to the new symbol.
7. Change the history slider with wheel-up and wheel-down; each direction should be opposite. Drag slider, click Older/Newer/Latest; verify candles remain visible throughout.
8. Test strategy template selection and syntax validation; run a small optimisation and copy optimised rules into the editor.
9. Save and reload a strategy, then check History/Settings after a backtest.
10. Report any issue with exact action, visible result, and full terminal traceback. Minor lag may be recorded for a later polish pass.

## Known limitations / deferred work
- A real TradingView-equivalent high-frame-rate chart is outside this Matplotlib-based candidate.
- The sortino/risk metrics remain educational simplifications; no margin, live orders, stock corporate action engine or brokerage features.
- Visual polish cannot be certified without launching the real GUI; actual Windows behaviour is an acceptance gate before v2.0 release.
- A final GitHub release and tag should be performed only after critical Windows acceptance checks pass.
