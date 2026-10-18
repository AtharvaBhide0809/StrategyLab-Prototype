import unittest, tempfile
from pathlib import Path
from engine import load_csv,backtest
from storage import Store
from optimizer import optimise,parameters,apply

SRC='BUY IF CLOSE > 0\nSELL IF CLOSE < 0'
class V1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.bars=load_csv(Path(__file__).with_name('sample_prices.csv'))
    def test_zero_signals(self):
        r=backtest('BUY IF RSI < 0\nSELL IF RSI > 70',self.bars)
        self.assertEqual(r['total_return'],0)
        self.assertEqual(r['closed_trades'],0)
    def test_allocation_leaves_cash(self):
        res=backtest(SRC,self.bars,allocation=.5,fee=0)
        self.assertEqual(res['trades'][0]['side'],'BUY')
        self.assertGreater(min(res['equity']),1000)
    def test_optimizer_generates_valid_rules(self):
        src='BUY IF RSI < 30\nSELL IF RSI > 70'
        outcome=optimise(src,self.bars,population=4,generations=2)
        self.assertEqual(len(outcome['history']),2)
        self.assertGreaterEqual(outcome['evaluations'],4)
    def test_store(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'test.db');store.save_strategy('A',SRC,{'capital':10000})
            self.assertEqual(len(store.strategies()),1)
            r=backtest(SRC,self.bars);store.save_run(store.strategies()[0][0],'DEMO','1d',r)
            self.assertEqual(len(store.runs()),1)
            store.delete_strategy(store.strategies()[0][0]);self.assertEqual(store.strategies(),[])
if __name__=='__main__':unittest.main()
