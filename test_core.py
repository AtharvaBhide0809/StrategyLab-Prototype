import unittest
from pathlib import Path
from strategy import parse_strategy, StrategyError, evaluate
from engine import load_csv, backtest, rsi, sma

ROOT=Path(__file__).resolve().parent
class TestPrototype(unittest.TestCase):
    def test_parser_and_boolean_precedence(self):
        rules=parse_strategy('buy if RSI < 30 OR CLOSE > SMA_20 AND VOLUME > 5\nsell if RSI > 70')
        values={'RSI':45,'CLOSE':10,'SMA_20':9,'VOLUME':6}
        self.assertTrue(evaluate(rules['BUY'],values))
        values['VOLUME']=1
        self.assertFalse(evaluate(rules['BUY'],values))
    def test_rejects_unknown_indicator(self):
        with self.assertRaises(StrategyError): parse_strategy('BUY IF SECRET < 3\nSELL IF RSI > 70')
    def test_indicators(self):
        self.assertEqual(sma([1,2,3,4],2),[None,1.5,2.5,3.5])
        self.assertEqual(rsi(list(range(1,20)),14)[14],100)
    def test_backtest(self):
        result=backtest('BUY IF CLOSE > 0\nSELL IF CLOSE < 0',load_csv(ROOT/'sample_prices.csv'))
        self.assertEqual(result['trades'][0]['side'],'BUY')
        self.assertEqual(result['trades'][0]['date'],'2022-01-04')
        self.assertEqual(len(result['equity']),950)
        self.assertLessEqual(result['max_drawdown'],0)
if __name__=='__main__': unittest.main()
