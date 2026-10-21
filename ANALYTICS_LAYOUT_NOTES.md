# StrategyLab v2.0 — structural analytics layout update

This is an incremental testing candidate built on `StrategyLab_v2.0_chart_fix_testing(1).zip`. It is **not** a final v2.0 release.

- Added **Strategy analytics** as the second navigation page, immediately following Dashboard.
- Dashboard retains market/data selection, key performance figures, the Run backtest action, moving-average overlay, full-height price chart and its historical-navigation controls.
- Existing **Equity and drawdown**, **Completed trades**, **Performance analysis**, and **Trade distribution** components move intact to the new page, using the same underlying backtest result and calculation routines.
- A dashboard shortcut opens analytics; analytics displays a compact run summary. An asset-selection change invalidates the corresponding analytics status.
- Updated Saved strategies and History navigation indices; loading a saved strategy or applying optimised rules now goes to the editor's new index.
- Added static GUI-structure regression tests runnable without PyQt6.

## Still deferred

- The supplied TradingView screenshots are **design references only**. Expanded periodic, benchmarking, streaks and growth/decline charts are not yet implemented.
- The existing history-slider mouse-wheel direction issue and manageable chart/UI lag are unchanged.
- Actual clickable PyQt6 GUI screenshots and Windows acceptance are still pending.

## Test on Windows

1. From the extracted application folder, run `python -m unittest discover -p "test_*.py" -v`.
2. Run `python app.py`.
3. Check the sidebar has Dashboard, Strategy analytics, then Strategy editor.
4. Run a backtest on Dashboard. Verify its plot occupies the main area and the shortcut opens Strategy analytics.
5. Check all four existing report tabs and clicking a completed trade; confirm the dashboard chart focuses on the trade (the chart may remain offscreen on the other page until you navigate back).
6. Save and load a strategy, and copy optimised rules to the editor; ensure those actions open Strategy editor rather than Strategy analytics.
7. Switch data selections and ensure old analytics are not represented as a new backtest.

Do not overwrite the stable tagged v1.1.1 repository or push this testing candidate as a release.
