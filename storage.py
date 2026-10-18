from contextlib import contextmanager

"""Local SQLite strategy, run and configuration store."""
import sqlite3, json
from datetime import datetime, timezone

class Store:
    def __init__(self,path):
        self.path=str(path)
        with self.db() as d:
            d.executescript('''
            CREATE TABLE IF NOT EXISTS profiles(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
            INSERT OR IGNORE INTO profiles(id,name) VALUES(1,'Local user');
            CREATE TABLE IF NOT EXISTS strategies(id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id), name TEXT NOT NULL, source TEXT NOT NULL, settings TEXT NOT NULL DEFAULT '{}', created TEXT NOT NULL, UNIQUE(profile_id,name));
            CREATE TABLE IF NOT EXISTS runs(id INTEGER PRIMARY KEY, strategy_id INTEGER REFERENCES strategies(id) ON DELETE SET NULL, symbol TEXT NOT NULL, timeframe TEXT NOT NULL, timestamp TEXT NOT NULL, stats_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS fills(id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE, date TEXT NOT NULL, side TEXT NOT NULL, price REAL NOT NULL, quantity REAL NOT NULL, pnl REAL);
            ''')
            d.execute('PRAGMA foreign_keys=ON')
    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("PRAGMA foreign_keys=ON")

            with connection:
                yield connection

        finally:
            connection.close()
    def save_strategy(self,name,source,settings):
        name=name.strip()
        if not name: raise ValueError('Strategy name cannot be empty')
        with self.db() as d:
            d.execute('''INSERT INTO strategies(profile_id,name,source,settings,created) VALUES(1,?,?,?,?) ON CONFLICT(profile_id,name) DO UPDATE SET source=excluded.source,settings=excluded.settings''', (name,source,json.dumps(settings),datetime.now(timezone.utc).isoformat()))
    def strategies(self):
        with self.db() as d: return d.execute('SELECT id,name,source,settings FROM strategies WHERE profile_id=1 ORDER BY name').fetchall()
    def delete_strategy(self,ident):
        with self.db() as d: d.execute('DELETE FROM strategies WHERE id=?',(ident,))
    def save_run(self, strategy_id, symbol, timeframe, result):
        stats={k:result[k] for k in ('total_return','buy_hold','sharpe','max_drawdown','win_rate','closed_trades')}
        with self.db() as d:
            cur=d.execute('INSERT INTO runs(strategy_id,symbol,timeframe,timestamp,stats_json) VALUES(?,?,?,?,?)',(strategy_id,symbol,timeframe,datetime.now(timezone.utc).isoformat(),json.dumps(stats)))
            d.executemany('INSERT INTO fills(run_id,date,side,price,quantity,pnl) VALUES(?,?,?,?,?,?)',[(cur.lastrowid,t['date'],t['side'],t['price'],t['quantity'],t['pnl']) for t in result['trades']])
    def runs(self):
        with self.db() as d: return d.execute('SELECT timestamp,symbol,timeframe,stats_json FROM runs ORDER BY id DESC LIMIT 200').fetchall()
