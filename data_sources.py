"""Historical data adapters. Network access happens ONLY in provider.fetch()."""
from __future__ import annotations
import csv
import io
import json
import os
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

INTERVALS = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '1d': 1440}

@dataclass
class MarketRequest:
    market: str
    symbol: str
    timeframe: str
    start: date
    end: date

    def __post_init__(self):
        if self.market not in ('crypto', 'stocks'):
            raise ValueError('Market must be crypto or stocks')
        if self.timeframe not in INTERVALS:
            raise ValueError('Unsupported timeframe')
        if not re.fullmatch(r'[A-Za-z0-9.\-]{1,24}', self.symbol):
            raise ValueError('Invalid symbol (e.g. BTCUSDT or AAPL)')
        if self.start > self.end or self.end > datetime.now(timezone.utc).date():
            raise ValueError('Check date range: end must not be in the future')

class ProviderError(ValueError):
    pass

def iso_time(value):
    """Normalise all dates to UTC ISO8601 strings, preserving intraday precision."""
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    else:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec='seconds')

def candle(t, o, h, l, c, v):
    b = {'date': iso_time(t), 'open': float(o), 'high': float(h), 'low': float(l),
         'close': float(c), 'volume': float(v)}
    if not (0 < b['open'] <= b['high'] and 0 < b['close'] <= b['high'] and
            0 < b['low'] <= min(b['open'], b['close']) and b['volume'] >= 0):
        raise ProviderError('Invalid OHLCV values returned by provider')
    return b

def request_bytes(url, headers=None, timeout=35):
    req = Request(url, headers={'User-Agent': 'StrategyLab-NEA/0.2', **(headers or {})})
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        if exc.code == 404: raise ProviderError('No historical archive/data found for this period or symbol') from exc
        if exc.code in (401, 403): raise ProviderError('Access denied. Check API keys and feed permissions') from exc
        raise ProviderError(f'Data provider returned HTTP {exc.code}') from exc
    except URLError as exc:
        raise ProviderError(f'Network problem: {exc.reason}') from exc

class BinanceArchive:
    name = 'Binance public spot archive'
    def fetch(self, req):
        if req.market != 'crypto': raise ProviderError('Binance adapter is for crypto only')
        # Monthly archives only for completed months. Current month uses daily archives.
        today = datetime.now(timezone.utc).date()
        months = []
        m = date(req.start.year, req.start.month, 1)
        while m <= req.end:
            months.append(m)
            m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        bars = []
        for month in months:
            following = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
            if following < today.replace(day=1) or (following == today.replace(day=1) and today.day >= 8):
                periods = [('monthly', month.strftime('%Y-%m'))]
            else:
                d = max(req.start, month)
                periods = []
                while d <= min(req.end, following-timedelta(days=1), today-timedelta(days=1)):
                    periods.append(('daily', d.isoformat()))
                    d += timedelta(days=1)
            for unit, period in periods:
                sym = req.symbol.upper()
                base = f'{sym}-{req.timeframe}-{period}'
                url = f'https://data.binance.vision/data/spot/{unit}/klines/{sym}/{req.timeframe}/{base}.zip'
                data = request_bytes(url)
                try:
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        csv_names = [name for name in archive.namelist() if name.endswith('.csv')]
                        if len(csv_names) != 1: raise ProviderError('Unexpected ZIP structure')
                        with archive.open(csv_names[0]) as f:
                            rows = csv.reader(io.TextIOWrapper(f, encoding='utf-8-sig'))
                            for row in rows:
                                if not row or row[0].lower() == 'open time': continue
                                stamp = int(row[0]); divisor = 1_000_000 if stamp > 10**14 else 1_000
                                time = datetime.fromtimestamp(stamp/divisor, tz=timezone.utc)
                                if req.start <= time.date() <= req.end:
                                    bars.append(candle(time, row[1],row[2],row[3],row[4],row[5]))
                except (zipfile.BadZipFile, IndexError, ValueError) as exc:
                    raise ProviderError('Invalid Binance CSV / ZIP archive') from exc
        return sorted(bars, key=lambda b: b['date'])

