"""StrategyLab v2.0 — educational, paper-only backtesting desktop application."""
import sys,json,csv,os
from pathlib import Path
from datetime import date
from PyQt6.QtCore import Qt,QDate,QTimer,QThread,pyqtSignal,QEvent
from PyQt6.QtGui import QColor,QBrush
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
 QPlainTextEdit,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QTabWidget,QSplitter,QFrame,QComboBox,QLineEdit,
 QDateEdit,QCheckBox,QSlider,QStackedWidget,QListWidget,QInputDialog,QDoubleSpinBox,QSpinBox,QProgressBar,QHeaderView,QGridLayout,QScrollArea)
from matplotlib.figure import Figure
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from engine import load_csv,backtest,annualisation_periods,indicators
from strategy import parse_strategy, StrategyError
from data_sources import HistoricalDataService,MarketRequest,INTERVALS
from storage import Store
from optimizer import optimise,parameters
from analytics import trade_metrics, advanced_report
from validation import validate

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'user_data'; DATA.mkdir(exist_ok=True)
EXAMPLE='BUY IF RSI < 30 OR CLOSE > SMA_20\nSELL IF RSI > 70'
STYLE='''QWidget{background:#0d111a;color:#dce6f2;font-family:Segoe UI;font-size:13px}QLineEdit,QPlainTextEdit,QComboBox,QDateEdit,QDoubleSpinBox,QSpinBox,QListWidget,QTableWidget{background:#1c2736;border:1px solid #344257;border-radius:5px;padding:5px;color:#e1e8f4}QPushButton{background:#263447;border:1px solid #364c68;border-radius:5px;padding:9px}QPushButton:hover{background:#354961}QPushButton:disabled{color:#718096;background:#202a38}QPushButton:pressed{background:#18529d}QPushButton#primary{background:#2463d5;border:1px solid #3577ee}QPushButton#nav{background:#172233;text-align:left;border:0;padding:13px}QPushButton#nav:checked{background:#1e416f;border-left:3px solid #57a6ff}QTabBar::tab{background:#1a2534;padding:11px 15px;margin-right:3px;border-radius:5px}QTabWidget::pane{border:1px solid #29394c;border-radius:5px}QTabBar::tab:hover{background:#34445a}QTabBar::tab:selected{background:#245ab8}QHeaderView::section{background:#263447;padding:6px;border:0}QTableWidget{gridline-color:#354253}QProgressBar{border:1px solid #334155;text-align:center}QProgressBar::chunk{background:#2463d5}'''

class Job(QThread):
    completed=pyqtSignal(object); failed=pyqtSignal(str)
    def __init__(self,fn): super().__init__(); self.fn=fn
    def run(self):
        try:self.completed.emit(self.fn())
        except Exception as ex:self.failed.emit(str(ex))

class Plot(FigureCanvasQTAgg):
    def __init__(self,height=4):
        self.fig=Figure(figsize=(9,height),facecolor='#1c2736',tight_layout=True)
        super().__init__(self.fig)
        self.setStyleSheet('background:#1c2736')
    def axes(self,n=1):
        self.fig.clear(); axes=self.fig.subplots(n,1,sharex=n>1)
        for ax in axes if n>1 else [axes]:
            ax.set_facecolor('#1c2736');ax.tick_params(colors='#a7b9cc',labelsize=8);ax.grid(alpha=.12)
            for spine in ax.spines.values():spine.set_color('#344357')
        return axes

