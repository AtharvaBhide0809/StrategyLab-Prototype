"""Stage 1 regression tests for the new analytical views."""
import unittest
from pathlib import Path
from analytics import advanced_report
from engine import load_csv,backtest

ROOT=Path(__file__).resolve().parent

class AdvancedAnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bars=load_csv(ROOT/'sample_prices.csv')
        cls.result=backtest('BUY IF CLOSE > 0\nSELL IF CLOSE < 0',cls.bars)

    def test_monthly_returns_compound_to_final_equity(self):
        report=advanced_report(self.result,10000)
        balance=10000
        for _,pct in report['monthly_returns']:
            balance*=1+pct/100
        self.assertAlmostEqual(balance,self.result['final_equity'],places=6)

    def test_trade_metrics_are_aligned(self):
        report=advanced_report(self.result,10000)
        self.assertEqual(len(report['trade_pnls']),self.result['closed_trades'])
        self.assertEqual(len(report['cumulative_trade_pnl']),self.result['closed_trades'])
        self.assertAlmostEqual(report['relative_return'],self.result['total_return']-self.result['buy_hold'])

    def test_no_trade_dataset(self):
        result=backtest('BUY IF CLOSE < 0\nSELL IF CLOSE > 0',self.bars)
        report=advanced_report(result,10000)
        self.assertEqual(report['longest_win_streak'],0)
        self.assertEqual(report['longest_loss_streak'],0)
        self.assertIsNone(report['best_trade'])
        self.assertIsNone(report['worst_trade'])
        self.assertEqual(report['trade_pnls'],[])

    def test_streaks_and_periodic_math(self):
        sample=dict(dates=['2025-01-01','2025-01-31','2025-02-01','2025-02-28'],equity=[100,110,110,121],
                    completed_trades=[{'pnl':5},{'pnl':8},{'pnl':-2},{'pnl':-3},{'pnl':4}],
                    periods_per_year=252,total_return=21,buy_hold=9)
        out=advanced_report(sample,100)
        self.assertEqual([m for m,_ in out['monthly_returns']],['2025-01','2025-02'])
        for _,percentage in out['monthly_returns']:
            self.assertAlmostEqual(percentage,10)
        self.assertEqual(out['longest_win_streak'],2)
        self.assertEqual(out['longest_loss_streak'],2)
        self.assertEqual(out['max_underwater_bars'],0)

    def test_bad_inputs_rejected(self):
        with self.assertRaises(ValueError):advanced_report(self.result,0)
        with self.assertRaises(ValueError):advanced_report({'dates':[],'equity':[]},100)
        with self.assertRaises(ValueError):advanced_report({'dates':['2025-01'],'equity':[float('nan')]},100)

if __name__=='__main__':unittest.main()
