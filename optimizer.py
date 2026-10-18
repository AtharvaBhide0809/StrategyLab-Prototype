"""Reference genetic optimiser for numerical rule thresholds; not a trading recommendation."""
import random, re
from dataclasses import dataclass
from engine import backtest

NUMERIC_CONDITION = re.compile(r'\b(RSI(?:_\d+)?|SMA_\d+|CLOSE|VOLUME|MACD(?:_SIGNAL)?)\s*(?:>=|<=|!=|==|>|<)\s*(\d+(?:\.\d+)?)',re.I)

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
        low,high=(0,100) if m.group(1).upper().startswith('RSI') else (max(0,val*.5), max(val*1.5,val+1))
        result.append(Parameter(m.start(2),m.end(2),f'{m.group(1).upper()} threshold {i+1}',val,low,high))
    return result

def apply(source, params, genes):
    for p,x in reversed(list(zip(params,genes))):
        source=source[:p.start]+f'{x:.4f}'.rstrip('0').rstrip('.')+source[p.end:]
    return source

def optimise(source,bars,initial=10000,fee=.001,periods_per_year=252,slippage=0.0,allocation=1.0,population=12,generations=8,objective='return',seed=7,callback=None):
    params=parameters(source)
    if not params: raise ValueError('No numeric comparison thresholds to optimise')
    if len(params)>10: raise ValueError('Optimisation supports at most 10 thresholds at once')
    rng=random.Random(seed)
    def random_gene(): return [rng.uniform(p.low,p.high) for p in params]
    pool=[ [p.current for p in params] ]+[random_gene() for _ in range(population-1)]
    cache={}; history=[]; global_best=None
    def score(genes):
        key=tuple(round(x,5) for x in genes)
        if key not in cache:
            try:
                result=backtest(apply(source,params,genes),bars,initial=initial,fee=fee,periods_per_year=periods_per_year,slippage=slippage,allocation=allocation)
                fitness=result['sharpe'] if objective=='sharpe' else result['total_return']
                cache[key]=(fitness,result)
            except (ValueError,ZeroDivisionError): cache[key]=(-float('inf'),None)
        return cache[key]
    for generation in range(generations):
        ranked=sorted([(score(g)[0],g) for g in pool],key=lambda x:x[0],reverse=True)
        if global_best is None or ranked[0][0]>global_best[0]: global_best=(ranked[0][0],ranked[0][1][:])
        history.append(global_best[0]); callback and callback(generation+1,generations,global_best[0])
        elite=max(2,population//4)
        parents=[g for _,g in ranked[:max(2,population//2)]]
        children=[g[:] for _,g in ranked[:elite]]
        while len(children)<population:
            x,y=rng.sample(parents,2)
            child=[rng.choice((a,b)) for a,b in zip(x,y)]
            for i,p in enumerate(params):
                if rng.random()<.25: child[i]=min(p.high,max(p.low,child[i]+rng.gauss(0,(p.high-p.low)*.08)))
            children.append(child)
        pool=children
    best_source=apply(source,params,global_best[1])
    return {'source':best_source,'best_fitness':global_best[0],'history':history,'evaluations':len(cache),'parameters':params,
            'result':score(global_best[1])[1]}
