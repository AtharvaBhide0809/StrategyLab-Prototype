# StrategyLab Reference v1.1 — update notes

This is an AI-generated reference implementation for exploration and testing, not independently authored assessed coursework.

## New in v1.1
- Single-click watchlist selection and explicit cache-first chart changes; old BTC candles cannot be presented as AAPL.
- Uncached assets show an empty chart and a manual download action. Automatic downloading remains a future improvement.
- Background downloads have an indeterminate activity bar, duplicate-click protection, status messages and error notifications. Progress is indeterminate because the providers do not expose consistent progress.
- Download completion does **not** automatically backtest large datasets. Use Run backtest after loading.
- Candlestick plot renders only the last 420 candles, avoiding excessive GUI patch creation. Equity/drawdown can still be expensive for massive histories.
- Performance analysis and trade return distribution tabs, with gross profits, gross losses, profit factor, expectancy and cumulative realised P/L.

## Remaining limitations / cautions
- Network downloads may still be slow and provider access can fail or be blocked. Alpaca IEX needs API credentials; Binance access depends on availability in your location.
- Cancellation of requests, real percentage progress, cache gap downloads, full interactive date-axis charts, trade selection highlighting and advanced strategy analytics are NOT yet implemented.
- Changing an asset marks previous metrics invalid; pressing Run backtest recomputes them.
- Data download archives can be large; for a first network test use 1 day of 5-minute data.
- All code should be reviewed and tested on Windows before merging into master.

## Install / test
`python -m pip install -r requirements.txt` then `python app.py`. Run `python -m unittest discover -v` for automated tests.

To upgrade your `feature/v1.1` repository, copy the files from this extracted folder into the existing local repository without deleting its `.git` directory. Test before committing.
