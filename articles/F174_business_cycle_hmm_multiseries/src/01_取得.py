"""01 データの取得

新しくは取らず、F13・F18 で取得した景気動向指数の表（2026年10月26日取得）を使う。
- 内閣府 経済社会総合研究所「景気動向指数」https://www.esri.cao.go.jp/jp/stat/di/
  2026年10月公表分の *ci.xlsx（CI）、*ci1.xlsx（先行系列）、*ci2.xlsx（一致系列）を
  F13 でブラウザから読み込み JSON にしたもの（articles/F18_nowcast_dfm/data/raw/f13_ci.json）
- 景気基準日付（同）https://www.esri.cao.go.jp/jp/stat/di/hiduke.html → cycle_dates.csv（F18 と同じ）

同梱の data/raw/ci_series_monthly.csv を使う。取り直すときは --download を付けると、
GitHub 上の F18 のファイルから作り直す。
"""
import sys, io, json, urllib.request
import pandas as pd
from common import RAW

BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/F18_nowcast_dfm/data/raw/"

def table(d, key, names):
    rows = [r for r in d[key] if r and isinstance(r[0], str) and r[0].isdigit() and len(r[0]) == 10]
    out = []
    for r in rows:
        vals = [(r[i] if i < len(r) else None) for i in range(3, 3 + len(names))]
        out.append([f"{int(r[1]):04d}-{int(r[2]):02d}-01"] + vals)
    df = pd.DataFrame(out, columns=["month"] + names)
    return df.set_index("month").apply(pd.to_numeric, errors="coerce")

if __name__ == "__main__":
    if "--download" not in sys.argv:
        print("data/raw/ の同梱データを使います（取り直すときは --download）")
        sys.exit(0)
    RAW.mkdir(parents=True, exist_ok=True)
    d = json.loads(urllib.request.urlopen(BASE + "f13_ci.json", timeout=120).read())
    c = table(d, "1026ci2.xlsx", [f"C{i}" for i in range(1, 11)])
    l = table(d, "1026ci1.xlsx", ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L10A", "L10B", "L11"])
    ci = table(d, "1026ci.xlsx", ["ci_lead", "ci_coin", "ci_lag"])
    keep_l = ["L1", "L2", "L3", "L4", "L5", "L6", "L9"]
    out = c.join(l[keep_l], how="outer").join(ci[["ci_lead", "ci_coin"]], how="left")
    out.to_csv(RAW / "ci_series_monthly.csv")
    (RAW / "cycle_dates.csv").write_bytes(urllib.request.urlopen(BASE + "cycle_dates.csv", timeout=60).read())
    print("saved", out.shape)