class Main(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle('StrategyLab | v2.0 · Analytics Studio');self.resize(1500,900)
        self.store=Store(DATA/'strategies.sqlite3');self.service=HistoricalDataService(DATA/'candles.sqlite3')
        self.bars=load_csv(ROOT/'sample_prices.csv');self.market='demo';self.timeframe='1d';self.symbol='DEMO';self.result=None;self.saved_id=None;self.busy=False;self.request_id=0
        self.settings={'capital':10000.,'fee':0.001,'slippage':0.,'position':100.}
        shell=QWidget();self.setCentralWidget(shell);row=QHBoxLayout(shell);row.setContentsMargins(0,0,0,0);row.setSpacing(0)
        sidebar=QWidget();sidebar.setFixedWidth(180);sl=QVBoxLayout(sidebar)
        brand=QLabel('◆  StrategyLab');brand.setStyleSheet('font-size:19px;font-weight:bold;color:#74b5ff;padding:16px 4px');sl.addWidget(brand)
        self.stack=QStackedWidget();self.nav=[]
        names=['Dashboard','Strategy analytics','Strategy editor','Parameters','Optimisation','Saved strategies','History / settings']
        for idx,name in enumerate(names):
            btn=QPushButton('  '+name);btn.setObjectName('nav');btn.setCheckable(True)
            btn.clicked.connect(lambda checked,i=idx:self.navigate(i));sl.addWidget(btn);self.nav.append(btn)
        sl.addStretch();sl.addWidget(QLabel('Reference build · No live orders'))
        row.addWidget(sidebar);row.addWidget(self.stack,1)
        watch=QWidget();watch.setFixedWidth(180);wl=QVBoxLayout(watch)
        lbl=QLabel('WATCHLIST');lbl.setStyleSheet('font-weight:bold;color:#9eb7d7');wl.addWidget(lbl)
        self.asset_search=QLineEdit();self.asset_search.setPlaceholderText('Search watchlist symbols');wl.addWidget(self.asset_search)
        self.watch=QListWidget();self.watch.addItems(['BTCUSDT · Crypto','ETHUSDT · Crypto','SOLUSDT · Crypto','AAPL · Stock','AMD · Stock','NVDA · Stock']);self.watch.itemClicked.connect(self.from_watch);wl.addWidget(self.watch)
        self.asset_search.textChanged.connect(self.filter_watchlist)
        wl.addWidget(QLabel('Single-click to select asset.\nMissing candles require manual download.'))
        row.addWidget(watch)
        self.build_dashboard();self.build_analytics();self.build_editor();self.build_params();self.build_optimisation();self.build_saved();self.build_history()
        self.setStyleSheet(STYLE);self.navigate(2);self.interval.currentTextChanged.connect(self.selection_changed);self.start.dateChanged.connect(self.selection_changed);self.end.dateChanged.connect(self.selection_changed);self.symbol_box.editingFinished.connect(self.selection_changed)
        self.statusBar().showMessage('Synthetic demo candles loaded. Live trading is never enabled.')

    def page(self,name):
        w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(15,12,15,12);v.setSpacing(9)
        h=QLabel(name);h.setStyleSheet('font-size:21px;font-weight:700');v.addWidget(h)
        self.stack.addWidget(w);return w,v
    def navigate(self,i):
        self.stack.setCurrentIndex(i)
        for j,b in enumerate(self.nav):b.setChecked(i==j)
        if i==5:self.refresh_saved()
        if i==6:self.refresh_history()
    def toolbar(self,layout):
        r=QHBoxLayout();r.addWidget(QLabel('Market'))
        self.market_combo=QComboBox();self.market_combo.addItems(['Crypto (Binance)','US stocks (Alpaca IEX)']);self.market_combo.currentIndexChanged.connect(self.on_market);r.addWidget(self.market_combo)
        self.symbol_box=QLineEdit('BTCUSDT');self.symbol_box.setMaximumWidth(130);r.addWidget(self.symbol_box)
        self.interval=QComboBox();self.interval.addItems(list(INTERVALS));self.interval.setCurrentText('5m');r.addWidget(self.interval)
        self.start=QDateEdit(QDate(2025,1,1));self.end=QDateEdit(QDate(2025,1,7))
        for d in (self.start,self.end):d.setCalendarPopup(True);r.addWidget(d)
        self.offline=QCheckBox('Offline');r.addWidget(self.offline)
        load=QPushButton('Download historical data');load.clicked.connect(self.download);r.addWidget(load);self.load_btn=load
        csv_btn=QPushButton('Open CSV');csv_btn.clicked.connect(self.open_csv);r.addWidget(csv_btn)
        r.addStretch();layout.addLayout(r)
        self.download_progress=QProgressBar();self.download_progress.setRange(0,0);self.download_progress.setVisible(False);layout.addWidget(self.download_progress)
        self.download_state=QLabel('');layout.addWidget(self.download_state)
        self.dataset=QLabel('DEMO · daily · synthetic OHLCV');self.dataset.setStyleSheet('color:#c6a879');layout.addWidget(self.dataset)
    def build_dashboard(self):
        _,v=self.page('Backtest Dashboard');self.toolbar(v)
        top=QHBoxLayout();self.stats=QLabel('');self.stats.setStyleSheet('font-size:14px;color:#d6e6fa');top.addWidget(self.stats,1)
        run=QPushButton('▶ Run backtest');run.setObjectName('primary');run.clicked.connect(self.run_backtest);top.addWidget(run);v.addLayout(top)
        overlay=QHBoxLayout();self.show_sma=QCheckBox('Overlay SMA 20 / 50');self.show_sma.stateChanged.connect(self.plot_candles);overlay.addWidget(self.show_sma);overlay.addStretch();v.addLayout(overlay)
        analytics_link=QPushButton('Open Strategy Analytics  →')
        analytics_link.clicked.connect(lambda:self.navigate(1))
        v.addWidget(analytics_link)
        self.price_plot=Plot(5);price_panel=QWidget();price_layout=QVBoxLayout(price_panel);price_layout.setContentsMargins(0,0,0,0)
        navigation=QHBoxLayout();self.price_toolbar=NavigationToolbar2QT(self.price_plot,price_panel);navigation.addWidget(self.price_toolbar)
        for label,amount in [('◀ Older',-200),('Newer ▶',200),('Latest',None)]:
            button=QPushButton(label);button.clicked.connect(lambda checked=False,step=amount:self.move_price_window(step));navigation.addWidget(button)
        price_layout.addLayout(navigation)
        self.price_slider=QSlider(Qt.Orientation.Horizontal);self.price_slider.setToolTip('Drag to browse the full candle history');self.price_slider.valueChanged.connect(self.slide_price_window);self.price_slider.installEventFilter(self)
        price_layout.addWidget(self.price_plot);price_layout.addWidget(self.price_slider)
        self.price_window=(0,0);self.price_window_size=420;self._chart_rendering=False;self._chart_pending=False;self._indicator_cache_key=None;self._indicator_cache=None
        self.price_plot.mpl_connect('button_release_event',self.on_price_navigation)
        self.price_plot.mpl_connect('scroll_event',self.on_price_navigation)
        v.addWidget(price_panel,1)

    def metric_cards(self, parent, definitions):
        """Readable summary cards with consistent typography and stable widget references."""
        grid=QGridLayout();grid.setContentsMargins(0,3,0,7);grid.setSpacing(10)
        cards={}
        for i,(key,title) in enumerate(definitions):
            panel=QFrame();panel.setObjectName('metricCard')
            panel.setStyleSheet('QFrame#metricCard{background:#172334;border:1px solid #34445a;border-radius:8px;}QFrame#metricCard QLabel{background:transparent;border:none;}')
            layout=QVBoxLayout(panel);layout.setContentsMargins(16,12,12,13);layout.setSpacing(5)
            caption=QLabel(title.upper());caption.setStyleSheet('font-size:11px;font-weight:600;color:#91a6c0;')
            value=QLabel('—');value.setObjectName('metric_'+key)
            value.setStyleSheet('font-size:20px;font-weight:700;color:#f2f7ff;')
            layout.addWidget(caption);layout.addWidget(value)
            grid.addWidget(panel,i//4,i%4);cards[key]=value
        parent.addLayout(grid)
        return cards

    def set_cards(self, group, values):
        for key,label in group.items():
            value=values.get(key,'—')
            label.setText(str(value))
            label.setStyleSheet('font-size:20px;font-weight:700;color:' + ('#ed7283' if str(value).startswith('-') else '#f2f7ff') + ';')

    def build_analytics(self):
        _,v=self.page('Strategy Analytics')
        self.analytics_summary=QLabel('Run a backtest from the Dashboard to generate analytics.')
        self.analytics_summary.setWordWrap(True)
        self.analytics_summary.setStyleSheet('font-size:13px;color:#9fb7d1;padding:4px')
        v.addWidget(self.analytics_summary)
        self.overview_cards=self.metric_cards(v,[('pnl','Total P/L'),('return','Strategy return'),('drawdown','Max drawdown'),('wins','Profitable trades')])
        self.tabs=QTabWidget()
        # Preserve the original tab sequence for established scripts and users.
        self.equity_page=QWidget();eqv=QVBoxLayout(self.equity_page)
        self.equity_cards=self.metric_cards(eqv,[('equity','Final equity'),('benchmark','Buy & hold'),('sharpe','Sharpe'),('trades','Closed trades')])
        self.equity_plot=Plot(3);eqv.addWidget(self.equity_plot,1)
        self.tabs.addTab(self.equity_page,'Equity and drawdown')
        self.trades=QTableWidget(0,7);self.trades.setHorizontalHeaderLabels(['Entry time','Exit time','Entry price','Exit price','Quantity','Net P/L','Return %']);self.trades.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tradepage=QWidget();tradelayout=QVBoxLayout(tradepage)
        filterrow=QHBoxLayout()
        self.trade_filter=QComboBox();self.trade_filter.addItems(['All trades','Profitable only','Losing only'])
        self.trade_search=QLineEdit();self.trade_search.setPlaceholderText('Filter entry/exit date (YYYY-MM-DD)')
        self.trade_filter.currentTextChanged.connect(self.fill_trades_filtered)
        self.trade_search.textChanged.connect(self.fill_trades_filtered)
        filterrow.addWidget(QLabel('Result'));filterrow.addWidget(self.trade_filter)
        filterrow.addWidget(self.trade_search,1);tradelayout.addLayout(filterrow)
        self.trades.setSortingEnabled(True);self.trades.cellClicked.connect(self.highlight_trade)
        tradelayout.addWidget(self.trades,1);self.tabs.addTab(tradepage,'Completed trades')
        self.analysis=QWidget();analysis_layout=QVBoxLayout(self.analysis)
        self.analysis_cards=self.metric_cards(analysis_layout,[('realised','Realised P/L'),('unrealised','Unrealised P/L'),('profit_factor','Profit factor'),('expectancy','Expectancy / trade')])
        self.analysis_metrics=QLabel('');self.analysis_metrics.setWordWrap(True);self.analysis_metrics.setStyleSheet('color:#9ab1cb;font-size:12px;');analysis_layout.addWidget(self.analysis_metrics)
        self.analysis_plot=Plot(3);analysis_layout.addWidget(self.analysis_plot,1)
        self.tabs.addTab(self.analysis,'Performance analysis')
        self.distribution_page=QWidget();dv=QVBoxLayout(self.distribution_page)
        self.distribution_cards=self.metric_cards(dv,[('winners','Winners'),('losers','Losers'),('best','Best trade'),('worst','Worst trade')])
        distctrl=QHBoxLayout();distctrl.addWidget(QLabel('Trade analysis'))
        self.trade_view=QComboBox();self.trade_view.addItems(['Distribution','Win / loss streaks','Entry hour patterns','Entry weekday patterns','Trade excursions','Trade duration'])
        self.trade_view.currentTextChanged.connect(self.refresh_trade_chart)
        distctrl.addWidget(self.trade_view);distctrl.addStretch();dv.addLayout(distctrl)
        self.distribution=Plot(3);dv.addWidget(self.distribution,1);self.tabs.addTab(self.distribution_page,'Trade distribution')
        self.risk_page=QWidget();risk_layout=QVBoxLayout(self.risk_page)
        self.risk_cards=self.metric_cards(risk_layout,[('sortino','Sortino ratio'),('relative','Vs benchmark'),('win_streak','Longest win streak'),('loss_streak','Longest loss streak')])
        self.risk_metrics=QLabel('Run a backtest to calculate risk and benchmark metrics.');self.risk_metrics.setWordWrap(True);self.risk_metrics.setStyleSheet('color:#9ab1cb;font-size:12px');risk_layout.addWidget(self.risk_metrics)
        self.risk_plot=Plot(3);risk_layout.addWidget(self.risk_plot,1)
        self.tabs.addTab(self.risk_page,'Risk and benchmarking')
        self.detail_page=QWidget();details=QVBoxLayout(self.detail_page)
        self.detail_cards=self.metric_cards(details,[('avg_win','Avg winning trade'),('avg_loss','Avg losing trade'),('duration','Avg duration (min)'),('recovery','Longest drawdown (bars)')])
        self.detail_selector=QComboBox();self.detail_selector.addItems(['Cumulative P/L & excursions','Growth and decline durations'])
        self.detail_selector.currentTextChanged.connect(self.refresh_detail)
        details.addWidget(self.detail_selector)
        self.detail_plot=Plot(3);details.addWidget(self.detail_plot,1)
        self.tabs.addTab(self.detail_page,'Growth & trade insights')
        self.periodic_page=QWidget();periodic_layout=QVBoxLayout(self.periodic_page)
        self.periodic_cards=self.metric_cards(periodic_layout,[('period','Selected period'),('best','Best period'),('worst','Worst period'),('positive','Positive periods')])
        controls=QHBoxLayout();controls.addWidget(QLabel('Return aggregation'))
        self.periodic_frequency=QComboBox();self.periodic_frequency.addItems(['Daily','Weekly','Monthly','Quarterly','Yearly']);self.periodic_frequency.setCurrentText('Weekly');self.periodic_frequency.currentTextChanged.connect(self.refresh_periodic)
        controls.addWidget(self.periodic_frequency);controls.addStretch();periodic_layout.addLayout(controls)
        self.periodic_metrics=QLabel('Run a backtest to calculate period returns.');self.periodic_metrics.setWordWrap(True);self.periodic_metrics.setStyleSheet('color:#9ab1cb;font-size:12px');periodic_layout.addWidget(self.periodic_metrics)
        self.periodic_plot=Plot(3);periodic_layout.addWidget(self.periodic_plot,1)
        self.tabs.addTab(self.periodic_page,'Periodic returns')
        v.addWidget(self.tabs,1)

    def build_editor(self):
        _,v=self.page('Strategy creator / editor')
        v.addWidget(QLabel('Structured rule language · two rules (BUY IF / SELL IF). No user Python is executed.'))
        presets=QHBoxLayout();presets.addWidget(QLabel('Rule template'))
        self.preset_box=QComboBox();self.preset_box.addItems(['RSI reversal','SMA trend','MACD momentum','RSI + volume'])
        presets.addWidget(self.preset_box)
        insert=QPushButton('Insert template');insert.clicked.connect(self.insert_preset);presets.addWidget(insert);presets.addStretch();v.addLayout(presets)
        self.editor=QPlainTextEdit(EXAMPLE);self.editor.setStyleSheet('font:14px Consolas;background:#162132');v.addWidget(self.editor,1)
        self.validation=QLabel('');v.addWidget(self.validation)
        self.validation_timer=QTimer(self);self.validation_timer.setSingleShot(True);self.validation_timer.setInterval(400);self.validation_timer.timeout.connect(self.validate)
        self.editor.textChanged.connect(lambda:self.validation_timer.start())
        btns=QHBoxLayout()
        for title,fun in [('Validate syntax',self.validate),('Run backtest',lambda:(self.run_backtest(),self.navigate(0))),('Save strategy',self.save_current),('Export rules',self.export_strategy),('Load example',lambda:self.editor.setPlainText(EXAMPLE))]:
            b=QPushButton(title);b.clicked.connect(fun);btns.addWidget(b)
        v.addLayout(btns)
        v.addWidget(QLabel('Examples: BUY IF (RSI < 30 OR CLOSE > SMA_20) AND VOLUME > 5000\nSELL IF RSI > 70\nSupported: CLOSE, VOLUME, VOLUME_SMA_N, RSI, RSI_N, SMA_N, MACD, MACD_SIGNAL; AND, OR, NOT, ( ), comparisons.'))
        self.validate()
    def build_params(self):
        _,v=self.page('Strategy parameters')
        form=QFormLayout();self.capital=QDoubleSpinBox();self.capital.setRange(100,1000000000);self.capital.setValue(10000);self.capital.setDecimals(2)
        self.fee=QDoubleSpinBox();self.fee.setRange(0,10);self.fee.setDecimals(3);self.fee.setSuffix(' % per order');self.fee.setValue(.1)
        self.slippage=QDoubleSpinBox();self.slippage.setRange(0,10);self.slippage.setDecimals(3);self.slippage.setSuffix(' %');self.slippage.setValue(0)
        self.position=QDoubleSpinBox();self.position.setRange(1,100);self.position.setValue(100);self.position.setSuffix(' % equity')
        for label,w in [('Starting capital',self.capital),('Transaction fee',self.fee),('Slippage estimate',self.slippage),('Position allocation',self.position)]:form.addRow(label,w)
        v.addLayout(form);v.addWidget(QLabel('Capital, fees, slippage and position allocation are applied to each simulation. Values apply when you next run a backtest.'))
        for w in (self.capital,self.fee,self.slippage,self.position):w.valueChanged.connect(self.read_settings)
        params_btn=QPushButton('Detect adjustable thresholds in strategy');params_btn.clicked.connect(self.show_params);v.addWidget(params_btn)
        self.detected=QPlainTextEdit();self.detected.setReadOnly(True);v.addWidget(self.detected,1)
        adjustable=QHBoxLayout();adjustable.addWidget(QLabel('No-code indicators'))
        self.rsi_period=QSlider(Qt.Orientation.Horizontal);self.rsi_period.setRange(2,50);self.rsi_period.setValue(14)
        self.sma_period=QSlider(Qt.Orientation.Horizontal);self.sma_period.setRange(2,200);self.sma_period.setValue(20)
        self.rsi_label=QLabel('RSI period 14');self.sma_label=QLabel('SMA period 20')
        adjustable.addWidget(self.rsi_label);adjustable.addWidget(self.rsi_period)
        adjustable.addWidget(self.sma_label);adjustable.addWidget(self.sma_period)
        self.rsi_period.valueChanged.connect(lambda n:self.rsi_label.setText(f'RSI period {n}'))
        self.sma_period.valueChanged.connect(lambda n:self.sma_label.setText(f'SMA period {n}'))
        v.addLayout(adjustable)
        preset=QPushButton('Insert configured RSI / SMA strategy');preset.clicked.connect(self.insert_adjustable_strategy);v.addWidget(preset)
        v.addWidget(QLabel('These sliders generate a new indicator-period strategy; they do not silently change existing rules.'))
        self.show_params()
    def build_optimisation(self):
        _,v=self.page('Genetic Algorithm optimiser')
        r=QHBoxLayout();self.pop=QSpinBox();self.pop.setRange(4,100);self.pop.setValue(12);self.gen=QSpinBox();self.gen.setRange(1,100);self.gen.setValue(8)
        self.obj=QComboBox();self.obj.addItems(['return','sharpe','drawdown_adjusted'])
        for label,w in [('Population',self.pop),('Generations',self.gen),('Fitness',self.obj)]:r.addWidget(QLabel(label));r.addWidget(w)
        v.addLayout(r)
        options=QHBoxLayout()
        self.train_pct=QSpinBox();self.train_pct.setRange(50,85);self.train_pct.setValue(70);self.train_pct.setSuffix(' % training')
        self.min_trades=QSpinBox();self.min_trades.setRange(0,1000);self.min_trades.setValue(2)
        self.penalty=QDoubleSpinBox();self.penalty.setRange(0,100);self.penalty.setDecimals(2);self.penalty.setValue(0)
        for label,w in [('Chronological split',self.train_pct),('Minimum train trades',self.min_trades),('Complexity penalty',self.penalty)]:options.addWidget(QLabel(label));options.addWidget(w)
        v.addLayout(options)
        bounds_label=QLabel('Optional search bounds (one min,max per detected threshold; blank = automatic bounds)')
        v.addWidget(bounds_label)
        self.bounds_edit=QPlainTextEdit();self.bounds_edit.setMaximumHeight(75);self.bounds_edit.setPlaceholderText('Example for two thresholds: 10,40\n60,90');v.addWidget(self.bounds_edit)
        run=QPushButton('Optimise numeric thresholds');run.setObjectName('primary');run.clicked.connect(self.run_optimisation);v.addWidget(run);self.opt_btn=run
        self.progress=QProgressBar();v.addWidget(self.progress)
        self.optimised=QPlainTextEdit();self.optimised.setReadOnly(True);v.addWidget(self.optimised,1)
        apply=QPushButton('Copy optimised rules to editor');apply.clicked.connect(self.use_optimised);v.addWidget(apply)
        v.addWidget(QLabel('Candidates are ranked ONLY on training data; held-out candles are evaluated once after selection. Repeated tuning against the holdout invalidates the comparison.'))
        self.best_source=None;self.highlighted_trade=None
    def build_saved(self):
        _,v=self.page('Saved strategies')
        self.saved=QTableWidget(0,2);self.saved.setHorizontalHeaderLabels(['ID','Strategy name']);self.saved.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);v.addWidget(self.saved,1)
        r=QHBoxLayout()
        for text,fn in [('Refresh',self.refresh_saved),('Load selection',self.load_saved),('Delete selection',self.delete_saved),('Export selected JSON',self.export_saved),('Save current editor',self.save_current)]:
            b=QPushButton(text);b.clicked.connect(fn);r.addWidget(b)
        v.addLayout(r)
    def build_history(self):
        _,v=self.page('Run history / settings')
        self.history=QTableWidget(0,5);self.history.setHorizontalHeaderLabels(['Date (UTC)','Symbol','Interval','Return %','Sharpe']);self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);v.addWidget(self.history,1)
        self.history_summary=QLabel('Select a previous run to view its cached statistics.');self.history_summary.setWordWrap(True);v.addWidget(self.history_summary)
        self.history.itemSelectionChanged.connect(self.show_selected_history)
        v.addWidget(QLabel('Alpaca credentials: set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY in your Windows environment.\nNo brokerage connections or order placement. Data downloads require internet; cached ranges run offline.\nCached data and saved strategies are in user_data/ (excluded from Git).'))
    def read_settings(self,*args):
        self.settings={'capital':self.capital.value(),'fee':self.fee.value()/100,'slippage':self.slippage.value()/100,'position':self.position.value()}
    def insert_preset(self):
        examples={
            'RSI reversal':'BUY IF RSI < 30\nSELL IF RSI > 70',
            'SMA trend':'BUY IF CLOSE > SMA_20\nSELL IF CLOSE < SMA_20',
            'MACD momentum':'BUY IF MACD > MACD_SIGNAL\nSELL IF MACD < MACD_SIGNAL',
            'RSI + volume':'BUY IF RSI < 35 AND VOLUME > 1000\nSELL IF RSI > 65'}
        self.editor.setPlainText(examples[self.preset_box.currentText()])

    def validate(self):
        try:parse_strategy(self.editor.toPlainText());self.validation.setText('✓ Syntax valid');self.validation.setStyleSheet('color:#7cdea5')
        except Exception as e:self.validation.setText(str(e));self.validation.setStyleSheet('color:#ff9f9f')
    def show_params(self):
        if hasattr(self,'detected'):
            items=parameters(self.editor.toPlainText());self.detected.setPlainText('\n'.join(f'{p.name}: {p.current:g}  (search {p.low:g} – {p.high:g})' for p in items) or 'No numeric comparison thresholds detected')
    def on_market(self,i):
        self.symbol_box.setText('AAPL' if i else 'BTCUSDT');self.selection_changed()
    def from_watch(self,item):
        symbol,market=item.text().split(' · ')
        # Keep the existing strategy text; the new asset must never reuse old candles.
        self.market_combo.blockSignals(True)
        self.market_combo.setCurrentIndex(0 if market=='Crypto' else 1)
        self.market_combo.blockSignals(False)
        self.symbol_box.setText(symbol)
        self.navigate(0)
        self.selection_changed()
    def current_request(self):
        return MarketRequest('crypto' if self.market_combo.currentIndex()==0 else 'stocks',
            self.symbol_box.text().strip(),self.interval.currentText(),
            self.start.date().toPyDate(),self.end.date().toPyDate())
    def empty_chart(self, message):
        self.price_plot.axes().text(.5,.5,message,ha='center',va='center',color='#cbd5e1',
                                    transform=self.price_plot.fig.axes[0].transAxes,fontsize=13)
        self.price_plot.draw_idle()
    def clear_results(self):
        self.bars=[];self.result=None;self.trades.setRowCount(0)
        self.stats.setText('No backtest for current selection')
        self.analytics_summary.setText('No results for the current selection. Run a backtest on the Dashboard.')
        self.price_plot.axes();self.empty_chart('No candles available for this selection.\nClick Download historical data.')
        self.equity_plot.axes();self.equity_plot.draw_idle()
        self.analysis_metrics.setText('No results — load data and run a backtest.')
        self.analysis_plot.axes();self.analysis_plot.draw_idle()
        self.distribution.axes();self.distribution.draw_idle()
        self.risk_metrics.setText('Run a backtest to generate risk and benchmarking reports.')
        self.risk_plot.axes();self.risk_plot.draw_idle()
        self.periodic_metrics.setText('Run a backtest to generate periodic returns.')
        self.periodic_plot.axes();self.periodic_plot.draw_idle()
        self._indicator_cache_key=None;self._indicator_cache=None
    def selection_changed(self,*args):
        self.request_id+=1
        if self.busy:
            self.download_state.setText('Selection changed; previous download will be ignored when finished.')
        try:req=self.current_request()
        except ValueError as exc:
            self.clear_results();self.dataset.setText(str(exc));return
        provider=self.service.providers[req.market]
        try:
            bars=self.service.cache.load(provider.name,req)
            complete=self.service.cache.has_download(provider.name,req)
        except Exception as exc:
            self.clear_results();self.download_state.setText(f'Cache error: {exc}');return
        if complete and bars:
            self.bars=bars;self.market=req.market;self.symbol=req.symbol.upper();self.timeframe=req.timeframe
            self.result=None;self.dataset.setText(f'{self.symbol} · {self.timeframe} · {len(bars):,} cached bars')
            self.stats.setText('Cached candles loaded — click Run backtest to generate new metrics.')
            self.plot_candles();self.equity_plot.axes();self.equity_plot.draw_idle();self.trades.setRowCount(0)
            self.analysis_metrics.setText('Backtest required for the selected asset.');self.analysis_plot.axes();self.analysis_plot.draw_idle();self.distribution.axes();self.distribution.draw_idle()
            self.analytics_summary.setText('Run a backtest on the Dashboard for this selection.');self.risk_metrics.setText('Backtest required.');self.risk_plot.axes();self.risk_plot.draw_idle();self.periodic_metrics.setText('Backtest required.');self.periodic_plot.axes();self.periodic_plot.draw_idle()
            self.download_state.setText('Cached data ready.');self.statusBar().showMessage('Asset selection loaded from SQLite.')
        else:
            self.clear_results();self.market=req.market;self.symbol=req.symbol.upper();self.timeframe=req.timeframe
            self.dataset.setText(f'{self.symbol} · {self.timeframe} · no complete cached date range')
            self.download_state.setText('Not cached. Click Download historical data to retrieve it.')
            self.statusBar().showMessage(f'{self.symbol} selected; historical candles not cached.')
    def download(self):
        if self.busy:return
        try:req=self.current_request()
        except ValueError as e:QMessageBox.warning(self,'Invalid request',str(e));return
        self.busy=True;self.load_btn.setEnabled(False);self.download_progress.setVisible(True)
        self.download_state.setText(f'Fetching {req.symbol.upper()} {req.timeframe} candles; the window remains usable…')
        self.statusBar().showMessage('Downloading in background — please wait…')
        request_id=self.request_id
        self.job=Job(lambda:self.service.get(req,self.offline.isChecked()))
        def received(response):
            bars,how=response
            if request_id!=self.request_id:
                self.download_state.setText('Previous download completed; selection changed.');return
            if len(bars)<35:
                self.download_state.setText(f'Only {len(bars)} candles found; at least 35 needed for backtesting.')
                return
            self.bars=bars;self.market=req.market;self.timeframe=req.timeframe;self.symbol=req.symbol.upper();self.result=None
            self.dataset.setText(f'{self.symbol} · {self.timeframe} · {len(self.bars):,} bars · {how}')
            self.plot_candles();self.stats.setText('Data loaded. Click Run backtest to calculate strategy metrics.')
            self.download_state.setText(f'Data ready: {len(self.bars):,} candles · {how}.')
            self.statusBar().showMessage('Historical candles ready. Run a backtest when you choose.')
        def failure(message):
            self.download_state.setText('Download failed: '+message)
            self.statusBar().showMessage('Download failed — see message beside progress indicator.')
            QMessageBox.warning(self,'Provider error',message)
        def finished():
            self.busy=False;self.download_progress.setVisible(False);self.load_btn.setEnabled(True)
        self.job.completed.connect(received);self.job.failed.connect(failure);self.job.finished.connect(finished)
        self.job.start()
    def open_csv(self):
        filename,_=QFileDialog.getOpenFileName(self,'Load OHLCV data',str(ROOT),'CSV (*.csv)')
        if filename:
            try:self.request_id+=1;self.bars=load_csv(filename);self.market='csv';self.timeframe='1d';self.symbol=Path(filename).stem;self.dataset.setText(f'{self.symbol} · CSV · {len(self.bars)} bars');self.run_backtest()
            except Exception as ex:QMessageBox.warning(self,'CSV error',str(ex))
    def run_backtest(self):
        try:
            self.read_settings();
            if not self.bars:raise ValueError('No candles loaded for this asset. Download historical data first.')
            annual=annualisation_periods(self.market if self.market!='demo' else 'csv',self.timeframe)
            self.result=backtest(self.editor.toPlainText(),self.bars,initial=self.settings['capital'],fee=self.settings['fee'],periods_per_year=annual,slippage=self.settings['slippage'],allocation=self.settings['position']/100,asset_type=self.market if self.market!='demo' else 'csv',timeframe=self.timeframe)
            self.highlighted_trade=None
            r=self.result;self.stats.setText(f"Return {r['total_return']:+.2f}%   |   Buy & hold {r['buy_hold']:+.2f}%   |   Sharpe {r['sharpe']:.2f}   |   Max DD {r['max_drawdown']:.2f}%   |   Trades {r['closed_trades']}   |   Wins {r['win_rate']:.1f}%")
            self.analytics_summary.setText(f"{self.symbol} · {self.timeframe}   |   Strategy {r['total_return']:+.2f}%   |   Buy & hold {r['buy_hold']:+.2f}%   |   Max drawdown {r['max_drawdown']:.2f}%   |   {r['closed_trades']} completed trades")
            self.plot_candles();self.plot_equity();self.fill_trades();self.plot_analysis();self.plot_advanced();self.store.save_run(self.saved_id,self.symbol,self.timeframe,r)
            self.statusBar().showMessage(f'Backtest complete: {len(self.bars):,} bars · {self.symbol}')
        except Exception as ex:QMessageBox.warning(self,'Backtesting error',str(ex));self.statusBar().showMessage('Last successful results retained — strategy error')
    def move_price_window(self,step):
        if not self.bars:return
        visible=min(self.price_window_size,len(self.bars))
        start=max(0,len(self.bars)-visible) if step is None else self.price_window[0]+step
        self.plot_candles(start=max(0,min(start,len(self.bars)-visible)),width=visible)

    def eventFilter(self, source, event):
        if source is getattr(self,'price_slider',None) and event.type()==QEvent.Type.Wheel:
            # Qt mouse-wheel delta is positive for wheel-up and negative for wheel-down.
            delta=event.angleDelta().y()
            if delta:
                step=max(1,self.price_slider.pageStep()//5)
                self.price_slider.setValue(self.price_slider.value() + (step if delta>0 else -step))
            return True
        return super().eventFilter(source,event)

    def slide_price_window(self,value):
        if self._chart_rendering:return
        self.plot_candles(start=value,width=self.price_window_size)

    def on_price_navigation(self,event):
        # The Matplotlib toolbar pans or zooms axes; the corresponding bars are
        # populated on mouse release, not continuously during every mouse movement.
        if not self.bars or self._chart_rendering or event.inaxes is not self.price_plot.fig.axes[0]:return
        ax=event.inaxes
        left,right=ax.get_xlim()
        width=max(25,min(len(self.bars),int(round(right-left))))
        start=max(0,min(int(round(left)),max(0,len(self.bars)-width)))
        self.plot_candles(start=start,width=width)

    def plot_candles(self, *args, start=None, width=None):
        # `*args` accepts the QCheckBox.stateChanged signal argument.
        bars=self.bars
        if not bars:
            self.empty_chart('No candles available. Click Download historical data.');return
        total=len(bars)
        if width is None:width=min(self.price_window_size,total)
        width=max(25,min(total,int(width)))
        if start is None:
            old_start,old_width=self.price_window
            start=old_start if old_width and old_start+old_width<=total else max(0,total-width)
        start=max(0,min(int(start),total-width));end=start+width
        self._chart_rendering=True
        try:
            ax=self.price_plot.axes()
            visible=bars[start:end]
            # A pair of Matplotlib collections replaces hundreds of individual
            # patches and scatter artists. Draw every visible candle accurately.
            wicks=[];bodies=[];colors=[]
            for i,b in enumerate(visible,start):
                color='#3ecf9c' if b['close']>=b['open'] else '#ef737b'
                wicks.append([(i,b['low']),(i,b['high'])])
                lo=min(b['open'],b['close']);hi=max(b['open'],b['close'])
                if hi==lo:hi=lo+max(1e-9,lo*.00002)
                bodies.append([(i-.32,lo),(i+.32,lo),(i+.32,hi),(i-.32,hi)])
                colors.append(color)
            ax.add_collection(LineCollection(wicks,colors=colors,linewidths=.75))
            ax.add_collection(PolyCollection(bodies,facecolors=colors,edgecolors=colors,linewidths=.4))
            date_to_index={str(b['date']):i for i,b in enumerate(bars)}
            if self.result is not None:
                for side,marker,color in [('BUY','^','#5cdb9c'),('SELL','v','#fc7373')]:
                    locations=[(date_to_index[t['date']],t['price']) for t in self.result['trades'] if t['side']==side and t['date'] in date_to_index and start<=date_to_index[t['date']]<end]
                    if locations:ax.scatter([v[0] for v in locations],[v[1] for v in locations],marker=marker,s=65,c=color,zorder=9)
            if getattr(self,'show_sma',None) and self.show_sma.isChecked():
                cache_key=id(bars)
                if self._indicator_cache_key!=cache_key:
                    self._indicator_cache=indicators(bars,{'SMA_20','SMA_50'});self._indicator_cache_key=cache_key
                series=self._indicator_cache
                for key,color in [('SMA_20','#e0b45e'),('SMA_50','#aa8aff')]:
                    ax.plot(range(start,end),series[key][start:end],color=color,linewidth=1,alpha=.85,label=key)
                ax.legend(loc='upper left',facecolor='#1c2736',labelcolor='white',fontsize=8)
            if getattr(self,'highlighted_trade',None) is not None and self.result:
                trades=self.result['completed_trades']
                if self.highlighted_trade<len(trades):
                    for d in (trades[self.highlighted_trade]['entry_date'],trades[self.highlighted_trade]['exit_date']):
                        if d in date_to_index and start<=date_to_index[d]<end:ax.axvline(date_to_index[d],color='#f4dc8b',alpha=.65,linestyle='--')
            lows=[b['low'] for b in visible];highs=[b['high'] for b in visible]
            ymin=min(lows);ymax=max(highs);pad=max((ymax-ymin)*.04,ymax*.0001)
            ax.set_ylim(ymin-pad,ymax+pad)
            ax.set_xlim(start-.6,end-.4)
            ax.set_title(f'{self.symbol}  ·  {self.timeframe}  ·  Candles {start+1:,}–{end:,} of {total:,}',color='#d7e5f6')
            ax.set_ylabel('Price',color='#abbccf')
            self.price_window=(start,width)
            self.price_slider.blockSignals(True);self.price_slider.setRange(0,max(0,total-width));self.price_slider.setValue(start);self.price_slider.setPageStep(max(1,width//2));self.price_slider.blockSignals(False)
            self.price_plot.draw_idle()
        finally:
            self._chart_rendering=False

    def plot_equity(self):
        r=self.result
        self.set_cards(self.overview_cards,{'pnl':f"{r['total_pnl']:+,.2f}",'return':f"{r['total_return']:+.2f}%",'drawdown':f"{r['max_drawdown']:.2f}%",'wins':f"{r['win_rate']:.1f}%"})
        self.set_cards(self.equity_cards,{'equity':f"{r['final_equity']:,.2f}",'benchmark':f"{r['buy_hold']:+.2f}%",'sharpe':f"{r['sharpe']:.2f}",'trades':str(r['closed_trades'])})
        axes=self.equity_plot.axes(2);r=self.result;n=len(r['equity'])
        axes[0].plot(r['equity'],c='#63acff',linewidth=1.2,label='Strategy')
        buyhold=[self.settings['capital']*b['close']/self.bars[0]['close'] for b in self.bars]
        axes[0].plot(buyhold,c='#efb740',linewidth=1,label='Buy and hold');axes[0].legend(facecolor='#1c2736',labelcolor='white',fontsize=8)
        axes[1].fill_between(range(n),r['drawdown'],0,color='#c75d65',alpha=.6);axes[1].set_ylim(min(-1,min(r['drawdown'])*1.05),max(1,max(r['drawdown'])*1.05));axes[1].set_ylabel('DD %',color='#abbccf');self.equity_plot.draw_idle()
    def plot_analysis(self):
        metrics=trade_metrics(self.result['trades'])
        r=self.result
        display=[('Gross profit',r['gross_profit']),('Gross loss',r['gross_loss']),
                 ('Net realised P/L',r['realised_pnl']),('Unrealised P/L',r['unrealised_pnl']),
                 ('Total P/L',r['total_pnl']),('Final equity',r['final_equity']),
                 ('Open position',f"Yes ({r['position_quantity']:.5f} units)" if r['open_position'] else 'No'),
                 ('Profit factor',r['profit_factor']),('Expectancy per trade',r['expectancy']),
                 ('Annualisation periods',r['periods_per_year'])]
        self.set_cards(self.analysis_cards,{'realised':f"{r['realised_pnl']:+,.2f}",'unrealised':f"{r['unrealised_pnl']:+,.2f}",'profit_factor':f"{r['profit_factor']:.2f}" if r['profit_factor'] is not None else 'N/A','expectancy':f"{r['expectancy']:.2f}" if r['expectancy'] is not None else 'N/A'})
        self.set_cards(self.distribution_cards,{'winners':str(metrics['winners']),'losers':str(metrics['losers']),'best':f"{max(metrics['pnl']):+,.2f}" if metrics['pnl'] else 'N/A','worst':f"{min(metrics['pnl']):+,.2f}" if metrics['pnl'] else 'N/A'})
        self.analysis_metrics.setText('    |    '.join(f'{k}: {v:,.2f}' if isinstance(v,(int,float)) else f'{k}: {v}' if v is not None else f'{k}: N/A' for k,v in display))
        ax=self.analysis_plot.axes()
        pnl=metrics['pnl']
        if pnl:
            cumulative=[];total=0
            for value in pnl:total+=value;cumulative.append(total)
            ax.plot(range(1,len(cumulative)+1),cumulative,c='#62aeff',marker='o',markersize=3)
            ax.axhline(0,c='#aab6cc',linewidth=.7)
            ax.set_title('Cumulative realised P/L by closed trade',color='#d6e6fa')
        else:ax.text(.5,.5,'No closed trades',ha='center',va='center',transform=ax.transAxes,color='white')
        self.analysis_plot.draw_idle()
        self.refresh_trade_chart()

    def refresh_trade_chart(self,*args):
        if not self.result:return
        ax=self.distribution.axes()
        pnl=[float(t['pnl']) for t in self.result['completed_trades']]
        mode=self.trade_view.currentText()
        if not pnl:
            ax.text(.5,.5,'No closed trades',ha='center',va='center',transform=ax.transAxes,color='white')
        elif mode=='Distribution':
            returns=[v/self.settings['capital']*100 for v in pnl]
            ax.hist([v for v in returns if v>=0],bins=min(14,max(5,int(len(pnl)**.5)*2)),color='#20af91',alpha=.9,label='Profitable')
            ax.hist([v for v in returns if v<0],bins=min(14,max(5,int(len(pnl)**.5)*2)),color='#d94c65',alpha=.9,label='Losing')
            ax.legend(facecolor='#1c2736',labelcolor='white',fontsize=9)
            ax.set_xlabel('Closed-trade P/L as % of starting capital',color='#d6e6fa');ax.set_ylabel('Trades',color='#d6e6fa')
            ax.set_title(f'{sum(v>0 for v in pnl)} winners · {sum(v<0 for v in pnl)} losers',color='#d6e6fa')
        elif mode=='Win / loss streaks':
            runs=[];last=None;count=0
            for value in pnl:
                current=1 if value>0 else -1 if value<0 else 0
                if current==last:count+=1
                else:
                    if count:runs.append(last*count)
                    last=current;count=1
            if count:runs.append(last*count)
            ax.bar(range(len(runs)),runs,color=['#20af91' if x>0 else '#d94c65' if x<0 else '#8a9eb4' for x in runs],width=.7)
            ax.axhline(0,c='#93a5bf',lw=.8);ax.set_ylabel('Consecutive trades',color='#d6e6fa')
            ax.set_xlabel('Consecutive result runs',color='#d6e6fa');ax.set_title('Winning and losing streaks',color='#d6e6fa')
        elif mode=='Trade excursions':
            from analytics import trade_excursions
            excursions=trade_excursions(self.result['completed_trades'],self.bars)
            x=list(range(len(excursions)))
            ax.bar(x,[v[0] or 0 for v in excursions],color='#20af91',label='Maximum favourable %')
            ax.bar(x,[v[1] or 0 for v in excursions],color='#d94c65',label='Maximum adverse %')
            ax.legend(facecolor='#1c2736',labelcolor='white',fontsize=9)
            ax.set_title('High/low-based excursions during completed positions',color='#d6e6fa')
        elif mode=='Trade duration':
            from analytics import trade_durations
            ax.hist(trade_durations(self.result['completed_trades']),bins=min(12,max(3,len(pnl)//3)),color='#62aeff')
            ax.set_title('Completed trade duration (minutes)',color='#d6e6fa')
        else:
            from collections import Counter
            from datetime import datetime
            winners=Counter();losers=Counter()
            for trade in self.result['completed_trades']:
                try:hour=datetime.fromisoformat(str(trade['entry_date']).replace('Z','+00:00')).weekday() if mode=='Entry weekday patterns' else datetime.fromisoformat(str(trade['entry_date']).replace('Z','+00:00')).hour
                except ValueError:continue
                (winners if trade['pnl']>0 else losers)[hour]+=1
            hours=list(range(7 if mode=='Entry weekday patterns' else 24))
            ax.bar(hours,[winners[h] for h in hours],color='#20af91',label='Profitable',width=.75)
            ax.bar(hours,[losers[h] for h in hours],bottom=[winners[h] for h in hours],color='#d94c65',label='Losing',width=.75)
            ax.set_xticks(hours if mode=='Entry weekday patterns' else range(0,24,2));ax.set_xlabel('Entry weekday (Mon=0)' if mode=='Entry weekday patterns' else 'Entry hour (source timestamps)',color='#d6e6fa')
            ax.set_ylabel('Completed trades',color='#d6e6fa');ax.set_title(mode,color='#d6e6fa')
            ax.legend(facecolor='#1c2736',labelcolor='white',fontsize=9)
        self.distribution.draw_idle()

    def plot_advanced(self):
        r=self.result
        report=advanced_report(r,self.settings['capital'])
        def fmt(value):return 'N/A' if value is None else f'{value:,.2f}'
        self.set_cards(self.risk_cards,{'sortino':fmt(report['sortino']),'relative':f"{report['relative_return']:+.2f} pp",'win_streak':str(report['longest_win_streak']),'loss_streak':str(report['longest_loss_streak'])})
        self.risk_metrics.setText(
            f"Sortino (illustrative): {fmt(report['sortino'])}    |    "
            f"Relative to buy and hold: {report['relative_return']:+.2f} pp    |    "
            f"Longest underwater stretch: {report['max_underwater_bars']:,} bars\n"
            f"Best trade: {fmt(report['best_trade'])}    |    Worst trade: {fmt(report['worst_trade'])}    |    "
            f"Winning streak: {report['longest_win_streak']}    |    Losing streak: {report['longest_loss_streak']}")
        ax=self.risk_plot.axes()
        values=[(v/self.settings['capital']-1)*100 for v in r['equity']]
        hold=[(b['close']/self.bars[0]['close']-1)*100 for b in self.bars]
        ax.plot(values,color='#5eaafc',linewidth=1.2,label='Strategy')
        ax.plot(hold,color='#dfb65e',linewidth=1,label='Buy and hold (no fees)')
        ax.set_title('Cumulative return comparison (%)',color='#d6e6fa')
        ax.legend(facecolor='#1c2736',labelcolor='white',fontsize=8)
        self.risk_plot.draw_idle()
        self.refresh_periodic();self.refresh_detail()

    def refresh_periodic(self,*args):
        if not self.result:return
        from analytics import periodic_returns
        frequency=self.periodic_frequency.currentText().lower()
        periodic=periodic_returns(self.result['dates'],self.result['equity'],self.settings['capital'],frequency)
        values=[v for _,v in periodic]
        self.set_cards(self.periodic_cards,{'period':frequency.title(),'best':f"{max(values):+.2f}%" if values else 'N/A','worst':f"{min(values):+.2f}%" if values else 'N/A','positive':f"{sum(x>0 for x in values)}/{len(values)}"})
        self.periodic_metrics.setText(f'{len(periodic)} {frequency} periods · Marked-to-market compounded returns; incomplete periods may be included')
        ax=self.periodic_plot.axes()
        if periodic:
            x=list(range(len(periodic)))
            # Limit bar width visually for short samples; one month should not fill the canvas.
            ax.bar(x,values,width=.58,color=['#20af91' if v>=0 else '#d94c65' for v in values])
            ax.set_xlim(-1,max(4,len(periodic)))
            step=max(1,len(x)//10)
            ax.set_xticks(x[::step],[periodic[i][0] for i in x[::step]],rotation=20,ha='right')
            ax.set_ylabel('Return (%)',color='#d6e6fa')
            ax.axhline(0,color='#abbccf',linewidth=.7)
            ax.set_title(f'{frequency.title()} returns',color='#d6e6fa')
        else:ax.text(.5,.5,'No periods available',ha='center',va='center',transform=ax.transAxes,color='white')
        self.periodic_plot.draw_idle()

    def filter_watchlist(self,text):
        for i in range(self.watch.count()):
            item=self.watch.item(i)
            item.setHidden(text.casefold() not in item.text().casefold())

    def show_selected_history(self):
        row=self.history.currentRow()
        records=self.store.runs()
        if row<0 or row>=len(records):return
        ts,symbol,interval,raw=records[row]
        data=json.loads(raw)
        self.history_summary.setText(f"Run {ts[:19]} UTC · {symbol} · {interval}  |  " +
              '  |  '.join(f'{k.replace("_"," ").title()}: {v:.2f}' if isinstance(v,(int,float)) else f'{k}: {v}' for k,v in data.items()))

    def insert_adjustable_strategy(self):
        self.editor.setPlainText(f'BUY IF RSI_{self.rsi_period.value()} < 30 AND CLOSE > SMA_{self.sma_period.value()}\nSELL IF RSI_{self.rsi_period.value()} > 70 OR CLOSE < SMA_{self.sma_period.value()}')
        self.navigate(2)

    def refresh_detail(self, *args):
        if not self.result:return
        from analytics import trade_excursions,trade_durations,drawdown_segments
        trades=self.result['completed_trades'];pnls=[t['pnl'] for t in trades]
        wins=[v for v in pnls if v>0];losses=[v for v in pnls if v<0]
        durations=trade_durations(trades);episodes=drawdown_segments(self.result['equity'],self.settings['capital'])
        self.set_cards(self.detail_cards,{'avg_win':f'{sum(wins)/len(wins):+.2f}' if wins else 'N/A',
             'avg_loss':f'{sum(losses)/len(losses):+.2f}' if losses else 'N/A',
             'duration':f'{sum(durations)/len(durations):.1f}' if durations else 'N/A',
             'recovery':str(max(episodes,default=0))})
        ax=self.detail_plot.axes()
        if self.detail_selector.currentIndex()==0:
            cumulative=[];total=0
            for value in pnls:total+=value;cumulative.append(total)
            excursions=trade_excursions(trades,self.bars)
            x=list(range(1,len(pnls)+1))
            ax.bar(x,pnls,color=['#20af91' if v>=0 else '#d94c65' for v in pnls],alpha=.4,label='Closed trade P/L')
            ax.plot(x,cumulative,color='#62aeff',lw=1.8,label='Cumulative P/L')
            if excursions:
                ax.text(.01,.02,'MFE/MAE from recorded high/low: '+f'{sum(v[0] for v in excursions if v[0] is not None)/max(1,sum(v[0] is not None for v in excursions)):.2f}% / '+f'{sum(v[1] for v in excursions if v[1] is not None)/max(1,sum(v[1] is not None for v in excursions)):.2f}%',transform=ax.transAxes,color='#c4d7eb')
            ax.set_title('Realised trade P/L and cumulative progression',color='#d6e6fa')
        else:
            ax.bar(range(1,len(episodes)+1),episodes,color='#d94c65',width=.65)
            ax.set_title('Underwater episodes (bars until recovery, or sample end)',color='#d6e6fa')
            ax.set_xlabel('Episode',color='#d6e6fa')
        ax.legend(facecolor='#1c2736',labelcolor='white',fontsize=8) if self.detail_selector.currentIndex()==0 else None
        self.detail_plot.draw_idle()

    def fill_trades_filtered(self,*args):
        if self.result:self.fill_trades()

    def fill_trades(self):
        """Filtered rows retain original backtest indices for cross-linked navigation."""
        completed=self.result['completed_trades']
        filtered=[]
        for index,trade in enumerate(completed):
            if self.trade_filter.currentIndex()==1 and trade['pnl']<=0:continue
            if self.trade_filter.currentIndex()==2 and trade['pnl']>=0:continue
            search=self.trade_search.text().strip().lower()
            if search and search not in str(trade['entry_date']).lower() and search not in str(trade['exit_date']).lower():continue
            filtered.append((index,trade))
        self.trades.setSortingEnabled(False);self.trades.setRowCount(len(filtered))
        for row,(index,trade) in enumerate(filtered):
            values=[trade['entry_date'],trade['exit_date'],f"{trade['entry_price']:.4f}",
                    f"{trade['exit_price']:.4f}",f"{trade['quantity']:.5f}",
                    f"{trade['pnl']:+.2f}",f"{trade['return_pct']:+.2f}%"]
            for col,value in enumerate(values):
                item=QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole,index)
                self.trades.setItem(row,col,item)
        self.trades.setSortingEnabled(True)
    def highlight_trade(self,row,column):
        item=self.trades.item(row,0)
        self.highlighted_trade=item.data(Qt.ItemDataRole.UserRole) if item else None
        if self.highlighted_trade is not None and self.result:
            trade=self.result['completed_trades'][self.highlighted_trade]
            indices={str(bar['date']):i for i,bar in enumerate(self.bars)}
            i=indices.get(str(trade['entry_date']))
            if i is not None:
                visible=min(self.price_window_size,len(self.bars))
                self.plot_candles(start=max(0,min(i-visible//2,len(self.bars)-visible)),width=visible)
        self.navigate(0)

    def save_current(self):
        name,ok=QInputDialog.getText(self,'Save strategy','Strategy name:')
        if ok:
            try:self.store.save_strategy(name,self.editor.toPlainText(),self.settings);self.statusBar().showMessage(f'Saved {name}');self.refresh_saved()
            except Exception as ex:QMessageBox.warning(self,'Save error',str(ex))
    def selected_id(self):
        row=self.saved.currentRow();return int(self.saved.item(row,0).text()) if row>=0 else None
    def refresh_saved(self):
        rows=self.store.strategies();self.saved.setRowCount(len(rows))
        for i,(ident,name,source,settings) in enumerate(rows):
            self.saved.setItem(i,0,QTableWidgetItem(str(ident)));self.saved.setItem(i,1,QTableWidgetItem(name))
    def load_saved(self):
        ident=self.selected_id()
        for key,name,source,settings in self.store.strategies():
            if key==ident:
                self.saved_id=ident;self.editor.setPlainText(source);self.navigate(2);return
    def delete_saved(self):
        ident=self.selected_id()
        if ident is not None:
            self.store.delete_strategy(ident)
            if self.saved_id==ident:self.saved_id=None
            self.refresh_saved()
    def export_strategy(self):
        path,_=QFileDialog.getSaveFileName(self,'Export strategy',str(ROOT/'strategy.json'),'JSON (*.json)')
        if path:
            with open(path,'w',encoding='utf-8') as f:json.dump({'source':self.editor.toPlainText(),'settings':self.settings},f,indent=2)
    def export_saved(self):
        ident=self.selected_id()
        match=next((row for row in self.store.strategies() if row[0]==ident),None)
        if match is None:
            QMessageBox.information(self,'Export','Select a saved strategy first.');return
        _,name,source,settings=match
        path,_=QFileDialog.getSaveFileName(self,'Export saved strategy',str(ROOT/(name+'.json')),'JSON (*.json)')
        if path:
            with open(path,'w',encoding='utf-8') as handle:
                json.dump({'name':name,'source':source,'settings':json.loads(settings)},handle,indent=2)

    def refresh_history(self):
        rows=self.store.runs();self.history.setRowCount(len(rows))
        for i,(ts,symbol,interval,raw) in enumerate(rows):
            s=json.loads(raw)
            for j,val in enumerate((ts[:19],symbol,interval,f"{s['total_return']:+.2f}",f"{s['sharpe']:.2f}")):self.history.setItem(i,j,QTableWidgetItem(val))
    def run_optimisation(self):
        if self.opt_btn.isEnabled() is False:return
        self.best_source=None;self.opt_btn.setEnabled(False);self.progress.setValue(5);self.optimised.setPlainText('Running optimisation…')
        source=self.editor.toPlainText();bars=self.bars[:];settings=self.settings.copy();population=self.pop.value();generations=self.gen.value();obj=self.obj.currentText()
        annual=annualisation_periods(self.market if self.market!='demo' else 'csv', self.timeframe)
        training_fraction=self.train_pct.value()/100
        minimum_trades=self.min_trades.value()
        complexity_penalty=self.penalty.value()
        try:
            raw=self.bounds_edit.toPlainText().strip()
            bounds=[tuple(float(x.strip()) for x in line.split(',')) for line in raw.splitlines() if line.strip()] if raw else None
        except ValueError:
            self.opt_btn.setEnabled(True);QMessageBox.warning(self,'Bounds error','Use one numeric min,max pair on each line.');return
        self.opt_job=Job(lambda:optimise(source,bars,initial=settings['capital'],fee=settings['fee'],periods_per_year=annual,slippage=settings['slippage'],allocation=settings['position']/100,population=population,generations=generations,objective=obj,training_fraction=training_fraction,min_trades=minimum_trades,complexity_penalty=complexity_penalty,bounds=bounds))
        def finish(out):
            self.best_source=out['source'];self.progress.setValue(100)
            report=out.get('validation')
            summary=(f"Training end: {report['train_end']}\nHoldout start: {report['holdout_start']}\n"
                     f"Train return: {report['training']['total_return']:+.2f}%  |  Holdout return: {report['holdout']['total_return']:+.2f}%\n"
                     f"Train completed trades: {report['training']['closed_trades']}  |  Holdout completed trades: {report['holdout']['closed_trades']}\n"
                     f"Holdout meets minimum trades: {report['holdout_sufficient']}\n\n") if report else ''
            self.optimised.setPlainText(summary+f"Best fitness: {out['best_fitness']:.4f}\nUnique backtests: {out['evaluations']}\nGeneration best: {out['history']}\n\nOptimised rules:\n{out['source']}")
        def optimisation_failed(msg):
            self.progress.setValue(0);self.optimised.setPlainText('Optimisation failed: '+msg)
            QMessageBox.warning(self,'Optimisation error',msg)
        self.opt_job.completed.connect(finish);self.opt_job.failed.connect(optimisation_failed);self.opt_job.finished.connect(lambda:self.opt_btn.setEnabled(True));self.opt_job.start()
    def use_optimised(self):
        if self.best_source:self.editor.setPlainText(self.best_source);self.navigate(2)

if __name__=='__main__':
    app=QApplication(sys.argv);window=Main();window.show();sys.exit(app.exec())
