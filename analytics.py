"""Derived statistics for completed trade records (simulation amounts, not live trading)."""

def trade_metrics(trades):
    pnl=[float(t['pnl']) for t in trades if t['side']=='SELL' and t.get('pnl') is not None]
    gains=[v for v in pnl if v>0];losses=[v for v in pnl if v<0]
    gross_profit=sum(gains);gross_loss=-sum(losses)
    return dict(pnl=pnl,gross_profit=gross_profit,gross_loss=gross_loss,
                net_pnl=sum(pnl),profit_factor=gross_profit/gross_loss if gross_loss else None,
                expectancy=sum(pnl)/len(pnl) if pnl else None,
                winners=len(gains),losers=len(losses),breakeven=len(pnl)-len(gains)-len(losses))


from collections import defaultdict
from datetime import datetime
import math


def advanced_report(result, initial):
    """Descriptive, unleveraged performance reporting; no forward-looking inference."""
    if not math.isfinite(initial) or initial <= 0:
        raise ValueError('initial capital must be positive')
    dates=result['dates']; equity=result['equity']
    if not equity or len(dates)!=len(equity):
        raise ValueError('equity and dates must be nonempty and aligned')
    round_trips=result.get('completed_trades', [])
    pnls=[float(t['pnl']) for t in round_trips]
    if not all(math.isfinite(x) for x in equity+pnls):
        raise ValueError('Nonfinite financial values')
    monthly=defaultdict(float)
    # Compound periodic returns from end-of-period marked-to-market equity.
    monthly_end={}
    for date,value in zip(dates,equity):
        month=str(date)[:7]
        monthly_end[month]=value
    previous=initial
    periodic=[]
    for month,ending in sorted(monthly_end.items()):
        periodic.append((month,(ending/previous-1)*100))
        previous=ending
    longest_win=longest_loss=win_streak=loss_streak=0
    for v in pnls:
        win_streak=win_streak+1 if v>0 else 0
        loss_streak=loss_streak+1 if v<0 else 0
        longest_win=max(longest_win,win_streak)
        longest_loss=max(longest_loss,loss_streak)
    profitable=[x for x in pnls if x>0]
    losing=[x for x in pnls if x<0]
    returns=[equity[i]/equity[i-1]-1 for i in range(1,len(equity)) if equity[i-1]>0]
    downside=math.sqrt(sum(min(r,0)**2 for r in returns)/len(returns)) if returns else 0
    mean=sum(returns)/len(returns) if returns else 0
    sortino=mean/downside*math.sqrt(result.get('periods_per_year',252)) if downside else None
    peak=initial; underwater=0; longest_underwater=0
    for v in equity:
        peak=max(peak,v)
        underwater=underwater+1 if v<peak else 0
        longest_underwater=max(longest_underwater,underwater)
    return {'monthly_returns':periodic,'trade_pnls':pnls,'best_trade':max(pnls) if pnls else None,
            'worst_trade':min(pnls) if pnls else None,'average_win':sum(profitable)/len(profitable) if profitable else None,
            'average_loss':sum(losing)/len(losing) if losing else None,'longest_win_streak':longest_win,
            'longest_loss_streak':longest_loss,'max_underwater_bars':longest_underwater,
            'sortino':sortino,'relative_return':result['total_return']-result['buy_hold'],
            'cumulative_trade_pnl':[sum(pnls[:i+1]) for i in range(len(pnls))]}


def periodic_returns(dates, equity, initial, frequency='monthly'):
    """Non-overlapping calendar period returns from UTC-labelled candle equity.

    The first period begins at initial capital. Subsequent periods compound
    from the previous period's last marked-to-market equity.
    """
    from datetime import datetime
    if frequency not in ('daily','weekly','monthly','quarterly','yearly'):
        raise ValueError('Unsupported return aggregation')
    if not len(dates) or len(dates)!=len(equity) or initial<=0:
        raise ValueError('Period returns require aligned data and positive capital')
    endings={}
    for stamp,amount in zip(dates,equity):
        dt=datetime.fromisoformat(str(stamp).replace('Z','+00:00'))
        if frequency=='daily':key=dt.date().isoformat()
        elif frequency=='weekly':
            iso=dt.isocalendar();key=f'{iso.year}-W{iso.week:02d}'
        elif frequency=='monthly':key=dt.strftime('%Y-%m')
        elif frequency=='quarterly':key=f'{dt.year}-Q{(dt.month-1)//3+1}'
        else:key=str(dt.year)
        if not math.isfinite(amount) or amount<=0:raise ValueError('Invalid equity value')
        endings[key]=amount
    previous=initial;result=[]
    for key,ending in sorted(endings.items()):
        result.append((key,(ending/previous-1)*100));previous=ending
    return result


def trade_excursions(completed, bars):
    """Per-trade MFE/MAE from high/low of included candles; indicative, not intrabar fills."""
    from datetime import datetime
    def timestamp(value):return datetime.fromisoformat(str(value).replace('Z','+00:00')).replace(tzinfo=None)
    out=[]
    for trade in completed:
        entry=timestamp(trade['entry_date']);exit_=timestamp(trade['exit_date'])
        segment=[b for b in bars if entry<=timestamp(b['date'])<=exit_]
        price=float(trade['entry_price'])
        if not segment or price<=0:out.append((None,None));continue
        out.append(((max(b['high'] for b in segment)/price-1)*100,
                    (min(b['low'] for b in segment)/price-1)*100))
    return out

def trade_durations(trades):
    from datetime import datetime
    result=[]
    for t in trades:
        a=datetime.fromisoformat(str(t['entry_date']).replace('Z','+00:00'))
        b=datetime.fromisoformat(str(t['exit_date']).replace('Z','+00:00'))
        result.append((b-a).total_seconds()/60)
    return result

def drawdown_segments(equity, initial):
    """Peak-to-recovery durations in bars; includes an unrecovered final episode."""
    peak=initial;underwater=0;episodes=[]
    for value in equity:
        if value>=peak:
            if underwater:episodes.append(underwater);underwater=0
            peak=value
        else:underwater+=1
    if underwater:episodes.append(underwater)
    return episodes
