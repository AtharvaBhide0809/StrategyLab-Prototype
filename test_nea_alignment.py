import unittest
from pathlib import Path
from datetime import datetime,timedelta
from engine import Indicator,register_indicator,indicators,load_csv,sma,rsi,backtest
from strategy import parse_strategy,StrategyError
from analytics import periodic_returns,trade_excursions,trade_durations,drawdown_segments
BARS=load_csv(Path(__file__).with_name('sample_prices.csv'))
class NeaAlignment(unittest.TestCase):
 def test_rsi_known_reference(self):
  # Public-domain Wilder RSI worked-series reference, rounded to two decimals.
  prices=[44.34,44.09,44.15,43.61,44.33,44.83,45.10,45.42,45.84,46.08,45.89,46.03,45.61,46.28,46.28]
  self.assertAlmostEqual(rsi(prices)[14],70.46,delta=.01)
 def test_sma_known_reference(self):
  self.assertEqual(sma([1,2,3,4,5],3),[None,None,2,3,4])
 def test_spelling_suggestion(self):
  with self.assertRaisesRegex(StrategyError,'Did you mean RSI'):
   parse_strategy('BUY IF RSiI < 30\nSELL IF RSI > 70')
 def test_volume_average(self):
  data=indicators(BARS[:40],{'VOLUME_SMA_5'})
  self.assertAlmostEqual(data['VOLUME_SMA_5'][4],sum(b['volume'] for b in BARS[:5])/5)
 def test_indicator_extension(self):
  class Example(Indicator):
   def matches(self,name):return name=='EXAMPLE'
   def calculate(self,bars,name,cache):return [3]*len(bars)
  obj=Example();register_indicator(obj)
  self.assertEqual(indicators(BARS[:40],{'EXAMPLE'})['EXAMPLE'][0],3)
  from engine import INDICATOR_REGISTRY
  INDICATOR_REGISTRY.remove(obj)
 def test_periodic_frequencies(self):
  dates=['2025-01-01','2025-04-01','2026-01-01']; values=[110,121,133.1]
  self.assertEqual(len(periodic_returns(dates,values,100,'quarterly')),3)
  self.assertEqual(len(periodic_returns(dates,values,100,'yearly')),2)
 def test_excursions_and_durations(self):
  tr=[dict(entry_date=BARS[10]['date'],exit_date=BARS[12]['date'],entry_price=BARS[10]['open'])]
  excursions=trade_excursions(tr,BARS)
  self.assertEqual(len(excursions),1)
  self.assertLessEqual(excursions[0][1],excursions[0][0])
  self.assertGreaterEqual(trade_durations(tr)[0],0)
 def test_drawdown_episodes(self):
  self.assertEqual(drawdown_segments([101,99,98,103,102],100),[2,1])
 def test_integrated_volume_strategy(self):
  result=backtest('BUY IF VOLUME > VOLUME_SMA_10\nSELL IF VOLUME < VOLUME_SMA_10',BARS)
  self.assertEqual(len(result['equity']),len(BARS))
if __name__=='__main__':unittest.main()
