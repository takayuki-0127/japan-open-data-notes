"""総務省「我が国のインターネットにおけるトラヒックの集計・試算」の集計値（情報通信統計データベース gt010108.xlsx）を取得する。
2026年5月分（令和8年8月31日公表）までを含む版を data/raw/gt010108.xlsx に置いてある。
環境によっては総務省のサイトに直接つながらないため、その場合はブラウザで URL を開いて保存し、data/raw/ に置く。"""
import sys, urllib.request
from common import XLSX, URL
if XLSX.exists() and "--force" not in sys.argv:
    print("exists", XLSX); sys.exit()
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
XLSX.write_bytes(urllib.request.urlopen(req, timeout=60).read()); print("saved", XLSX)
