"""Historical OHLCV backtesting. Signals at close, filled at NEXT bar open."""
import csv
import math
from datetime import datetime
from strategy import parse_strategy, needed_fields, evaluate

def load_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        bars = []
        for row in csv.DictReader(f):
            bars.append({'date': row['Date'],
                         **{k.lower(): float(row[k]) for k in ('Open','High','Low','Close','Volume')}})
    bars.sort(key=lambda r: r['date'])
    if len(bars) < 35 or len({r['date'] for r in bars}) != len(bars):
        raise ValueError('CSV needs 35+ unique timestamp records')
    if any(b['open'] <= 0 or b['close'] <= 0 or b['high'] < b['low'] for b in bars):
        raise ValueError('Invalid OHLC prices in CSV')
    return bars

def sma(series, n):
    out = [None] * len(series)
    rolling = 0.0
    for i, x in enumerate(series):
        rolling += x
        if i >= n: rolling -= series[i-n]
        if i >= n-1: out[i] = rolling/n
    return out

def ema(series, n):
    out = [None] * len(series)
    if len(series) < n: return out
    alpha = 2/(n+1)
    prev = sum(series[:n])/n
    out[n-1] = prev
    for i in range(n, len(series)):
        prev = alpha*series[i]+(1-alpha)*prev
        out[i] = prev
    return out

def rsi(series, n=14):
    out = [None] * len(series)
    if len(series) <= n: return out
    gains = [max(series[i]-series[i-1], 0) for i in range(1, len(series))]
    losses = [max(series[i-1]-series[i], 0) for i in range(1, len(series))]
    ag, al = sum(gains[:n])/n, sum(losses[:n])/n
    def score(g,l): return 100 if l == 0 else 100-100/(1+g/l)
    out[n] = score(ag,al)
    for i in range(n+1, len(series)):
        ag=(ag*(n-1)+gains[i-1])/n; al=(al*(n-1)+losses[i-1])/n
        out[i]=score(ag,al)
    return out

class Indicator:
    """Extensible, deterministic indicator interface (subclass and register)."""
    name = None
    def matches(self, name):
        return name == self.name
    def calculate(self, bars, name, cache):
        raise NotImplementedError

class MovingAverageIndicator(Indicator):
    def matches(self,name): return name.startswith('SMA_')
    def calculate(self,bars,name,cache):return sma(cache['CLOSE'],int(name.split('_')[-1]))

class RelativeStrengthIndicator(Indicator):
    def matches(self,name):return name=='RSI' or name.startswith('RSI_')
    def calculate(self,bars,name,cache):return rsi(cache['CLOSE'],14 if name=='RSI' else int(name.split('_')[-1]))

class VolumeMovingAverageIndicator(Indicator):
    def matches(self,name):return name.startswith('VOLUME_SMA_')
    def calculate(self,bars,name,cache):return sma(cache['VOLUME'],int(name.split('_')[-1]))

class MACDIndicator(Indicator):
    def matches(self,name):return name in ('MACD','MACD_SIGNAL')
    def calculate(self,bars,name,cache):
        e12,e26=ema(cache['CLOSE'],12),ema(cache['CLOSE'],26)
        macd=[a-b if a is not None and b is not None else None for a,b in zip(e12,e26)]
        if name=='MACD':return macd
        valid=[x for x in macd if x is not None]
        return [None]*(len(macd)-len(valid))+ema(valid,9)

INDICATOR_REGISTRY=[MovingAverageIndicator(),RelativeStrengthIndicator(),VolumeMovingAverageIndicator(),MACDIndicator()]

def register_indicator(indicator):
    if not isinstance(indicator,Indicator):raise TypeError('Expected Indicator subclass')
    INDICATOR_REGISTRY.insert(0,indicator)

def indicators(bars,names):
    cache={'CLOSE':[b['close'] for b in bars], 'VOLUME':[b['volume'] for b in bars]}
    for name in names:
        if name in cache:continue
        handler=next((item for item in INDICATOR_REGISTRY if item.matches(name)),None)
        if handler is None:raise ValueError(f'Unknown indicator: {name}')
        cache[name]=handler.calculate(bars,name,cache)
    return cache

def annualisation_periods(asset_type='crypto', timeframe='1d'):
    """Approximate periodic samples/year, assuming regular 24/7 crypto or US cash sessions."""
    minutes = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '1d': 1440}
    if timeframe not in minutes:
        raise ValueError(f'Unsupported timeframe: {timeframe}')
    if asset_type == 'crypto':
        return 365 if timeframe == '1d' else 365 * 24 * 60 / minutes[timeframe]
    if asset_type in ('stocks', 'stock', 'csv'):
        return 252 if timeframe == '1d' else 252 * 390 / minutes[timeframe]
    raise ValueError(f'Unsupported asset type: {asset_type}')


