"""01 取得：新しいデータは取らない。F18（articles/F18_nowcast_dfm）の整形済みデータと
DFM のナウキャスト結果を GitHub から取ってきて data/raw に置く。"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F18_nowcast_dfm/"
FILES = {
    "data/monthly_panel.csv": "monthly_panel.csv",
    "data/gdp_q.csv": "gdp_q.csv",
    "data/raw/cycle_dates.csv": "cycle_dates.csv",
    "results/nowcast_base.csv": "f18_nowcast_base.csv",
}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for src, dst in FILES.items():
        p = RAW / dst
        if p.exists():
            print("あり:", p.name)
            continue
        urllib.request.urlretrieve(BASE + src, p)
        print("取得:", p.name)
