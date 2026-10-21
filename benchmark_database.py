"""Isolated database capacity benchmark; never touches user's StrategyLab data."""
import tempfile,time,json
from pathlib import Path
from storage import Store
with tempfile.TemporaryDirectory() as td:
 db=Store(Path(td)/'test.sqlite3')
 ts=time.perf_counter()
 for i in range(100):db.save_strategy(f'Benchmark strategy {i:03d}','BUY IF RSI < 30\nSELL IF RSI > 70',{'capital':10000})
 save_time=time.perf_counter()-ts
 ts=time.perf_counter();strategies=db.strategies();list_time=time.perf_counter()-ts
 trades=[]
 for i in range(1000):
  trades.extend([{'date':f'2025-01-01T00:{i%60:02d}:00','side':'BUY','price':100,'quantity':1,'pnl':None},
  {'date':f'2025-01-01T01:{i%60:02d}:00','side':'SELL','price':101,'quantity':1,'pnl':1}])
 result=dict(total_return=1,buy_hold=2,sharpe=1,max_drawdown=-2,win_rate=100,closed_trades=1000,trades=trades)
 ts=time.perf_counter();db.save_run(strategies[0][0],'TEST','1d',result);save_fills=time.perf_counter()-ts
 with db.db() as conn:
  count=conn.execute('SELECT COUNT(*) FROM fills').fetchone()[0]
  fks=conn.execute('PRAGMA foreign_key_check').fetchall()
 print(json.dumps(dict(saved_strategies=len(strategies),time_to_save_100_strategies_s=round(save_time,4),time_to_list_100_s=round(list_time,4),fills_stored=count,completed_round_trips=1000,save_fills_s=round(save_fills,4),foreign_key_errors=len(fks)),indent=2))
