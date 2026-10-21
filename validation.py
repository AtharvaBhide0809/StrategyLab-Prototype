"""Chronological train / held-out validation. Educational, not predictive."""
from __future__ import annotations
import math
from engine import backtest


def split_index(bars, training_fraction=0.7, minimum=35):
    if not math.isfinite(training_fraction) or not 0.5 <= training_fraction <= 0.85:
        raise ValueError('Training fraction must be between 0.5 and 0.85')
    n = len(bars)
    cut = int(n * training_fraction)
    if cut < minimum or n-cut < minimum:
        raise ValueError('Need at least 35 candles in both training and holdout windows')
    dates = [str(x['date']) for x in bars]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError('Candles must be chronological and have unique timestamps')
    return cut


def validate(source, bars, training_fraction=0.7, minimum_trades=2, **kwargs):
    """Fit no models; report IS and untouched OOS results with warmup-only prehistory.

    The out-of-sample backtest starts flat at the split and cannot trade on training bars.
    The full input is used solely to warm up indicators.
    """
    cut = split_index(bars, training_fraction)
    if not isinstance(minimum_trades,int) or minimum_trades < 0:
        raise ValueError('minimum_trades must be a nonnegative integer')
    train = backtest(source, bars[:cut], **kwargs)
    held = backtest(source, bars, trading_start=cut, **kwargs)
    # Track only held-out candles; initial capital is held unchanged before the split.
    equity = held['equity'][cut:]
    held['equity'] = equity
    held['dates'] = held['dates'][cut:]
    peak=kwargs.get('initial',10000.0)
    drawdowns=[]
    for value in equity:
        peak=max(peak,value)
        drawdowns.append((value/peak-1)*100)
    held['drawdown']=drawdowns
    held['max_drawdown']=min(drawdowns)
    held['total_return']=(equity[-1]/kwargs.get('initial',10000.0)-1)*100
    held['total_pnl']=equity[-1]-kwargs.get('initial',10000.0)
    daily=[equity[i]/equity[i-1]-1 for i in range(1,len(equity))]
    mean=sum(daily)/len(daily) if daily else 0.0
    sd=math.sqrt(sum((v-mean)**2 for v in daily)/(len(daily)-1)) if len(daily)>1 else 0.0
    held['sharpe']=mean/sd*math.sqrt(held['periods_per_year']) if sd else 0.0
    held['buy_hold'] = (bars[-1]['close']/bars[cut]['close']-1)*100
    return {'training':train, 'holdout':held, 'split_index':cut,
            'train_end':str(bars[cut-1]['date']), 'holdout_start':str(bars[cut]['date']),
            'minimum_trades':minimum_trades,
            'train_sufficient':train['closed_trades'] >= minimum_trades,
            'holdout_sufficient':held['closed_trades'] >= minimum_trades,
            'return_gap_pct_points':train['total_return']-held['total_return'],
            'warning':'Historical results are not a forecast. OOS can still overfit when repeatedly inspected.'}
