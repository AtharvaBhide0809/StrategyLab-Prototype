"""Benchmarks use generated deterministic data and should also run on the user's Windows hardware."""
from engine import backtest
from optimizer import optimise
from strategy import parse_strategy
from datetime import date,timedelta
import math,time,json
SRC='BUY IF RSI < 35\nSELL IF RSI > 65'
def synthetic(days=1827):
 out=[];base=date(2020,1,1)
 for i in range(days):
  close=100+3*math.sin(i/8)+i*.01
  out.append(dict(date=(base+timedelta(days=i)).isoformat(),open=close+.13,high=close+1,low=close-1,close=close,volume=1000+i%30))
 return out
def timed(fn):
 start=time.perf_counter();output=fn();return round(time.perf_counter()-start,4),output
if __name__=='__main__':
 bars=synthetic();parse_times=[timed(lambda:parse_strategy(SRC))[0] for _ in range(1000)]
 back_time,result=timed(lambda:backtest(SRC,bars,asset_type='stocks',timeframe='1d'))
 opt_time,opt=timed(lambda:optimise(SRC,bars,population=30,generations=50,training_fraction=.7,min_trades=2))
 print(json.dumps({'python_platform':'local test environment','parser_max_s':max(parse_times),'parser_mean_s':sum(parse_times)/len(parse_times),'five_year_daily_backtest_s':back_time,'backtest_trades':result['closed_trades'],'optimisation_50x30_s':opt_time,'optimiser_unique_backtests':opt['evaluations'],'optimisation_fit':opt['best_fitness'],'holdout_trades':opt['validation']['holdout']['closed_trades'],'threshold_parser_s':.1,'threshold_backtest_s':3,'threshold_optimisation_s':300},indent=2))
