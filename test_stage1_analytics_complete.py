"""New Stage 1 verification: period aggregation and actual Qt widget contract."""
import os
import unittest
from analytics import periodic_returns

class CalendarAggregationTests(unittest.TestCase):
    def test_daily_weekly_monthly_compound(self):
        dates=['2025-01-06T00:00:00+00:00','2025-01-07T00:00:00+00:00','2025-01-13T00:00:00+00:00','2025-02-01T00:00:00+00:00']
        equity=[110,121,133.1,146.41]
        self.assertEqual(len(periodic_returns(dates,equity,100,'daily')),4)
        w=periodic_returns(dates,equity,100,'weekly')
        self.assertEqual(len(w),3)
        self.assertAlmostEqual(w[0][1],21)
        self.assertAlmostEqual(w[1][1],10)
        m=periodic_returns(dates,equity,100,'monthly')
        self.assertAlmostEqual(m[0][1],33.1)
        self.assertAlmostEqual(m[1][1],10)

    def test_invalid_period(self):
        with self.assertRaises(ValueError):
            periodic_returns(['2025-01-01'],[100],100,'hourly')

class GuiContractTests(unittest.TestCase):
    def test_widget_card_and_frequency_wiring(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        try:
            from PyQt6.QtWidgets import QApplication
            from app import Main
        except ImportError:
            self.skipTest('PyQt6 is not present; run in GUI test environment')
        app=QApplication.instance() or QApplication([])
        window=Main()
        self.assertEqual(window.tabs.count(),7)
        self.assertEqual(len(window.overview_cards),4)
        self.assertEqual(len(window.risk_cards),4)
        self.assertEqual(window.periodic_frequency.count(),5)
        window.run_backtest()
        self.assertIsNotNone(window.result)
        self.assertNotEqual(window.overview_cards['pnl'].text(),'—')
        for freq in ['Daily','Weekly','Monthly','Quarterly','Yearly']:
            window.periodic_frequency.setCurrentText(freq)
            self.assertIn(freq.lower(),window.periodic_metrics.text())
        window.close()

if __name__=='__main__':unittest.main()
