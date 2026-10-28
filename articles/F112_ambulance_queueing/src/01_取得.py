"""F112 01 取得：総務省消防庁『令和7年版 救急救助の現況』Ⅰ救急編（PDF）を取得し、テキストにする

https://www.fdma.go.jp/publication/rescue/post-7.html の「Ⅰ 救急編」
（この記事では、PDF をブラウザで保存して data/raw/ に置いた。2026年10月29日取得）
テキスト化には poppler の pdftotext を使う（-layout で表の列の並びを保つ）。
"""
import subprocess, urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.fdma.go.jp/publication/rescue/items/kkkg_r07_01_kyukyu.pdf"
pdf = RAW / "kkkg_r07_01_kyukyu.pdf"
if not pdf.exists():
    urllib.request.urlretrieve(URL, pdf)
subprocess.run(["pdftotext", "-layout", str(pdf), str(RAW / "kkkg_r07_01_kyukyu.txt")], check=True)
print(pdf.stat().st_size, "bytes")
