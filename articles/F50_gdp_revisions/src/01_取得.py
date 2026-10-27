"""データの取得について

内閣府のサイトはこのコンテナから直接読めないため、ブラウザで src/01_取得.js を実行して
data/raw/f50_qe_releases.json（と f50_qe_extra.json）を作った。景気基準日付（data/raw/cycle_dates.csv）は
F18 と同じ（内閣府「景気基準日付」https://www.esri.cao.go.jp/jp/stat/di/hiduke.html）。

このスクリプトは、取得済みのファイルがそろっているかだけを確かめる。
"""
import json
from common import RAW

for f in ["f50_qe_releases.json", "f50_qe_extra.json", "cycle_dates.csv"]:
    p = RAW / f
    print(f, "OK" if p.exists() else "ない", p.stat().st_size if p.exists() else "")
d = json.load(open(RAW / "f50_qe_releases.json", encoding="utf-8"))
print("公表回", len(d), "（CSV が取れた回）", sum(1 for r in d if r.get("jk")))
