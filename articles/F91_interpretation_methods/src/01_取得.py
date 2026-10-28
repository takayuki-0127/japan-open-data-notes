"""01 取得：F03（地価）と F22（電力需要）の整形済みデータを、このリポジトリの GitHub から取ってくる"""
import urllib.request
from common import RAW
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {"F03_features.csv": "F03_land_price_ml/data/features.csv",
         "F22_hourly_tokyo.csv": "F22_power_demand_forecast/data/hourly_tokyo.csv"}
for name, path in FILES.items():
    dst = RAW / name
    if not dst.exists():
        urllib.request.urlretrieve(BASE + path, dst)
    print(name, dst.stat().st_size)
