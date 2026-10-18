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

def indicators(bars, names):
    closes = [b['close'] for b in bars]
    data = {'CLOSE': closes, 'VOLUME': [b['volume'] for b in bars]}
    for name in names:
        if name.startswith('SMA_'):
            data[name] = sma(closes, int(name.split('_')[1]))
        if name == 'RSI' or name.startswith('RSI_'):
            data[name] = rsi(closes, 14 if name == 'RSI' else int(name.split('_')[1]))
    if 'MACD' in names or 'MACD_SIGNAL' in names:
        e12,e26=ema(closes,12),ema(closes,26)
        macd=[a-b if a is not None and b is not None else None for a,b in zip(e12,e26)]
        data['MACD']=macd
        valid=[x for x in macd if x is not None]
        signal=ema(valid,9)
        data['MACD_SIGNAL']=[None]*(len(macd)-len(valid))+signal
    return data

def backtest(source, bars, initial=10000.0, fee=0.001, periods_per_year=252, slippage=0.0, allocation=1.0):
    if len(bars) < 35: raise ValueError("At least 35 candles are required")
    if initial <= 0 or not 0 <= fee < 1 or not 0 <= slippage < 1 or not 0 < allocation <= 1: raise ValueError('Invalid capital, fee, slippage or allocation')
    rules = parse_strategy(source)
    names = needed_fields(rules['BUY']) | needed_fields(rules['SELL'])
    series = indicators(bars, names)
    cash, shares, trades, equity = initial, 0.0, [], []
    entry_cost = None
    # Decision on yesterday's close; fill at today's open, avoiding close-lookahead bias.
    for i,b in enumerate(bars):
        if i > 0:
            vals={name: col[i-1] for name,col in series.items()}
            # Don't execute any rule until its indicators have warmed up.
            if all(series[name][i-1] is not None for name in names):
                if shares == 0 and evaluate(rules['BUY'], vals):
                    price=b['open']*(1+slippage); budget=cash*allocation; qty=budget/(price*(1+fee))
                    if qty > 0:
                        entry_cost=budget; shares=qty; cash-=budget
                        trades.append({'date': str(b['date']), 'side':'BUY', 'price':price, 'quantity':qty, 'pnl':None})
                elif shares > 0 and evaluate(rules['SELL'], vals):
                    price=b['open']*(1-slippage); proceeds=shares*price*(1-fee)
                    cash+=proceeds
                    trades.append({'date':str(b['date']), 'side':'SELL', 'price':price, 'quantity':shares, 'pnl':proceeds-entry_cost})
                    shares=0.0; entry_cost=None
        equity.append(cash+shares*b['close'])
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
    return {'equity':equity, 'dates':[str(b['date']) for b in bars], 'trades':trades,
            'total_return':ret, 'buy_hold':bh, 'max_drawdown':min(drawdowns),
            'drawdown':drawdowns, 'sharpe':sharpe, 'closed_trades':len(sells),
            'win_rate':100*sum(t['pnl']>0 for t in sells)/len(sells) if sells else 0}
