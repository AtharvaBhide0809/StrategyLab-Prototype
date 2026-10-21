import os
import unittest

class VisualWorkflowTests(unittest.TestCase):
    def test_analytics_page_controls(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PyQt6.QtWidgets import QApplication
            from app import Main
        except ImportError:
            self.skipTest('PyQt6 not available')
        app=QApplication.instance() or QApplication([])
        w=Main();w.run_backtest()
        self.assertIsNotNone(w.result)
        w.navigate(1)
        for i in range(6):
            w.tabs.setCurrentIndex(i)
            self.assertEqual(w.tabs.currentIndex(),i)
        for option in ['Distribution','Win / loss streaks','Entry hour patterns']:
            w.trade_view.setCurrentText(option)
            self.assertEqual(w.trade_view.currentText(),option)
        for option in ['Daily','Weekly','Monthly']:
            w.periodic_frequency.setCurrentText(option)
            self.assertIn(option.lower(),w.periodic_metrics.text())
        w.navigate(0)
        w.price_slider.setValue(max(10,w.price_slider.maximum()//2))
        from PyQt6.QtCore import Qt,QPoint,QPointF
        from PyQt6.QtGui import QWheelEvent
        def scroll(delta):
            event=QWheelEvent(QPointF(5,5),QPointF(5,5),QPoint(0,0),QPoint(0,delta),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
            QApplication.sendEvent(w.price_slider,event)
            return w.price_slider.value()
        before=w.price_slider.value()
        forward=scroll(120)
        backward=scroll(-120)
        self.assertGreater(forward,before)
        self.assertEqual(backward,before)
        w.close()

if __name__=='__main__':unittest.main()
