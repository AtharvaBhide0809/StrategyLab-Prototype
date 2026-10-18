"""StrategyLab Reference v1.0 — PyQt6 desktop demonstration."""
import sys,json,csv,os
from pathlib import Path
from datetime import date
from PyQt6.QtCore import Qt,QDate,QTimer,QThread,pyqtSignal
from PyQt6.QtGui import QColor,QBrush
from PyQt6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
 QPlainTextEdit,QFileDialog,QMessageBox,QTableWidget,QTableWidgetItem,QTabWidget,QSplitter,QFrame,QComboBox,QLineEdit,
 QDateEdit,QCheckBox,QStackedWidget,QListWidget,QInputDialog,QDoubleSpinBox,QSpinBox,QProgressBar,QHeaderView)
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from engine import load_csv,backtest,annualisation_periods
from strategy import parse_strategy, StrategyError
from data_sources import HistoricalDataService,MarketRequest,INTERVALS
from storage import Store
from optimizer import optimise,parameters
from analytics import trade_metrics

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'user_data'; DATA.mkdir(exist_ok=True)
EXAMPLE='BUY IF RSI < 30 OR CLOSE > SMA_20\nSELL IF RSI > 70'
STYLE='''QWidget{background:#111722;color:#e1e8f4;font-family:Segoe UI;font-size:12px}QLineEdit,QPlainTextEdit,QComboBox,QDateEdit,QDoubleSpinBox,QSpinBox,QListWidget,QTableWidget{background:#1c2736;border:1px solid #344257;border-radius:5px;padding:5px;color:#e1e8f4}QPushButton{background:#263447;border:1px solid #364c68;border-radius:5px;padding:9px}QPushButton:hover{background:#354961}QPushButton#primary{background:#2463d5;border:1px solid #3577ee}QPushButton#nav{background:#172233;text-align:left;border:0;padding:13px}QPushButton#nav:checked{background:#1e416f;border-left:3px solid #57a6ff}QTabBar::tab{background:#263447;padding:9px}QTabBar::tab:selected{background:#245ab8}QHeaderView::section{background:#263447;padding:6px;border:0}QTableWidget{gridline-color:#354253}QProgressBar{border:1px solid #334155;text-align:center}QProgressBar::chunk{background:#2463d5}'''

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
        super().__init__();self.setWindowTitle('StrategyLab | Reference v1.1.1');self.resize(1500,900)
        self.store=Store(DATA/'strategies.sqlite3');self.service=HistoricalDataService(DATA/'candles.sqlite3')
        self.bars=load_csv(ROOT/'sample_prices.csv');self.market='demo';self.timeframe='1d';self.symbol='DEMO';self.result=None;self.saved_id=None;self.busy=False;self.request_id=0
        self.settings={'capital':10000.,'fee':0.001,'slippage':0.,'position':100.}
        shell=QWidget();self.setCentralWidget(shell);row=QHBoxLayout(shell);row.setContentsMargins(0,0,0,0);row.setSpacing(0)
        sidebar=QWidget();sidebar.setFixedWidth(180);sl=QVBoxLayout(sidebar)
        brand=QLabel('◆  StrategyLab');brand.setStyleSheet('font-size:19px;font-weight:bold;color:#74b5ff;padding:16px 4px');sl.addWidget(brand)
        self.stack=QStackedWidget();self.nav=[]
        names=['Dashboard','Strategy editor','Parameters','Optimisation','Saved strategies','History / settings']
        for idx,name in enumerate(names):
            btn=QPushButton('  '+name);btn.setObjectName('nav');btn.setCheckable(True)
            btn.clicked.connect(lambda checked,i=idx:self.navigate(i));sl.addWidget(btn);self.nav.append(btn)
        sl.addStretch();sl.addWidget(QLabel('Reference build · No live orders'))
        row.addWidget(sidebar);row.addWidget(self.stack,1)
        watch=QWidget();watch.setFixedWidth(180);wl=QVBoxLayout(watch)
        lbl=QLabel('WATCHLIST');lbl.setStyleSheet('font-weight:bold;color:#9eb7d7');wl.addWidget(lbl)
        self.watch=QListWidget();self.watch.addItems(['BTCUSDT · Crypto','ETHUSDT · Crypto','SOLUSDT · Crypto','AAPL · Stock','AMD · Stock','NVDA · Stock']);self.watch.itemClicked.connect(self.from_watch);wl.addWidget(self.watch)
        wl.addWidget(QLabel('Single-click to select asset.\nMissing candles require manual download.'))
        row.addWidget(watch)
        self.build_dashboard();self.build_editor();self.build_params();self.build_optimisation();self.build_saved();self.build_history()
        self.setStyleSheet(STYLE);self.navigate(0);self.run_backtest();self.interval.currentTextChanged.connect(self.selection_changed);self.start.dateChanged.connect(self.selection_changed);self.end.dateChanged.connect(self.selection_changed);self.symbol_box.editingFinished.connect(self.selection_changed)
        self.statusBar().showMessage('Synthetic demo candles loaded. Live trading is never enabled.')

    def page(self,name):
        w=QWidget();v=QVBoxLayout(w);v.setContentsMargins(15,12,15,12);v.setSpacing(9)
        h=QLabel(name);h.setStyleSheet('font-size:21px;font-weight:700');v.addWidget(h)
        self.stack.addWidget(w);return w,v
    def navigate(self,i):
        self.stack.setCurrentIndex(i)
        for j,b in enumerate(self.nav):b.setChecked(i==j)
        if i==4:self.refresh_saved()
        if i==5:self.refresh_history()
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
        chart=QSplitter(Qt.Orientation.Vertical)
        self.price_plot=Plot(5);chart.addWidget(self.price_plot)
        self.tabs=QTabWidget();self.equity_plot=Plot(3);self.tabs.addTab(self.equity_plot,'Equity and drawdown')
        self.trades=QTableWidget(0,7);self.trades.setHorizontalHeaderLabels(['Entry time','Exit time','Entry price','Exit price','Quantity','Net P/L','Return %']);self.trades.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.trades,'Completed trades')
        self.analysis=QWidget();analysis_layout=QVBoxLayout(self.analysis);self.analysis_metrics=QLabel('');self.analysis_metrics.setWordWrap(True);analysis_layout.addWidget(self.analysis_metrics)
        self.analysis_plot=Plot(3);analysis_layout.addWidget(self.analysis_plot,1)
        self.tabs.addTab(self.analysis,'Performance analysis')
        self.distribution=Plot(3);self.tabs.addTab(self.distribution,'Trade distribution')
        chart.addWidget(self.tabs);chart.setSizes([440,290]);v.addWidget(chart,1)
    def build_editor(self):
        _,v=self.page('Strategy creator / editor')
        v.addWidget(QLabel('Structured rule language · two rules (BUY IF / SELL IF). No user Python is executed.'))
        self.editor=QPlainTextEdit(EXAMPLE);self.editor.setStyleSheet('font:14px Consolas;background:#162132');v.addWidget(self.editor,1)
        self.validation=QLabel('');v.addWidget(self.validation)
        self.validation_timer=QTimer(self);self.validation_timer.setSingleShot(True);self.validation_timer.setInterval(400);self.validation_timer.timeout.connect(self.validate)
        self.editor.textChanged.connect(lambda:self.validation_timer.start())
        btns=QHBoxLayout()
        for title,fun in [('Validate syntax',self.validate),('Run backtest',lambda:(self.run_backtest(),self.navigate(0))),('Save strategy',self.save_current),('Export rules',self.export_strategy),('Load example',lambda:self.editor.setPlainText(EXAMPLE))]:
            b=QPushButton(title);b.clicked.connect(fun);btns.addWidget(b)
        v.addLayout(btns)
        v.addWidget(QLabel('Examples: BUY IF (RSI < 30 OR CLOSE > SMA_20) AND VOLUME > 5000\nSELL IF RSI > 70\nSupported: CLOSE, VOLUME, RSI, RSI_N, SMA_N, MACD, MACD_SIGNAL; AND, OR, NOT, ( ), comparisons.'))
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
        self.detected=QPlainTextEdit();self.detected.setReadOnly(True);v.addWidget(self.detected,1);self.show_params()
    def build_optimisation(self):
        _,v=self.page('Genetic Algorithm optimiser')
        r=QHBoxLayout();self.pop=QSpinBox();self.pop.setRange(4,100);self.pop.setValue(12);self.gen=QSpinBox();self.gen.setRange(1,100);self.gen.setValue(8)
        self.obj=QComboBox();self.obj.addItems(['return','sharpe'])
        for label,w in [('Population',self.pop),('Generations',self.gen),('Fitness',self.obj)]:r.addWidget(QLabel(label));r.addWidget(w)
        v.addLayout(r)
        run=QPushButton('Optimise numeric thresholds');run.setObjectName('primary');run.clicked.connect(self.run_optimisation);v.addWidget(run);self.opt_btn=run
        self.progress=QProgressBar();v.addWidget(self.progress)
        self.optimised=QPlainTextEdit();self.optimised.setReadOnly(True);v.addWidget(self.optimised,1)
        apply=QPushButton('Copy optimised rules to editor');apply.clicked.connect(self.use_optimised);v.addWidget(apply)
        v.addWidget(QLabel('Genetic search uses the selected historical candles. Test candidate settings on a separate later date range before drawing conclusions.'))
        self.best_source=None
    def build_saved(self):
        _,v=self.page('Saved strategies')
        self.saved=QTableWidget(0,2);self.saved.setHorizontalHeaderLabels(['ID','Strategy name']);self.saved.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);v.addWidget(self.saved,1)
        r=QHBoxLayout()
        for text,fn in [('Refresh',self.refresh_saved),('Load selection',self.load_saved),('Delete selection',self.delete_saved),('Save current editor',self.save_current)]:
            b=QPushButton(text);b.clicked.connect(fn);r.addWidget(b)
        v.addLayout(r)
    def build_history(self):
        _,v=self.page('Run history / settings')
        self.history=QTableWidget(0,5);self.history.setHorizontalHeaderLabels(['Date (UTC)','Symbol','Interval','Return %','Sharpe']);self.history.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);v.addWidget(self.history,1)
        v.addWidget(QLabel('Alpaca credentials: set APCA_API_KEY_ID and APCA_API_SECRET_KEY in your Windows environment.\nNo brokerage connections or order placement. Data downloads require internet; cached ranges run offline.\nCached data and saved strategies are in user_data/ (excluded from Git).'))
    def read_settings(self,*args):
        self.settings={'capital':self.capital.value(),'fee':self.fee.value()/100,'slippage':self.slippage.value()/100,'position':self.position.value()}
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
        self.price_plot.axes();self.empty_chart('No candles available for this selection.\nClick Download historical data.')
        self.equity_plot.axes();self.equity_plot.draw_idle()
        self.analysis_metrics.setText('No results — load data and run a backtest.')
        self.analysis_plot.axes();self.analysis_plot.draw_idle()
        self.distribution.axes();self.distribution.draw_idle()
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
            r=self.result;self.stats.setText(f"Return {r['total_return']:+.2f}%   |   Buy & hold {r['buy_hold']:+.2f}%   |   Sharpe {r['sharpe']:.2f}   |   Max DD {r['max_drawdown']:.2f}%   |   Trades {r['closed_trades']}   |   Wins {r['win_rate']:.1f}%")
            self.plot_candles();self.plot_equity();self.fill_trades();self.plot_analysis();self.store.save_run(self.saved_id,self.symbol,self.timeframe,r)
            self.statusBar().showMessage(f'Backtest complete: {len(self.bars):,} bars · {self.symbol}')
        except Exception as ex:QMessageBox.warning(self,'Backtesting error',str(ex));self.statusBar().showMessage('Last successful results retained — strategy error')
    def plot_candles(self):
        ax=self.price_plot.axes();bars=self.bars
        if not bars:
            self.empty_chart('No candles available. Click Download historical data.');return
        # Render only a bounded recent window; never create thousands of Matplotlib patches on the GUI thread.
        offset=max(0,len(bars)-420);step=max(1,(len(bars)-offset)//360);sample=range(offset,len(bars),step)
        for i in sample:
            b=bars[i];up=b['close']>=b['open'];color='#3ecf9c' if up else '#ef737b'
            ax.vlines(i,b['low'],b['high'],color=color,linewidth=.75)
            bottom=min(b['open'],b['close']);height=max(abs(b['close']-b['open']),b['close']*.00002)
            ax.add_patch(Rectangle((i-step*.32,bottom),max(.65,step*.64),height,facecolor=color,edgecolor=color))
        date_to_index={str(b['date']):i for i,b in enumerate(bars)}
        if self.result is not None:
            for t in self.result["trades"]:
                i=date_to_index.get(t['date']);
                if i is not None:ax.scatter(i,t['price'],marker='^' if t['side']=='BUY' else 'v',s=85,c='#5cdb9c' if t['side']=='BUY' else '#fc7373',zorder=9)
        ax.set_xlim(offset-4,len(bars)+3);ax.set_title(f'{self.symbol}  ·  {self.timeframe}  ·  Candlestick chart / trades',color='#d7e5f6');ax.set_ylabel('Price',color='#abbccf');self.price_plot.draw_idle()
    def plot_equity(self):
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
        ax=self.distribution.axes()
        if pnl:
            ax.hist([v / self.settings['capital'] * 100 for v in pnl],bins=min(18,max(4,int(len(pnl)**.5)*2)),color='#35ba98',edgecolor='#1c2736')
            ax.set_xlabel('Trade P/L as % of starting capital',color='#d6e6fa')
            ax.set_ylabel('Trades',color='#d6e6fa')
            ax.set_title(f"Winners {metrics['winners']} · Losers {metrics['losers']} · Breakeven {metrics['breakeven']}",color='#d6e6fa')
        else:ax.text(.5,.5,'No closed trades',ha='center',va='center',transform=ax.transAxes,color='white')
        self.distribution.draw_idle()
    def fill_trades(self):
        """One row per completed round trip; open positions remain in performance analysis."""
        completed=self.result['completed_trades'];self.trades.setRowCount(len(completed))
        for i,t in enumerate(completed):
            values=[t['entry_date'],t['exit_date'],f"{t['entry_price']:.4f}",
                    f"{t['exit_price']:.4f}",f"{t['quantity']:.5f}",
                    f"{t['pnl']:+.2f}",f"{t['return_pct']:+.2f}%"]
            for j,val in enumerate(values):self.trades.setItem(i,j,QTableWidgetItem(val))
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
                self.saved_id=ident;self.editor.setPlainText(source);self.navigate(1);return
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
    def refresh_history(self):
        rows=self.store.runs();self.history.setRowCount(len(rows))
        for i,(ts,symbol,interval,raw) in enumerate(rows):
            s=json.loads(raw)
            for j,val in enumerate((ts[:19],symbol,interval,f"{s['total_return']:+.2f}",f"{s['sharpe']:.2f}")):self.history.setItem(i,j,QTableWidgetItem(val))
    def run_optimisation(self):
        self.opt_btn.setEnabled(False);self.progress.setValue(5);self.optimised.setPlainText('Running optimisation…')
        source=self.editor.toPlainText();bars=self.bars[:];settings=self.settings.copy();population=self.pop.value();generations=self.gen.value();obj=self.obj.currentText()
        annual=annualisation_periods(self.market if self.market!='demo' else 'csv', self.timeframe)
        self.opt_job=Job(lambda:optimise(source,bars,initial=settings['capital'],fee=settings['fee'],periods_per_year=annual,slippage=settings['slippage'],allocation=settings['position']/100,population=population,generations=generations,objective=obj))
        def finish(out):
            self.best_source=out['source'];self.progress.setValue(100)
            self.optimised.setPlainText(f"Best fitness: {out['best_fitness']:.4f}\nUnique backtests: {out['evaluations']}\nGeneration best: {out['history']}\n\nOptimised rules:\n{out['source']}")
        self.opt_job.completed.connect(finish);self.opt_job.failed.connect(lambda msg:QMessageBox.warning(self,'Optimisation error',msg));self.opt_job.finished.connect(lambda:self.opt_btn.setEnabled(True));self.opt_job.start()
    def use_optimised(self):
        if self.best_source:self.editor.setPlainText(self.best_source);self.navigate(1)

if __name__=='__main__':
    app=QApplication(sys.argv);window=Main();window.show();sys.exit(app.exec())
