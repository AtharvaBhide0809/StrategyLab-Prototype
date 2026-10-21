"""Automated GUI smoke test. Run separately: python gui_smoke_nea.py
It accesses only its bundled sample data and StrategyLab's local test project data.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint,QPointF,Qt,QEvent
from PyQt6.QtGui import QWheelEvent
from app import Main
app=QApplication.instance() or QApplication([])
w=Main();w.show();app.processEvents()
assert w.stack.count()==7 and w.stack.currentIndex()==2
w.run_backtest();app.processEvents()
assert w.result is not None and w.trades.rowCount()>0
w.navigate(1);assert w.stack.currentIndex()==1
for i in range(w.tabs.count()):
 w.tabs.setCurrentIndex(i);app.processEvents()
for freq in ('Daily','Weekly','Monthly','Quarterly','Yearly'):
 w.periodic_frequency.setCurrentText(freq);app.processEvents()
for mode in ('Distribution','Win / loss streaks','Entry hour patterns','Entry weekday patterns','Trade excursions','Trade duration'):
 w.trade_view.setCurrentText(mode);app.processEvents()
all_count=w.trades.rowCount();w.trade_filter.setCurrentIndex(1);profitable=w.trades.rowCount();w.trade_filter.setCurrentIndex(2);losing=w.trades.rowCount()
assert profitable+losing<=all_count
w.trade_filter.setCurrentIndex(0);w.highlight_trade(0,0);assert w.stack.currentIndex()==0
slider=w.price_slider;slider.setValue(min(120,slider.maximum()));app.processEvents()
def wheel(direction):
 delta=120*direction
 event=QWheelEvent(QPointF(10,10),QPointF(10,10),QPoint(0,0),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
 app.sendEvent(slider,event);app.processEvents()
if slider.maximum()>200:
 before=slider.value();wheel(+1);up=slider.value();wheel(-1);down=slider.value()
 assert up>before and down==before,(before,up,down)
w.navigate(3);w.rsi_period.setValue(22);w.sma_period.setValue(35);w.insert_adjustable_strategy()
assert 'RSI_22' in w.editor.toPlainText() and 'SMA_35' in w.editor.toPlainText()
print('GUI_SMOKE_PASS: pages, backtest, analytics, filters, chart jumps, bidirectional wheel, no-code indicator sliders')
w.close()
