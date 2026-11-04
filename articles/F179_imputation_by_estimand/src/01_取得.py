"""01 取得：統計センター SSDSE-A-2026（市区町村）を data/raw/ に置き、中身を確かめる。

SSDSE は https://www.nstac.go.jp/use/literacy/ssdse/ から CSV を手で落とす。
このフォルダには SSDSE-A-2026.csv を同梱している（Shift_JIS、F166・F170 と同じファイル）。
ここではファイルがあることと、行数・MD5 を確かめるだけ。
"""
import hashlib
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
p = RAW / "SSDSE-A-2026.csv"
if not p.exists():
    raise SystemExit(f"{p} がありません。SSDSE のページから落として置いてください。")
h = hashlib.md5(p.read_bytes()).hexdigest()
n = sum(1 for _ in open(p, encoding="cp932"))
print(p.name, n, "行", "MD5一致" if h == "3343e61712d4a0a8e5b15e91adce9642" else f"MD5が違う（{h}）")
