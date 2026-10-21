# Run from the application source directory in Windows PowerShell.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.\app.py') -or -not (Test-Path '.\sample_prices.csv')) { throw 'Run this script from the folder containing app.py and sample_prices.csv' }
python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller install failed' }
python -m PyInstaller --noconfirm --clean --onedir --windowed --name StrategyLab_v2 --add-data 'sample_prices.csv;.' app.py
if ($LASTEXITCODE -ne 0) { throw 'Windows executable build failed' }
Write-Host 'Built: .\dist\StrategyLab_v2\StrategyLab_v2.exe'
Write-Host 'Verify it launches and that strategy storage and offline replay work.'
Write-Host 'The bundled source currently stores user_data near its program assets. Keep the extracted directory writable and BACK UP user_data before replacing builds.'
