"""01 取得：観光庁「宿泊旅行統計調査」推移表（都道府県×月の延べ宿泊者数、2011年1月〜2025年12月の確定値）。
元の Excel：https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html の「推移表」（旧1-2・旧2-2・旧3-2 シート）。
政府のサイトはスクリプトからの取得が不安定なため、F04 でブラウザから読んで縦長にした表を使う。"""
import urllib.request
from common import RAW
URL = ("https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/"
       "articles/F04_goto_causalimpact/data/raw/lodging_pref_monthly_2011_2025.csv")
if __name__ == "__main__":
    out = RAW / "lodging_pref_monthly_2011_2025.csv"
    if not out.exists():
        urllib.request.urlretrieve(URL, out)
    print("ok", out)
