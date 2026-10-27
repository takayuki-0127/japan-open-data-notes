"""01 取得：F22 で整えた1時間ごとの需要と日ごとの気象の表を、GitHub から取ってくる。
元データ：東京電力パワーグリッド・関西電力送配電「エリア需給実績」、気象庁「過去の気象データ」（東京・大阪の日ごとの値）。
取得と整形の詳細は articles/F22_power_demand_forecast/src/01_取得.py・02_整形.py。"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F22_power_demand_forecast/data/"
import gzip, shutil
for name in ["hourly_tokyo.csv", "hourly_kansai.csv"]:
    p = RAW / (name + ".gz")  # このフォルダには gzip で圧縮して置いている
    if not p.exists():
        tmp = RAW / name
        urllib.request.urlretrieve(BASE + name, tmp)
        with open(tmp, "rb") as fi, gzip.open(p, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        tmp.unlink()
    print(p.name, p.stat().st_size)
