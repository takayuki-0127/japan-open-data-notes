"""01 データの取得

新しくは取らず、F13・F18 で取得したデータを使う。
- 景気動向指数（内閣府 経済社会総合研究所、2026年10月公表、1985年1月〜2026年8月）
  https://www.esri.cao.go.jp/jp/stat/di/di.html
  長期系列 *ci.xlsx の CI一致指数、一致系列 *ci2.xlsx の鉱工業生産指数（1975年1月〜）
  → F13 の 02_整形.py で月次表にしたもの（articles/F13_unemployment_forecast/data/ の f13_monthly.csv）
    から3列を抜き出して data/raw/ci_iip_monthly.csv に置いている
- 景気基準日付（内閣府 経済社会総合研究所）https://www.esri.cao.go.jp/jp/stat/di/hiduke.html
  第8循環の谷（1975年3月）〜第16循環の谷（2020年5月）→ data/raw/cycle_dates.csv（F18 と同じ）

取り直すときは --download を付けると、GitHub 上の F18 のファイルから作り直す。
"""
import sys, io, urllib.request
import pandas as pd
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F18_nowcast_dfm/data/raw/"

if __name__ == "__main__":
    if "--download" not in sys.argv:
        print("data/raw/ の同梱データを使います（取り直すときは --download）")
        sys.exit(0)
    RAW.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(io.BytesIO(urllib.request.urlopen(BASE + "f13_monthly.csv", timeout=60).read()))
    m[["month", "ci_coin", "ci_lead", "iip"]].to_csv(RAW / "ci_iip_monthly.csv", index=False)
    (RAW / "cycle_dates.csv").write_bytes(urllib.request.urlopen(BASE + "cycle_dates.csv", timeout=60).read())
    print("saved")
