# StrategyLab v2.0 — Release checklist (2026-10-21)

## Source baseline
Input: `StrategyLab_v2_NEA_consolidated_testfix(1).zip`. The sole application-source change in this package corrects the **Settings** help text to use `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY`, matching `data_sources.py`. No market provider or backtesting logic changed.

## Verified independently in this session
- Archive integrity verified.
- Unittest: 63 cases, 61 passed, 2 skipped in the headless environment, 0 failures; user's previous Windows run passed all 63.
- Deterministic benchmark on this Linux runtime: parser 0.0004 sec; 5-year daily backtest 0.0049 sec; genetic optimiser 50 x 30 2.5977 sec; benchmark is not proof of identical performance on live historical data.
- Database benchmark: 100 strategies saved; 2,000 fills (1,000 round trips); zero foreign-key errors.
- Previous full audit (`StrategyLab_v2_final_source_audit.md`) supports calculation accuracy for independently checked SMA, RSI, MACD reference series, with choice-of-seeding caveats.
- Prior user's Windows acceptance: all nine GUI workflows, persistence, offline replay and physical wheel direction passed.

## Items which cannot truthfully be certified here
1. Credentialed Alpaca AAPL historical download, cache reuse and offline replay; user must provide credentials locally, without sharing secrets.
2. Standalone `.exe` creation and launch on Windows. A reproducible `build_windows.ps1` is included. A built executable has NOT been verified here.
3. Genuine client questionnaire scoring >=8/10 on visual clarity and usability.
4. Formal strict 3NF of every logical stored attribute is NOT claimed: the core relational keys support 3NF-like normalisation but settings and cached statistics are opaque JSON text. Discuss and justify this tradeoff in the NEA.

## Windows source test commands
```powershell
cd "$HOME\Downloads\StrategyLab_v2_release_ready\StrategyLab_v2.0_chart_fix"
python -m unittest discover -p "test_*.py" -v
python benchmark_nea.py
python benchmark_database.py
python gui_smoke_nea.py
python app.py
```
If folder extraction name differs, use `Get-ChildItem -Directory` to identify the inner application folder.

## Windows executable build
```powershell
cd "$HOME\Downloads\StrategyLab_v2_release_ready\StrategyLab_v2.0_chart_fix"
.\build_windows.ps1
& ".\dist\StrategyLab_v2\StrategyLab_v2.exe"
```
Build requires internet for PyInstaller installation unless installed already. Do not claim standalone deliverable until this binary launches and can save/load and backtest.

## Alpaca data verification: safely set credentials for this terminal session only
Never put credentials into repository, screenshots, logs or ChatGPT. Obtain your own provider credentials with suitable read-only market-data access. In an **interactive PowerShell session**:
```powershell
$env:ALPACA_API_KEY_ID = Read-Host "Alpaca key ID"
$secure = Read-Host "Alpaca secret key (input hidden)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $env:ALPACA_API_SECRET_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr); Remove-Variable ptr,secure -ErrorAction SilentlyContinue }
python app.py
```
Within StrategyLab choose **US stocks (Alpaca IEX)**, **AAPL**, and a short market-open interval; switch **Offline** off and click **Download historical data**. Confirm real candles appear, run a backtest, then switch Offline on and rerun without downloading. The data source uses `data.alpaca.markets` historical bars with `feed=iex`; your plan may constrain which historical dates/times are accessible. Any error must be captured WITHOUT keys.

After closing the app, clear credentials from the PowerShell session:
```powershell
Remove-Item Env:ALPACA_API_KEY_ID -ErrorAction SilentlyContinue
Remove-Item Env:ALPACA_API_SECRET_KEY -ErrorAction SilentlyContinue
```
Run independent checkout on cached sample data if the vendor's free tier does not permit the requested period. The provider is a third-party service; success cannot be promised.

## Client evaluation
Have the actual named client use the app and score separately clarity/legibility and ease-of-use out of ten. Record date, tasks, scores, specific observations and agreed follow-ups. Do not invent client responses.

## GitHub release (only after the outstanding checks are resolved or transparently noted)
Do not blindly overwrite the existing v1.1.1 repository. From the original `StrategyLab-Prototype` repository, ensure `feature/v2.0` is selected and clean, copy reviewed source files from the new candidate (excluding user_data, credentials, __pycache__, dist, build), test again, inspect git diff, then commit/push. Tag `v2.0` only after release acceptance. Preserve earlier release tags.
