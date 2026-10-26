"""01 データの取得

使うデータ（data/raw/ に 2026-10-26 時点のものを同梱）
- 景気動向指数 個別系列（内閣府 経済社会総合研究所）https://www.esri.cao.go.jp/jp/stat/di/di.html
    一致系列 *ci2.xlsx・先行系列 *ci1.xlsx・CI *ci.xlsx（2026年10月公表、2026年8月分まで）
    → F13 と同じファイル。ブラウザ内（SheetJS）で読んで行ごとの配列にしたものが f13_ci.json
- 労働力調査（完全失業率・季節調整値）：F13 で作った月次表 f13_monthly.csv の u_sa 列
- 四半期別GDP速報（内閣府）2026年4-6月期 2次速報 実質季節調整系列
    https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-jk2622.csv
    → 国内総生産(支出側) の列だけを gdp_real_sa.csv に（1994年1-3月期〜2026年4-6月期、2020暦年連鎖価格、10億円）
- 景気基準日付（内閣府）https://www.esri.cao.go.jp/jp/stat/di/hiduke.html → cycle_dates.csv（第8〜16循環の山と谷）

コンテナから内閣府のサイトに直接つながらない環境だったので、ブラウザで取得したものを置いている。
直接つながる環境では --download で GDP の CSV を取り直せる（景気動向指数は F13 の 01_取得.py を参照）。
"""
import sys, csv, io, re, urllib.request
from common import RAW

GDP_URL = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-jk2622.csv"


def fetch_gdp(url=GDP_URL):
    with urllib.request.urlopen(url, timeout=60) as r:
        t = r.read().decode("shift_jis")
    out, y = [], None
    for line in t.splitlines():
        m = re.match(r'^(\d{4})?/?\s*(\d+)-\s*(\d+)\.,"?([-\d,\.]+)', line)
        if m:
            if m.group(1):
                y = int(m.group(1))
            q = int(m.group(3)) // 3
            out.append((f"{y}Q{q}", float(m.group(4).replace(",", ""))))
    with open(RAW / "gdp_real_sa.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["quarter", "gdp_real_sa"]); w.writerows(out)
    print("saved gdp_real_sa.csv", len(out))


if __name__ == "__main__":
    if "--download" in sys.argv:
        fetch_gdp()
    else:
        print("data/raw/ の同梱データを使います（GDP を取り直すときは --download）")
