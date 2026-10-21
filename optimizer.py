"""Deterministic genetic threshold search with optional chronological holdout.

Holdout candles are NEVER used to rank or mutate candidates.
"""
import math
import random
import re
from dataclasses import dataclass
from engine import backtest
from validation import split_index, validate

NUMERIC_CONDITION = re.compile(r'\b(RSI(?:_\d+)?|SMA_\d+|CLOSE|VOLUME|MACD(?:_SIGNAL)?)\s*(?:>=|<=|!=|==|>|<)\s*(\d+(?:\.\d+)?)', re.I)

@dataclass
class Parameter:
    start:int
    end:int
    name:str
    current:float
    low:float
    high:float

def parameters(source):
    result=[]
    for i,m in enumerate(NUMERIC_CONDITION.finditer(source)):
        val=float(m.group(2))
        lo,hi=(0,100) if m.group(1).upper().startswith('RSI') else (max(0,val*.5),max(val*1.5,val+1))
        result.append(Parameter(m.start(2),m.end(2),f'{m.group(1).upper()} threshold {i+1}',val,lo,hi))
    return result

def apply(source,params,genes):
    for p,x in reversed(list(zip(params,genes))):
        source=source[:p.start]+f'{x:.4f}'.rstrip('0').rstrip('.')+source[p.end:]
    return source

def optimise(source,bars,initial=10000,fee=.001,periods_per_year=252,slippage=0.0,allocation=1.0,
             population=12,generations=8,objective='return',seed=7,callback=None,
             training_fraction=1.0,min_trades=0,complexity_penalty=0.0,
             bounds=None):
    params=parameters(source)
    if not params: raise ValueError('No numeric comparison thresholds to optimise')
    if len(params)>10: raise ValueError('Optimisation supports at most 10 thresholds at once')
    if not isinstance(population,int) or population<4 or not isinstance(generations,int) or generations<1:
        raise ValueError('Population must be >=4; generations >=1')
    if objective not in ('return','sharpe','drawdown_adjusted'):
        raise ValueError('Invalid fitness objective')
    if not isinstance(min_trades,int) or min_trades<0: raise ValueError('min_trades must be nonnegative')
    if complexity_penalty<0 or not math.isfinite(complexity_penalty):raise ValueError('Invalid complexity penalty')
    if bounds is not None:
        if len(bounds)!=len(params):raise ValueError('Bounds count must equal number of thresholds')
        for p,(low,high) in zip(params,bounds):
            if not all(map(math.isfinite,(low,high))) or high<=low:raise ValueError('Invalid search bounds')
            p.low,p.high=float(low),float(high)
    if training_fraction!=1.0:
        cut=split_index(bars,training_fraction)
        train_bars=bars[:cut]
    else:
        train_bars=bars
    kwargs=dict(initial=initial,fee=fee,periods_per_year=periods_per_year,slippage=slippage,allocation=allocation)
    rng=random.Random(seed)
    def clamp(g):return [min(p.high,max(p.low,x)) for p,x in zip(params,g)]
    pool=[clamp([p.current for p in params])]+[[rng.uniform(p.low,p.high) for p in params] for _ in range(population-1)]
    cache={};history=[];best=None
    def score(genes):
        key=tuple(round(x,5) for x in genes)
        if key not in cache:
            try:
                result=backtest(apply(source,params,genes),train_bars,**kwargs)
                fit=(result['sharpe'] if objective=='sharpe' else
                     result['total_return']-abs(result['max_drawdown']) if objective=='drawdown_adjusted' else result['total_return'])
                if result['closed_trades']<min_trades:fit=-float('inf')
                else:fit-=complexity_penalty*len(params)
                if not math.isfinite(fit):fit=-float('inf')
                cache[key]=(fit,result)
            except (ValueError,ZeroDivisionError,ArithmeticError): cache[key]=(-float('inf'),None)
        return cache[key]
    for gen in range(generations):
        ranked=sorted(((score(g)[0],g) for g in pool),key=lambda t:t[0],reverse=True)
        if best is None or ranked[0][0]>best[0]:best=(ranked[0][0],ranked[0][1][:])
        history.append(best[0])
        if callback: callback(gen+1,generations,best[0])
        elite=max(2,population//4)
        parents=[g for _,g in ranked[:max(2,population//2)]]
        children=[g[:] for _,g in ranked[:elite]]
        while len(children)<population:
            x,y=rng.sample(parents,2)
            child=[rng.choice((a,b)) for a,b in zip(x,y)]
            for i,p in enumerate(params):
                if rng.random()<.25:child[i]=min(p.high,max(p.low,child[i]+rng.gauss(0,(p.high-p.low)*.08)))
            children.append(child)
        pool=children
    if best[0]==-float('inf'):
        raise ValueError('No candidate satisfied the minimum completed-trade requirement')
    selected=apply(source,params,best[1]);report=None
    if training_fraction!=1.0:
        report=validate(selected,bars,training_fraction=training_fraction,minimum_trades=min_trades,**kwargs)
    return dict(source=selected,best_fitness=best[0],history=history,evaluations=len(cache),
                parameters=params,result=score(best[1])[1],validation=report,
                training_candles=len(train_bars),holdout_candles=len(bars)-len(train_bars))
