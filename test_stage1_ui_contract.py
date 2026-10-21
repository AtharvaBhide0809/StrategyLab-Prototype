"""Stage 1 structural contracts that run without the optional Qt desktop dependency."""
import ast
import unittest
from pathlib import Path

SOURCE=(Path(__file__).resolve().parent/'app.py').read_text(encoding='utf-8')
TREE=ast.parse(SOURCE)
MAIN=next(node for node in TREE.body if isinstance(node,ast.ClassDef) and node.name=='Main')
METHODS={n.name:n for n in MAIN.body if isinstance(n,ast.FunctionDef)}

class Stage1UIContract(unittest.TestCase):
    def test_all_advanced_analytics_widgets_are_constructed(self):
        creation=METHODS['build_analytics']
        assigned={target.attr for node in ast.walk(creation) if isinstance(node,ast.Assign)
                  for target in node.targets if isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name) and target.value.id=='self'}
        for name in ('risk_metrics','risk_plot','periodic_metrics','periodic_plot'):
            with self.subTest(name=name):
                self.assertIn(name,assigned)
        self.assertIn('self.plot_advanced()',ast.get_source_segment(SOURCE,METHODS['run_backtest']))

    def test_advanced_reports_reset_on_market_change(self):
        for name in ('risk_metrics','periodic_metrics','risk_plot','periodic_plot'):
            self.assertIn(name,ast.get_source_segment(SOURCE,METHODS['clear_results']))
            self.assertIn(name,ast.get_source_segment(SOURCE,METHODS['selection_changed']))

    def test_mouse_wheel_filter_is_installed(self):
        dashboard=ast.get_source_segment(SOURCE,METHODS['build_dashboard'])
        self.assertIn('self.price_slider.installEventFilter(self)',dashboard)
        filter_body=ast.get_source_segment(SOURCE,METHODS['eventFilter'])
        self.assertIn('event.angleDelta().y()',filter_body)
        self.assertIn('delta>0',filter_body)
        self.assertIn('else -step',filter_body)

    def test_sma_overlays_are_cached(self):
        plot=ast.get_source_segment(SOURCE,METHODS['plot_candles'])
        self.assertIn('self._indicator_cache_key',plot)
        self.assertIn('self._indicator_cache',plot)

    def test_worker_optimisation_configuration_is_snapshotted(self):
        src=ast.get_source_segment(SOURCE,METHODS['run_optimisation'])
        self.assertIn('training_fraction=self.train_pct.value()/100',src)
        self.assertIn('minimum_trades=self.min_trades.value()',src)
        self.assertIn('complexity_penalty=self.penalty.value()',src)
        worker=src[src.index('self.opt_job=Job('):]
        for expression in ('self.train_pct.value()', 'self.min_trades.value()', 'self.penalty.value()'):
            self.assertNotIn(expression,worker)

if __name__=='__main__': unittest.main()