def backtest(source, bars, initial=10000.0, fee=0.001, periods_per_year=None,
             slippage=0.0, allocation=1.0, asset_type='crypto', timeframe='1d', trading_start=0):
    if periods_per_year is None:
        periods_per_year = annualisation_periods(asset_type, timeframe)
    if not math.isfinite(periods_per_year) or periods_per_year <= 0:
        raise ValueError('periods_per_year must be positive and finite')
    if not isinstance(trading_start, int) or not 0 <= trading_start < len(bars):
        raise ValueError('Invalid trading_start index')
    if len(bars) < 35: raise ValueError("At least 35 candles are required")
    if initial <= 0 or not 0 <= fee < 1 or not 0 <= slippage < 1 or not 0 < allocation <= 1: raise ValueError('Invalid capital, fee, slippage or allocation')
    rules = parse_strategy(source)
    names = needed_fields(rules['BUY']) | needed_fields(rules['SELL'])
    series = indicators(bars, names)
    cash, shares, trades, equity = initial, 0.0, [], []
    entry_cost = None
    entry_date = None
    entry_price = None
    completed_trades = []
    # Decision on yesterday's close; fill at today's open, avoiding close-lookahead bias.
    for i,b in enumerate(bars):
        if i > 0 and i >= trading_start:
            vals={name: col[i-1] for name,col in series.items()}
            # Don't execute any rule until its indicators have warmed up.
            if all(series[name][i-1] is not None for name in names):
                if shares == 0 and evaluate(rules['BUY'], vals):
                    price=b['open']*(1+slippage); budget=cash*allocation; qty=budget/(price*(1+fee))
                    if qty > 0:
                        entry_cost=budget; entry_date=str(b['date']); entry_price=price; shares=qty; cash-=budget
                        trades.append({'date': str(b['date']), 'side':'BUY', 'price':price, 'quantity':qty, 'pnl':None})
                elif shares > 0 and evaluate(rules['SELL'], vals):
                    price=b['open']*(1-slippage); proceeds=shares*price*(1-fee)
                    cash+=proceeds
                    pnl=proceeds-entry_cost
                    trades.append({'date':str(b['date']), 'side':'SELL', 'price':price, 'quantity':shares, 'pnl':pnl})
                    completed_trades.append({'entry_date':entry_date,'exit_date':str(b['date']),
                        'entry_price':entry_price,'exit_price':price,'quantity':shares,
                        'pnl':pnl,'return_pct':100*pnl/entry_cost})
                    shares=0.0; entry_cost=None; entry_date=None; entry_price=None
        equity.append(cash+shares*b['close'])
    # The trading_start gate skips warmup-only execution, not indicator calculation.
    # Return the full trace for charting; validation isolates the evaluation window.
    ret=(equity[-1]/initial-1)*100
    bh=(bars[-1]['close']/bars[0]['close']-1)*100
    peak=equity[0]; drawdowns=[]
    for x in equity:
        peak=max(peak,x); drawdowns.append((x/peak-1)*100)
    daily=[equity[i]/equity[i-1]-1 for i in range(1,len(equity))]
    mean=sum(daily)/len(daily)
    std=math.sqrt(sum((x-mean)**2 for x in daily)/(len(daily)-1)) if len(daily)>1 else 0
    sharpe=mean/std*math.sqrt(periods_per_year) if std>0 else 0
    sells=[t for t in trades if t['side']=='SELL']
    gains=[t['pnl'] for t in sells if t['pnl'] > 0]
    losses=[t['pnl'] for t in sells if t['pnl'] < 0]
    realised_pnl=sum(t['pnl'] for t in sells)
    gross_profit=sum(gains); gross_loss=-sum(losses)
    unrealised_pnl=shares*bars[-1]['close']-entry_cost if shares > 0 else 0.0
    final_equity=equity[-1]; total_pnl=final_equity-initial
    if not math.isclose(total_pnl, realised_pnl+unrealised_pnl, rel_tol=1e-9, abs_tol=1e-6):
        raise ArithmeticError('Equity does not reconcile with realised/unrealised P&L')
    return {'equity':equity, 'dates':[str(b['date']) for b in bars], 'trades':trades,
            'completed_trades':completed_trades,
            'total_return':ret, 'buy_hold':bh, 'max_drawdown':min(drawdowns),
            'drawdown':drawdowns, 'sharpe':sharpe, 'periods_per_year':periods_per_year,
            'closed_trades':len(sells), 'win_rate':100*len(gains)/len(sells) if sells else 0,
            'winning_trades':len(gains), 'losing_trades':len(losses),
            'breakeven_trades':len(sells)-len(gains)-len(losses),
            'gross_profit':gross_profit, 'gross_loss':gross_loss, 'realised_pnl':realised_pnl,
            'profit_factor':gross_profit/gross_loss if gross_loss > 0 else None,
            'expectancy':realised_pnl/len(sells) if sells else None,
            'cash':cash, 'position_quantity':shares, 'open_position':shares > 0,
            'unrealised_pnl':unrealised_pnl, 'final_equity':final_equity, 'total_pnl':total_pnl}
