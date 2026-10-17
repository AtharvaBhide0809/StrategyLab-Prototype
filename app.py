"""Run with: python app.py (requires PyQt6 and matplotlib)."""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QSplitter, QFrame)
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from engine import load_csv, backtest

EXAMPLE = 'BUY IF RSI < 30 AND SMA_20 > SMA_50\nSELL IF RSI > 65 OR SMA_20 < SMA_50'
ROOT = Path(__file__).resolve().parent

class BacktestApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('StrategyLab — NEA Prototype')
        self.resize(1200, 780)
        self.csv_path = ROOT / 'sample_prices.csv'
        self.bars = load_csv(self.csv_path)
        host=QWidget(); self.setCentralWidget(host)
        main=QVBoxLayout(host)
        title=QLabel('StrategyLab  /  Historical Strategy Tester')
        title.setStyleSheet('font-size: 23px; font-weight: 700; padding: 8px 0;')
        main.addWidget(title)
        self.file_label=QLabel('Dataset: sample_prices.csv (SYNTHETIC DEMO DATA — not actual market prices)')
        self.file_label.setStyleSheet('color: #b45309;')
        main.addWidget(self.file_label)
        actions=QHBoxLayout()
        load=QPushButton('Load historical CSV'); load.clicked.connect(self.load_file); actions.addWidget(load)
        example=QPushButton('Reset example'); example.clicked.connect(lambda:self.editor.setPlainText(EXAMPLE)); actions.addWidget(example)
        run=QPushButton('▶ Run backtest'); run.setObjectName('run'); run.clicked.connect(self.run_test); actions.addWidget(run)
        actions.addStretch(); main.addLayout(actions)
        split=QSplitter(Qt.Orientation.Horizontal); main.addWidget(split,1)
        left=QWidget(); left_layout=QVBoxLayout(left)
        left_layout.addWidget(QLabel('STRATEGY RULES'))
        self.editor=QTextEdit(); self.editor.setPlainText(EXAMPLE)
        self.editor.setStyleSheet('font-family: Consolas, monospace; font-size: 14px;')
        left_layout.addWidget(self.editor, 1)
        helpbox=QLabel('Syntax: BUY IF condition / SELL IF condition\n'
                       'Indicators: CLOSE, VOLUME, RSI, RSI_14, SMA_20, SMA_50, MACD, MACD_SIGNAL\n'
                       'Operators: >  <  >=  <=  ==  !=  AND  OR  NOT  ( )\n'
                       'Example: BUY IF (RSI < 30 OR CLOSE > SMA_20) AND VOLUME > 5000\n'
                       'One open long position at a time; 0.1% fee per order.')
        helpbox.setWordWrap(True); helpbox.setStyleSheet('color: #aeb9ca; line-height: 1.5;')
        left_layout.addWidget(helpbox)
        split.addWidget(left)
        right=QWidget(); right_layout=QVBoxLayout(right)
        self.stats=QLabel('Run a strategy to see performance statistics.')
        self.stats.setWordWrap(True); self.stats.setStyleSheet('font-size: 14px; padding: 8px;')
        right_layout.addWidget(self.stats)
        tabs=QTabWidget(); right_layout.addWidget(tabs,1)
        fig=Figure(figsize=(7,6), tight_layout=True)
        self.ax=fig.subplots(2,1,sharex=True)
        self.canvas=FigureCanvasQTAgg(fig); tabs.addTab(self.canvas,'Performance charts')
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(['Date','Side','Price','Quantity','Realised P/L'])
        self.table.horizontalHeader().setStretchLastSection(True)
        tabs.addTab(self.table,'Trade log')
        split.addWidget(right); split.setSizes([390,790])
        self.setStyleSheet('QMainWindow, QWidget {background:#111827; color:#e5e7eb;} '
            'QTextEdit, QTableWidget, QTabWidget::pane {background:#1f2937; border:1px solid #374151;} '
            'QPushButton {background:#374151; padding:10px 14px; border-radius:6px;} '
            'QPushButton:hover {background:#4b5563;} QPushButton#run {background:#2563eb;} '
            'QTabBar::tab {padding:9px; background:#273448;} QTabBar::tab:selected {background:#2563eb;}')
        self.run_test()

    def load_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Select daily OHLCV CSV',str(ROOT),'CSV files (*.csv)')
        if not path: return
        try: bars=load_csv(path)
        except Exception as e:
            QMessageBox.warning(self,'CSV error',str(e)); return
        self.bars=bars; self.csv_path=Path(path)
        self.file_label.setText('Dataset: '+path)
        self.file_label.setStyleSheet('color:#9ca3af;')
        self.run_test()

    def run_test(self):
        try: res=backtest(self.editor.toPlainText(), self.bars)
        except Exception as e:
            QMessageBox.warning(self,'Strategy / backtest error',str(e)); return
        self.stats.setText(f"Return: {res['total_return']:+.2f}%    |    Buy & hold: {res['buy_hold']:+.2f}%\n"
            f"Sharpe: {res['sharpe']:.2f}    |    Max drawdown: {res['max_drawdown']:.2f}%\n"
            f"Completed trades: {res['closed_trades']}    |    Win rate: {res['win_rate']:.1f}%")
        for ax in self.ax:
            ax.clear(); ax.set_facecolor('#1f2937'); ax.tick_params(colors='#d1d5db')
            for spine in ax.spines.values(): spine.set_color('#64748b')
        indexes=list(range(len(res['equity'])))
        self.ax[0].plot(indexes,res['equity'],color='#60a5fa',label='Strategy equity')
        first=self.bars[0]['close']
        buy_hold=[10000*b['close']/first for b in self.bars]
        self.ax[0].plot(indexes,buy_hold,color='#fbbf24',alpha=.8,label='Buy & hold')
        self.ax[0].legend(facecolor='#1f2937',labelcolor='white')
        self.ax[0].set_ylabel('Equity (£)',color='#d1d5db')
        self.ax[1].fill_between(indexes,res['drawdown'],color='#f87171',alpha=.65)
        self.ax[1].set_ylabel('Drawdown (%)',color='#d1d5db')
        self.ax[1].set_xlabel('Daily bars (chronological)',color='#d1d5db')
        self.canvas.draw()
        self.table.setRowCount(len(res['trades']))
        for i,t in enumerate(res['trades']):
            vals=[t['date'],t['side'],f"{t['price']:.2f}",f"{t['quantity']:.4f}",
                  '—' if t['pnl'] is None else f"{t['pnl']:+.2f}"]
            for j,val in enumerate(vals): self.table.setItem(i,j,QTableWidgetItem(val))

if __name__=='__main__':
    app=QApplication(sys.argv)
    window=BacktestApp(); window.show()
    sys.exit(app.exec())