class AlpacaIEX:
    name = 'Alpaca free IEX US stocks'
    def fetch(self, req):
        if req.market != 'stocks': raise ProviderError('Alpaca adapter is for stocks only')
        key = os.environ.get('ALPACA_API_KEY_ID','').strip()
        secret = os.environ.get('ALPACA_API_SECRET_KEY','').strip()
        if not key or not secret:
            raise ProviderError('Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY environment variables')
        timeframe = {'1m':'1Min','5m':'5Min','15m':'15Min','1h':'1Hour','1d':'1Day'}[req.timeframe]
        base = 'https://data.alpaca.markets/v2/stocks/' + req.symbol.upper() + '/bars'
        params = dict(timeframe=timeframe, start=req.start.isoformat()+'T00:00:00Z',
                      end=(req.end+timedelta(days=1)).isoformat()+'T00:00:00Z',
                      feed='iex', adjustment='raw', limit=10000)
        headers = {'APCA-API-KEY-ID':key, 'APCA-API-SECRET-KEY':secret}
        bars, token, seen = [], None, set()
        while True:
            if token: params['page_token'] = token
            page = json.loads(request_bytes(base+'?'+urlencode(params), headers=headers))
            for b in page.get('bars') or []:
                bars.append(candle(b['t'],b['o'],b['h'],b['l'],b['c'],b['v']))
            token = page.get('next_page_token')
            if not token: break
            if token in seen: raise ProviderError('Repeated pagination token from Alpaca')
            seen.add(token)
        return sorted(bars, key=lambda b:b['date'])

class CandleCache:
    """Unique provider/market/symbol/timeframe/timestamp keys prevent data collisions."""
    def __init__(self, path):
        self.path = str(path)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS candles (
                provider TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL, timestamp TEXT NOT NULL,
                open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL,
                close REAL NOT NULL, volume REAL NOT NULL,
                PRIMARY KEY (provider, market, symbol, timeframe, timestamp))''')
            db.execute('''CREATE TABLE IF NOT EXISTS downloads (
                provider TEXT NOT NULL, market TEXT NOT NULL, symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                PRIMARY KEY (provider, market, symbol, timeframe, start_date, end_date))''')
    def connect(self): return sqlite3.connect(self.path)
    def save(self, provider, req, bars):
        with self.connect() as db:
            db.executemany('''INSERT OR REPLACE INTO candles VALUES(?,?,?,?,?,?,?,?,?,?)''',
                [(provider,req.market,req.symbol.upper(),req.timeframe,b['date'],b['open'],b['high'],
                  b['low'],b['close'],b['volume']) for b in bars])
            db.execute('INSERT OR REPLACE INTO downloads VALUES(?,?,?,?,?,?)',
                       (provider,req.market,req.symbol.upper(),req.timeframe,req.start.isoformat(),req.end.isoformat()))
    def load(self, provider, req):
        with self.connect() as db:
            result = db.execute('''SELECT timestamp,open,high,low,close,volume FROM candles
                 WHERE provider=? AND market=? AND symbol=? AND timeframe=?
                 AND substr(timestamp,1,10)>=? AND substr(timestamp,1,10)<=?
                 ORDER BY timestamp''', (provider,req.market,req.symbol.upper(),req.timeframe,
                                          req.start.isoformat(),req.end.isoformat())).fetchall()
        return [dict(date=r[0],open=r[1],high=r[2],low=r[3],close=r[4],volume=r[5]) for r in result]
    def has_download(self, provider, req):
        with self.connect() as db:
            intervals = db.execute('''SELECT start_date,end_date FROM downloads WHERE
                 provider=? AND market=? AND symbol=? AND timeframe=? ORDER BY start_date''',
                 (provider, req.market, req.symbol.upper(), req.timeframe)).fetchall()
        # Complete coverage can be assembled from adjacent downloaded intervals.
        covered = req.start
        for a,b in intervals:
            a,b=date.fromisoformat(a), date.fromisoformat(b)
            if a <= covered <= b+timedelta(days=1): covered=max(covered,b+timedelta(days=1))
            if covered > req.end: return True
        return False

class HistoricalDataService:
    def __init__(self, cache_path):
        self.cache = CandleCache(cache_path)
        self.providers = {'crypto':BinanceArchive(), 'stocks':AlpacaIEX()}
    def get(self, req, offline=False):
        provider = self.providers[req.market]
        cached = self.cache.load(provider.name, req)
        if self.cache.has_download(provider.name,req): return cached, 'Cached (SQLite)'
        if offline:
            if cached: return cached, 'Partial local cache (incomplete period)'
            raise ProviderError('Requested range not fully cached. Download online first.')
        bars = provider.fetch(req)
        if not bars: raise ProviderError('Provider returned no candles for the selected period')
        self.cache.save(provider.name,req,bars)
        return self.cache.load(provider.name,req), 'Downloaded and cached'
