import unittest
from pathlib import Path
from engine import load_csv, backtest
from optimizer import optimise, parameters, apply
from validation import split_index, validate

SRC='BUY IF RSI < 40\nSELL IF RSI > 60'
BARS=load_csv(Path(__file__).with_name('sample_prices.csv'))

class V2Tests(unittest.TestCase):
    def test_chronological_split(self):
        cut=split_index(BARS,.7)
        self.assertEqual(cut,665)
        self.assertLess(BARS[cut-1]['date'],BARS[cut]['date'])
    def test_bad_split(self):
        with self.assertRaises(ValueError):split_index(BARS,.9)
        with self.assertRaises(ValueError):split_index(BARS[:60],.7)
    def test_no_preholdout_trades(self):
        out=validate('BUY IF CLOSE > 0\nSELL IF CLOSE < 0',BARS)
        self.assertGreaterEqual(out['holdout']['trades'][0]['date'],out['holdout_start'])
        self.assertEqual(len(out['holdout']['equity']),285)
    def test_holdout_account_reconciliation(self):
        r=validate(SRC,BARS)
        h=r['holdout']
        self.assertAlmostEqual(h['total_pnl'],h['realised_pnl']+h['unrealised_pnl'])
        self.assertEqual(h['closed_trades'],len(h['completed_trades']))
        self.assertAlmostEqual(h['total_return'],(h['final_equity']/10000-1)*100)
    def test_split_does_not_change_train(self):
        out=validate(SRC,BARS)
        self.assertEqual(out['training']['equity'],backtest(SRC,BARS[:665])['equity'])
    def test_out_of_sample_not_used_for_fitness(self):
        a=optimise(SRC,BARS,population=4,generations=2,training_fraction=.7)
        b=optimise(SRC,BARS[:665],population=4,generations=2)
        self.assertEqual(a['source'],b['source'])
        self.assertEqual(a['history'],b['history'])
    def test_minimum_trades(self):
        with self.assertRaisesRegex(ValueError,'minimum completed-trade'):
            optimise('BUY IF RSI < 0\nSELL IF RSI > 99999',BARS,population=4,generations=1,min_trades=10000)
    def test_invalid_objective(self):
        with self.assertRaises(ValueError):optimise(SRC,BARS,objective='bogus')
    def test_bounds(self):
        out=optimise(SRC,BARS,population=4,generations=2,bounds=[(25,35),(65,75)])
        self.assertEqual(out['parameters'][0].low,25)
        self.assertIn('source',out)
    def test_oos_has_no_in_sample_trade_leakage(self):
        out=validate('BUY IF CLOSE > 0\nSELL IF CLOSE < 0',BARS)
        self.assertEqual(out['holdout']['trades'][0]['date'],BARS[665]['date'])

if __name__=='__main__':unittest.main()
