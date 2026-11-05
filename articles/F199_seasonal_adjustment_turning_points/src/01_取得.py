"""F63 のフォルダ（コミット c3ad8a7 に固定）から、季節調整前の原数値と景気基準日付を取得する。"""
import pathlib, urllib.request
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/c3ad8a7/articles/F63_yoy_vs_mom/data/raw/"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)
for name in ["f42_series.csv", "cycle_dates.csv", "f35_ci_iip_monthly.csv"]:
    with urllib.request.urlopen(BASE + name, timeout=60) as r:
        (OUT / name).write_bytes(r.read())
    print("ok", name)
