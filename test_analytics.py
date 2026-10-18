import unittest
from analytics import trade_metrics
class MetricsTests(unittest.TestCase):
 def test_profit_factor(self):
  items=[{'side':'SELL','pnl':20},{'side':'SELL','pnl':-10},{'side':'BUY','pnl':None}]
  m=trade_metrics(items)
  self.assertEqual(m['profit_factor'],2)
  self.assertEqual(m['net_pnl'],10)
  self.assertEqual(m['expectancy'],5)
 def test_no_closed_trades(self):
  m=trade_metrics([])
  self.assertIsNone(m['profit_factor'])
  self.assertIsNone(m['expectancy'])
if __name__=='__main__':unittest.main()
