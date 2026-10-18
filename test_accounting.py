"""Deterministic regression checks for returns, open positions and annualisation."""
import math
import unittest
from engine import backtest, annualisation_periods


def bars_with_prices(prices):
    return [dict(date=f'2025-01-{(i // 288)+1:02d}T{(i % 288)//12:02d}:{((i % 12)*5):02d}:00+00:00',
                 open=p,high=p,low=p,close=p,volume=10) for i,p in enumerate(prices)]


class AccountingTests(unittest.TestCase):
    def test_periods(self):
        self.assertEqual(annualisation_periods('crypto','5m'), 105120)
        self.assertEqual(annualisation_periods('crypto','1d'), 365)
        self.assertEqual(annualisation_periods('stocks','5m'), 19656)
        self.assertEqual(annualisation_periods('stocks','1d'), 252)

    def test_open_position_reconciles(self):
        result=backtest('BUY IF CLOSE > 0\nSELL IF CLOSE < 0',
                        bars_with_prices([100]*35+[95]*15),initial=10000,fee=.001,
                        asset_type='crypto',timeframe='5m')
        self.assertTrue(result['open_position'])
        self.assertEqual(result['closed_trades'],0)
        self.assertEqual(result['realised_pnl'],0)
        self.assertAlmostEqual(result['total_pnl'],result['unrealised_pnl'])
        self.assertAlmostEqual(result['final_equity'],10000+result['total_pnl'])
        self.assertEqual(len(result['completed_trades']),0)

    def test_round_trip_and_costs(self):
        result=backtest('BUY IF CLOSE > 100\nSELL IF CLOSE < 99',
                        bars_with_prices([110]*35+[98]*35),initial=10000,fee=.001)
        self.assertEqual(result['closed_trades'],1)
        self.assertFalse(result['open_position'])
        self.assertAlmostEqual(result['total_pnl'],result['realised_pnl'])
        t=result['completed_trades'][0]
        self.assertAlmostEqual(t['pnl'],result['realised_pnl'])
        self.assertEqual(t['entry_price'],110)
        self.assertEqual(t['exit_price'],98)
        self.assertEqual(result['losing_trades'],1)

    def test_no_trades(self):
        result=backtest('BUY IF CLOSE < 0\nSELL IF CLOSE > 0',bars_with_prices([100]*40))
        self.assertEqual(result['total_pnl'],0)
        self.assertFalse(result['open_position'])
        self.assertIsNone(result['profit_factor'])

if __name__=='__main__': unittest.main()
