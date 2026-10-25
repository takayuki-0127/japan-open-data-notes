"""データの取得。
1) SSDSE-A（統計センター「教育用標準データセット」市区町村、2026年版）
   https://www.nstac.go.jp/use/literacy/ssdse/ から SSDSE-A-2026.csv をダウンロードし data/raw/ に置く（手作業）
2) 市区町村の境界（国土数値情報 行政区域 2021 をもとにした簡略版 TopoJSON、smartnews-smri/japan-topography、CC BY 4.0）
"""
import urllib.request
from common import RAW

RAW.mkdir(parents=True, exist_ok=True)
url = ("https://raw.githubusercontent.com/smartnews-smri/japan-topography/main/"
       "data/municipality/topojson/s0010/N03-21_210101.json")
dst = RAW / "N03-21_210101.json"
if not dst.exists():
    urllib.request.urlretrieve(url, dst)
print("ok", dst.exists(), (RAW / "SSDSE-A-2026.csv").exists())
