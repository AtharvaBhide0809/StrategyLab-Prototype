import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch
from data_sources import MarketRequest, HistoricalDataService, BinanceArchive, AlpacaIEX, ProviderError

class SourceTests(unittest.TestCase):
    def test_binance_microseconds(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            z.writestr('BTCUSDT-5m-2025-01.csv', '1735689600000000,100,105,99,102,8,1735689899999999,0,0,0,0,0\n')
        req=MarketRequest('crypto','BTCUSDT','5m',date(2025,1,1),date(2025,1,1))
        with patch('data_sources.request_bytes',return_value=data.getvalue()):
            result=BinanceArchive().fetch(req)
        self.assertEqual(result[0]['date'],'2025-01-01T00:00:00+00:00')
        self.assertEqual(result[0]['close'],102)

    def test_cache_and_offline_reload(self):
        req=MarketRequest('crypto','BTCUSDT','5m',date(2025,1,1),date(2025,1,2))
        with tempfile.TemporaryDirectory() as folder:
            svc=HistoricalDataService(Path(folder)/'cache.sqlite')
            one={'date':'2025-01-01T00:00:00+00:00','open':100.,'high':105.,'low':99.,'close':102.,'volume':8.}
            with patch.object(svc.providers['crypto'],'fetch',return_value=[one]) as fetch:
                x,status=svc.get(req)
                y,status2=svc.get(req,offline=True)
                self.assertEqual(status2,'Cached (SQLite)')
                self.assertEqual(x,y)
                fetch.assert_called_once()

    def test_alpaca_pagination(self):
        req=MarketRequest('stocks','AAPL','1m',date(2025,1,1),date(2025,1,2))
        pages=[b'{"bars":[{"t":"2025-01-01T14:30:00Z","o":10,"h":11,"l":9,"c":10.5,"v":100}],"next_page_token":"next"}',
               b'{"bars":[{"t":"2025-01-01T14:31:00Z","o":10.5,"h":11,"l":10,"c":10.8,"v":90}],"next_page_token":null}']
        with patch.dict('os.environ',{'ALPACA_API_KEY_ID':'test','ALPACA_API_SECRET_KEY':'test'}):
            with patch('data_sources.request_bytes',side_effect=pages) as mock:
                result=AlpacaIEX().fetch(req)
        self.assertEqual(len(result),2)
        self.assertIn('feed=iex', mock.call_args_list[0].args[0])

    def test_bad_symbol(self):
        with self.assertRaises(ValueError):
            MarketRequest('crypto','../../path','1m',date(2025,1,1),date(2025,1,2))

if __name__=='__main__': unittest.main()
