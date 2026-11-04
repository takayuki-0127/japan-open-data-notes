"""01 取得：統計センター SSDSE-A（市区町村）2026年版と2021年版を data/raw/ に置く。

SSDSE は https://www.nstac.go.jp/use/literacy/ssdse/ から CSV を手で落とす（Shift_JIS）。
元ファイルは大きいのでリポジトリには入れていない。必要な列だけを 02 で data/frame.csv にしてあり、
data/frame.csv があれば 03 以降はそのまま動く。
"""
import hashlib
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EXPECT = {
    "SSDSE-A-2026.csv": "3343e61712d4a0a8e5b15e91adce9642",
    "SSDSE-A-2021.csv": "f4f35b4bafedc9c81be1f201e4374298",
}
for name, md5 in EXPECT.items():
    p = RAW / name
    if not p.exists():
        print(f"{p} がありません（data/frame.csv があれば 03 以降は動きます）")
        continue
    h = hashlib.md5(p.read_bytes()).hexdigest()
    print(name, "MD5一致" if h == md5 else f"MD5が違う（{h}）")
