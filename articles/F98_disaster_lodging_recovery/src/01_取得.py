"""01 取得：観光庁「宿泊旅行統計調査」推移表（都道府県×月の延べ宿泊者数、2011年1月〜2025年12月）を F04 で縦長にしたものと、
F33 で国土数値情報（行政区域）から作った県の隣り合いの表を使う。
元の Excel：https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html の「推移表」。政府のサイトはスクリプトからの取得が不安定なため、
F04 でブラウザから読んだものを GitHub に置き、ここから取り直す。"""
import urllib.request
from common import RAW
B = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {"lodging_pref_monthly_2011_2025.csv": "F04_goto_causalimpact/data/raw/lodging_pref_monthly_2011_2025.csv",
         "pairs.csv": "F33_migration_gravity/data/pairs.csv"}
if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for f, p in FILES.items():
        if not (RAW / f).exists():
            urllib.request.urlretrieve(B + p, RAW / f)
        print("ok", f)
