# Start here — StrategyLab v2.0 NEA requirements candidate

This folder is the **source folder**. Open it in VS Code. See `NEA_CONSOLIDATED_RELEASE_NOTES.md` for all changes, limitations, and reproducible results.

## From PowerShell in Downloads
```powershell
cd "$HOME\Downloads\StrategyLab_v2_NEA_consolidated\StrategyLab_v2.0_chart_fix"
python -m unittest discover -p "test_*.py" -v
python benchmark_nea.py
python benchmark_database.py
python gui_smoke_nea.py
python app.py
```
Expected 63 tests, of which 2 are skipped by the pre-existing baseline; GUI smoke uses your installed PyQt6.

This build starts with Strategy Editor, as specified by the NEA success criteria. The dashboard and analytics remain available from the left sidebar.
