"""01 取得：統計センター SSDSE-A（市区町村）を data/raw/ に置き、中身を確かめる。

SSDSE は https://www.nstac.go.jp/use/literacy/ssdse/ から CSV を手で落とす（F166 と同じファイル）。
このフォルダには SSDSE-A-2026.csv と SSDSE-A-2021.csv を同梱している（Shift_JIS）。
ここではファイルがあることと、行数・MD5 を確かめるだけ。
"""
import hashlib
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
EXPECT = {
    "SSDSE-A-2026.csv": "3343e61712d4a0a8e5b15e91adce9642",
    "SSDSE-A-2021.csv": "f4f35b4bafedc9c81be1f201e4374298",
}
for name, md5 in EXPECT.items():
    p = RAW / name
    if not p.exists():
        raise SystemExit(f"{p} がありません。SSDSE のページから落として置いてください。")
    h = hashlib.md5(p.read_bytes()).hexdigest()
    n = sum(1 for _ in open(p, encoding="cp932"))
    print(name, n, "行", "MD5一致" if h == md5 else f"MD5が違う（{h}）")
