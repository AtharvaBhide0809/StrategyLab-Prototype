"""Static GUI integration checks usable even when PyQt6 is unavailable."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'app.py').read_text(encoding='utf-8')
        main = next(n for n in ast.parse(cls.source).body
                    if isinstance(n, ast.ClassDef) and n.name == 'Main')
        cls.methods = {n.name: ast.get_source_segment(cls.source, n) for n in main.body
                       if isinstance(n, ast.FunctionDef)}

    def test_analytics_page_is_a_distinct_page(self):
        self.assertIn("self.page('Strategy Analytics')", self.methods['build_analytics'])
        self.assertIn('self.build_dashboard();self.build_analytics();self.build_editor()', self.methods['__init__'])
        self.assertIn("'Dashboard','Strategy analytics','Strategy editor'", self.methods['__init__'])

    def test_chart_and_analytics_are_separate(self):
        self.assertIn('v.addWidget(price_panel,1)', self.methods['build_dashboard'])
        self.assertNotIn('self.tabs=QTabWidget()', self.methods['build_dashboard'])
        self.assertIn('self.tabs=QTabWidget()', self.methods['build_analytics'])
        for name in ('Equity and drawdown', 'Completed trades', 'Performance analysis', 'Trade distribution'):
            self.assertIn(name, self.methods['build_analytics'])

    def test_saved_strategy_navigation_indices_updated(self):
        self.assertIn('if i==5:self.refresh_saved()', self.methods['navigate'])
        self.assertIn('if i==6:self.refresh_history()', self.methods['navigate'])
        self.assertIn('self.navigate(2)', self.methods['load_saved'])
        self.assertIn('self.navigate(2)', self.methods['use_optimised'])

    def test_result_lifecycle_updates_analytics(self):
        self.assertIn('self.analytics_summary.setText', self.methods['run_backtest'])
        self.assertIn('self.analytics_summary.setText', self.methods['clear_results'])
        self.assertIn('self.plot_equity();self.fill_trades();self.plot_analysis()', self.methods['run_backtest'])


if __name__ == '__main__':
    unittest.main()
