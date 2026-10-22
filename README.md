# StrategyLab v2.0 — Analytics Studio

**Latest release:** [Download StrategyLab v2.0](https://github.com/AtharvaBhide0809/StrategyLab-Prototype/releases/tag/v2.0)

StrategyLab is a desktop application for designing, testing, optimising and analysing rule-based trading strategies using historical stock and cryptocurrency market data.

This version introduces an expanded graphical interface, advanced analytics, historical-data integration and a packaged Windows application.

## Key features:

- **Visual Strategy Editor:** Create and validate trading strategies using structured BUY/SELL rules without writing Python code.
- **Historical Backtesting:** Simulate strategies using historical market data with no live order execution.
- **Strategy Analytics:** Examine equity curves, drawdown, completed trades, profitability, risk metrics and periodic returns.
- **Stock and Cryptocurrency Data:** Retrieve supported historical market data and cache it locally in SQLite.
- **Offline Backtesting:** Reuse downloaded datasets without an internet connection.
- **Genetic Optimisation:** Explore strategy parameters using a genetic algorithm with chronological holdout evaluation.
- **Strategy Management:** Save, reload, export and organise trading strategies.
- **Windows Desktop Application:** Run StrategyLab through a packaged executable.

## Testing and verification:

StrategyLab v2.0 has undergone automated and manual testing:

- 63 automated regression tests passed on Windows.
- Parser, backtester, optimiser and database benchmarks passed.
- Historical-data downloads and backtests verified for AAPL, AMD and NVDA.
- Offline data caching and reproducible backtests verified.
- GUI acceptance testing completed successfully.
- Packaged Windows application extracted, launched and successfully tested.

## Installation:

### Windows:

1. Download `StrategyLab_v2.0_Windows.zip` from the release assets.
2. Extract the entire ZIP.
3. Open the extracted `StrategyLab_v2` folder.
4. Launch `StrategyLab_v2.exe`.

Keep all supporting files inside the extracted application folder.

### Running from source:

1. Download the source code.
2. Install Python and the dependencies listed in `requirements.txt`.
3. Run `python app.py`.

## Historical market data:

- Downloading new US stock-market data requires your own Alpaca API credentials. Configure these locally using the environment-variable names documented in the source code.
- Previously cached data and compatible CSV datasets can be used without Alpaca credentials.
- Never include API keys or secret credentials in shared files.

## Important limitations:

- StrategyLab is intended for educational use and historical strategy research.
- It does not execute real brokerage orders.
- Backtested performance is not a guarantee of future trading profitability.
- Results depend on the available historical dataset, strategy rules and simulation assumptions.
- The packaged Windows application has been tested on the development computer, but compatibility on a separate Windows computer without Python has not been independently verified.

## Development:

StrategyLab was developed as part of an A-Level Computer Science NEA project, demonstrating GUI development, algorithm design, data handling, database persistence, automated testing and software engineering.
