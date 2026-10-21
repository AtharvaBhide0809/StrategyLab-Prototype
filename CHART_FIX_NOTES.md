# StrategyLab v2.0 chart-navigation fix (testing build)

- Renders all candles **in the selected viewport**, rather than permanently omitting candles outside the newest 420.
- Uses two batch collections for candle bodies and wicks to reduce repaint overhead.
- Older/Newer/Latest buttons and a full-range horizontal scrollbar navigate historical data.
- Matplotlib Pan and Zoom remain available. Finish a drag/zoom and release the mouse to load the corresponding candles. Home/Back/Forward retain Matplotlib standard behaviour but the dedicated history navigator is recommended.
- Y scale automatically reflects the displayed price window.
- Known limitation: very dense chart zoom levels and large datasets may still redraw slowly on lower-end machines. This patch is not yet GUI-tested on the recipient Windows system.

Test with `python -m unittest discover -p "test_*.py" -v` then `python app.py`. Do not overwrite your stable v1.1.1 repository.
