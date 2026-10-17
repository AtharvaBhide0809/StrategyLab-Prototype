"""Create deterministic illustrative data; NEVER treat this as market history."""
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

def create(path):
    r=random.Random(72)
    day=date(2022,1,3)
    price=100.0
    with open(path,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['Date','Open','High','Low','Close','Volume'])
        i=0
        while i<950:
            if day.weekday()<5:
                opening=price*(1+r.gauss(0,.004))
                closing=max(.1,opening*(1+0.001*math.sin(i/23)+r.gauss(.0002,.014)))
                high=max(opening,closing)*(1+abs(r.gauss(0,.006)))
                low=min(opening,closing)*(1-abs(r.gauss(0,.006)))
                w.writerow([day.isoformat(),*[round(x,4) for x in (opening,high,low,closing)],r.randint(120000,800000)])
                price=closing; i+=1
            day+=timedelta(days=1)
if __name__=='__main__': create(Path(__file__).with_name('sample_prices.csv'))
