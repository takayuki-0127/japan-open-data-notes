"""F01・F14 のフォルダから、このシミュレーションの土台にする実データを取ってくる（新しい公的データの取得はしない）"""
import urllib.request
from common import RAW
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
PIN = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/c56ebc67126a738058bdae7c172e7b29473f9286/articles/"  # F14 の記事フォルダは削除したので、削除前の版（コミット c56ebc6）から取る
FILES = {"f01_panel.csv": BASE + "F01_minimum_wage_did/data/panel.csv",
         "f14_analysis.csv": PIN + "F14_compact_city_psm_did/data/analysis.csv"}
for name, path in FILES.items():
    out = RAW / name
    if out.exists():
        print("あり:", out.name); continue
    urllib.request.urlretrieve(path, out)
    print("取得:", out.name)
