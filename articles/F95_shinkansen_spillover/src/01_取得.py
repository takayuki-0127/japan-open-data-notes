"""01 取得：F29（＝F04）の宿泊旅行統計の縦長の表と、F33 の県の隣接・県庁所在地の座標を使う。
- 観光庁「宿泊旅行統計調査」推移表（都道府県×月の延べ宿泊者数、2011年1月〜2025年12月の確定値）
  元の Excel：https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html
- 県の隣接（境界を共有するか）と県庁所在地の座標：F33 で国土数値情報（行政区域）から作ったもの
data/raw/ に無いときは GitHub から取り直す。"""
import urllib.request
from common import RAW
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FILES = {"lodging_pref_monthly_2011_2025.csv": "F04_goto_causalimpact/data/raw/lodging_pref_monthly_2011_2025.csv",
         "pairs.csv": "F33_migration_gravity/data/pairs.csv",
         "pref_points.csv": "F33_migration_gravity/data/pref_points.csv"}
if __name__ == "__main__":
    for name, path in FILES.items():
        out = RAW / name
        if not out.exists():
            urllib.request.urlretrieve(BASE + path, out)
        print("ok", out)
