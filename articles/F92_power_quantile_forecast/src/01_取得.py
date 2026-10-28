"""01 取得：F67（元は F22）で作った日別データ（東京・関西のエリア需要と気象庁の気温）を取ってくる

元のデータ：東京電力パワーグリッド・関西電力送配電「エリア需給実績」、気象庁「過去の気象データ」（東京・大阪の日別値）。
1時間ごとの需要から、日ごとの最大（ピーク、MW）を作ったもの。
"""
import urllib.request
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F67_temp_power_gam/data/"
RAW.mkdir(parents=True, exist_ok=True)
for name in ["daily_tokyo.csv", "daily_kansai.csv"]:
    urllib.request.urlretrieve(BASE + name, RAW / name)
    print("saved", name)
