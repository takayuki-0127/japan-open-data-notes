"""01 取得：F67 で作った日ごとの表（東京・関西）を GitHub から取得する（data にあれば省略）

元は F22 で整えた1時間ごとの需要（東京電力パワーグリッド・関西電力送配電「エリア需給実績」）と
気象庁「過去の気象データ」の日平均気温。
"""
import urllib.request
from common import DATA

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F67_temp_power_gam/data/"
for name in ["daily_tokyo.csv", "daily_kansai.csv"]:
    p = DATA / name
    if p.exists():
        print("あり", name)
        continue
    urllib.request.urlretrieve(BASE + name, p)
    print("取得", name, p.stat().st_size)
