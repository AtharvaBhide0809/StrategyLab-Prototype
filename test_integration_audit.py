"""Additional headless integration tests; do not require PyQt6."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from engine import backtest, load_csv
from optimizer import optimise
from strategy import parse_strategy, StrategyError
from storage import Store

ROOT=Path(__file__).resolve().parent
BARS=load_csv(ROOT/'sample_prices.csv')
SOURCE='BUY IF RSI < 40\nSELL IF RSI > 60'

class IntegrationAudit(unittest.TestCase):
    def test_editor_templates_parse(self):
        text=(ROOT/'app.py').read_text()
        tree=ast.parse(text)
        main=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
        method=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='insert_preset')
        expression=next(n.value for n in method.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Dict))
        templates=ast.literal_eval(expression)
        self.assertEqual(len(templates),4)
        for strategy in templates.values(): self.assertEqual(set(parse_strategy(strategy)),{'BUY','SELL'})
    def test_invalid_rule_rejected(self):
        with self.assertRaises(StrategyError):parse_strategy('BUY IF SECRET > 10\nSELL IF RSI > 70')
    def test_end_to_end_backtest_persistence(self):
        result=backtest(SOURCE,BARS)
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'db.sqlite')
            store.save_strategy('Integration',SOURCE,{'capital':10000})
            row=store.strategies()[0]
            self.assertEqual(row[2],SOURCE)
            store.save_run(row[0],'DEMO','1d',result)
            saved=store.runs()[0]
            self.assertEqual(saved[1:3],('DEMO','1d'))
            self.assertAlmostEqual(json.loads(saved[3])['total_return'],result['total_return'])
            store.delete_strategy(row[0]);self.assertEqual(store.strategies(),[])
            self.assertEqual(len(store.runs()),1)
    def test_oos_optimisation_to_editor_parse(self):
        result=optimise(SOURCE,BARS,population=6,generations=3,training_fraction=.7,min_trades=2)
        self.assertTrue(result['validation'])
        parse_strategy(result['source'])
        self.assertLess(result['validation']['train_end'],result['validation']['holdout_start'])
    def test_optimisation_seed_reproducibility(self):
        a=optimise(SOURCE,BARS,population=6,generations=2,training_fraction=.7,min_trades=2,seed=16)
        b=optimise(SOURCE,BARS,population=6,generations=2,training_fraction=.7,min_trades=2,seed=16)
        self.assertEqual((a['source'],a['history']),(b['source'],b['history']))
    def test_chart_window_boundaries_and_marker_indexing(self):
        total=len(BARS);width=420
        for requested in (-999,0,200,total-420,total,100000):
            start=max(0,min(int(requested),total-width));end=start+width
            self.assertEqual(len(BARS[start:end]),width)
            self.assertTrue(0<=start<end<=total)
        date_idx={str(b['date']):i for i,b in enumerate(BARS)}
        result=backtest(SOURCE,BARS)
        self.assertTrue(all(t['date'] in date_idx for t in result['trades']))
    def test_pages_and_actions_defined(self):
        text=(ROOT/'app.py').read_text();tree=ast.parse(text)
        main=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
        methods={n.name for n in main.body if isinstance(n,ast.FunctionDef)}
        for name in ('build_dashboard','build_analytics','build_editor','build_params','build_optimisation','build_saved','build_history','navigate','run_backtest','run_optimisation','use_optimised','plot_candles','refresh_saved','refresh_history'):
            self.assertIn(name,methods)

if __name__=='__main__':unittest.main()

class ThreadSafetyAudit(unittest.TestCase):
    def test_optimiser_gui_settings_snapshotted_before_worker(self):
        text=(ROOT/'app.py').read_text()
        tree=ast.parse(text)
        main=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Main')
        method=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='run_optimisation')
        worker=next(n for n in ast.walk(method) if isinstance(n,ast.Lambda) and 'optimise(' in (ast.get_source_segment(text,n) or ''))
        worker_source=ast.get_source_segment(text,worker)
        for attr in ('self.train_pct.value()', 'self.min_trades.value()', 'self.penalty.value()'):
            self.assertNotIn(attr,worker_source)
