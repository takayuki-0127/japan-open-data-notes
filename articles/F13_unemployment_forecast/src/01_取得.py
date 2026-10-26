"""01 データの取得

- 労働力調査 長期時系列 表1 a-1（季節調整値・原数値）  e-Stat statInfId=000031831358
- 一般職業紹介状況 第3表 有効求人倍率（季節調整値を含む）  e-Stat（毎月 statInfId が変わる。
  一覧ページで表名「有効求人倍率（パートタイムを含む一般）」の最新を探す。F12 と同じファイル）
- 景気動向指数（内閣府 経済社会総合研究所）https://www.esri.cao.go.jp/jp/stat/di/di.html
  長期系列 *ci.xlsx（CI 先行・一致）、一致系列 *ci2.xlsx（鉱工業生産指数・労働投入量指数・有効求人倍率）、
  先行系列 *ci1.xlsx（新規求人数 など）。ファイル名の先頭（例 1026）は公表日で毎月変わる。

このリポジトリの data/raw/ には 2026-10-26 に取得したものを置いている（lfs.xlsx, jobs.xlsx, f13_ci.json）。
f13_ci.json は 3 つの景気動向指数の Excel をブラウザ内（SheetJS）で読んで、行ごとの配列にしたもの。
コンテナから e-Stat・内閣府に直接つながらない環境のため、ブラウザで取得したものを置いている。
直接つながる環境では下の fetch() で取り直せる。
"""
import sys, urllib.request
from common import RAW

ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
URLS = {
    "lfs.xlsx": ESTAT.format("000031831358"),
    # 有効求人倍率の statInfId は毎月変わるので、実行時に最新のものに置き換える
    "jobs.xlsx": ESTAT.format("000040505314"),
}
ESRI = "https://www.esri.cao.go.jp/jp/stat/di/{}"


def fetch(name, url):
    with urllib.request.urlopen(url, timeout=60) as r:
        (RAW / name).write_bytes(r.read())
    print("saved", name)


if __name__ == "__main__":
    if "--download" not in sys.argv:
        print("data/raw/ の同梱データを使います（取り直すときは --download）")
        sys.exit(0)
    RAW.mkdir(parents=True, exist_ok=True)
    for n, u in URLS.items():
        fetch(n, u)
    prefix = sys.argv[sys.argv.index("--download") + 1] if len(sys.argv) > sys.argv.index("--download") + 1 else "1026"
    for s in ("ci", "ci1", "ci2"):
        fetch(f"{prefix}{s}.xlsx", ESRI.format(f"{prefix}{s}.xlsx"))
    print("景気動向指数は xlsx のまま保存。02_整形.py は f13_ci.json か xlsx のどちらでも読める")
