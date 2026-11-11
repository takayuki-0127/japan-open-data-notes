"""01 取得：F246 で作った架空の会社「サンプルマート（架空）」の“正しい”データを data/truth/ に写す。

- この回では公開データを新しく取得しない。F246 のフォルダ（コミット 3006b8208d 時点）の data/ をそのまま使う。
- data/truth/ はリポジトリには入れない（F246 にあるので）。このスクリプトで取り直せる。
- truth は「本当はこうだった」という答え。02_整形.py がこれをもとに、現場から届く“汚れた”ファイル（data/raw_synth/）を合成する。
"""
import pathlib, urllib.request, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "truth"; OUT.mkdir(parents=True, exist_ok=True)
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/3006b8208d/articles/F246_kpi_definitions_fictional_retail/data/"
FILES = ["dim_store.csv", "dim_category.csv", "dim_date.csv", "fact_store_day.csv.gz",
         "fact_store_day_category.csv.gz", "fact_member_month.csv", "fact_ec_day.csv"]

for f in FILES:
    p = OUT / f
    if not p.exists():
        urllib.request.urlretrieve(BASE + f, p)
    print(f, p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest())
