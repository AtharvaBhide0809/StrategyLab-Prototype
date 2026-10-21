# StrategyLab v2.0 — consolidated NEA-alignment candidate

This is ONE development candidate (not a final release). It is built from `StrategyLab_v2_stage1_TradingView_GUI_candidate.zip`; v1.1.1 and the GitHub repository were not modified.

## Implemented against the P1 / P2 audit
- Strategy Editor is now the startup page (NEA success criterion 1a).
- Extensible `Indicator` class, registered indicator dispatch, SMA, RSI, MACD and rolling-volume (`VOLUME_SMA_N`).
- Misspelling hints for common indicator tokens using fuzzy-match suggestions.
- Filtering completed trades to profitable/losing entries and substring search of entry/exit dates.
- No-code RSI-period and SMA-period sliders which explicitly generate editable pseudocode; no hidden parameter rewrites.
- Search-as-you-type watchlist filtering (not a comprehensive market/security master search).
- Export-selected-saved-strategy as JSON, in addition to editor export.
- Run history has a selectable summary for persisted cached statistics. This does NOT recreate full historical equity/candle plots from stored runs.
- Periodic return views: daily, weekly, monthly, quarterly, yearly.
- Trade distribution: P/L histogram, streaks, hour/weekday patterns, excursion highs/lows, holding duration.
- Growth/trade insights report: average win, average loss, durations, underwater episodes, per-trade bars and cumulative realised P/L.
- Click a completed trade to jump back to the dashboard around the entry/exit and mark it.
- Retained pre-existing overview cards, benchmarking, risk summaries, price chart, optimiser, persistence, and other stages.

## Automated results in assistant Linux container
- `python -m unittest discover -p "test_*.py" -v`: **63 total**, **61 passed**, **2 skipped** (skips originate in existing baseline tests).
- `python gui_smoke_nea.py` using PyQt6 / Qt offscreen: passed through navigation, backtest, all seven analytics pages, weekly/quarterly/yearly controls, trade filters, selected-trade chart jump, wheel up/down, indicator sliders.
- `python benchmark_nea.py` with deterministic generated 1,827-day price series:
  - Parser 1,000-run maximum 0.0003 s (limit < 0.1 s)
  - Five-year daily backtest 0.0045 s (limit < 3 s)
  - Genetic optimiser: 50 generations, population 30, 1.8079 s (limit < 300 s), 530 distinct simulated backtests.
- `python benchmark_database.py`: 100 saved strategies in 0.1296 s; listing 100 in 0.0003 s; 1,000 completed trades (2,000 buy/sell fills) stored in 0.0035 s; no foreign key integrity errors.
- Times are environment/sample specific and are NOT claims about user hardware, provider latency, or complex real-market strategies.
- One reference RSI calculation gives 70.464..., matching the known 70.46 two-decimal example. A broad externally verified indicator reference suite is still needed before claiming all RSI/SMA/MACD outputs accurate to 0.01 on arbitrary data.

## Unverified / limitations
- Windows physical mouse wheel / chart responsiveness must still be checked; Qt offscreen wheel direction test passes, not a Windows guarantee.
- No built Windows standalone `.exe` (Python packages are required).
- Formal third-normal-form assessment: schema has related profiles, strategies, runs and fills, with foreign keys; needs documented functional-dependency analysis and database design evidence.
- Data-provider network retrieval not verified live in this cycle; offline deterministic data and code paths tested.
- Comprehensive ticker search across all available instruments is not supplied; local watchlist filtering and manual ticker entry are.
- Historical report overview shows cached results but cannot reopen full curve snapshots for old runs, because those time series are not persisted.
- String literals / ticker fields are not part of the structured numeric rules language; keyword case tolerance works, but do not claim preservation of arbitrary quoted strings.
- All new plot metrics are descriptive approximations. MFE/MAE uses OHLC highs/lows between recorded trade entry and exit; intrabar ordering and cost adjustments are not inferred.
- Client clarity and ease-of-use scores >=8/10 require actual client evaluation.
- Real Windows performance and the exact NEA benchmarks should be reproduced using included benchmark scripts.
- Strategy linter and user-defined formula indicators remain explicitly optional extensions and are not in this build.
- Actual monthly/quarterly/yearly bar grouping is based on available recorded candle dates; partial periods may be shown.

## Windows exact commands
After extracting the ZIP to Downloads, run from **any** PowerShell directory:

```powershell
cd "$HOME\Downloads\StrategyLab_v2_NEA_consolidated\StrategyLab_v2.0_chart_fix"
python -m unittest discover -p "test_*.py" -v
python benchmark_nea.py
python benchmark_database.py
python gui_smoke_nea.py
python app.py
```

If your extraction folder is named differently, use `Get-ChildItem "$HOME\Downloads" -Directory` then correct the path.

## NEA integrity note
This is reference/prototype code. For assessed coursework, the student must follow their exam board's rules, understand and implement their own algorithms where required, preserve an honest development/testing record, and acknowledge assistance as mandated.
