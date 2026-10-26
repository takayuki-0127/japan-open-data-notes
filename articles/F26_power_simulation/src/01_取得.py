"""F01・F14 のフォルダから、このシミュレーションの土台にする実データを取ってくる（新しい公的データの取得はしない）"""
import urllib.request
from common import RAW
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {"f01_panel.csv": "F01_minimum_wage_did/data/panel.csv",
         "f14_analysis.csv": "F14_compact_city_psm_did/data/analysis.csv"}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print("あり:", out.name); continue
    urllib.request.urlretrieve(BASE + path, out)
    print("取得:", out.name)
