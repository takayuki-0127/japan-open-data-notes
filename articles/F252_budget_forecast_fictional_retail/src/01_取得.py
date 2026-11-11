"""01 取得：前の回の成果物を取ってくる（公開データの新しい取得はなし）。

- F247 の mart（コミット e8ba90f）：data/mart/ に写す。レポートの数字はすべてここから計算する。
- F246 の合成のコード（src/02_整形.py）と、その入力（data/raw/、コミット 3006b82）：data/f246/ に写す。
  乱数の種だけを変えたデータを作り直して「偶然の幅」を測るのに使う（03_分析.py）。
- 商業動態統計（スーパー、月次）は F246 の data/raw/sales_monthly_6types.csv に入っているものを使う（業界の動きの参考）。
- data/mart/ と data/f246/ はリポジトリに入れない（元の回にあるので）。このスクリプトで取り直せる。
"""
import hashlib, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
GH = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/"
F247 = GH + "e8ba90fcb3b50f8875ed90a0120fbd1015537599/articles/F247_data_mart_fictional_retail/mart/"
F246 = GH + "3006b8208d/articles/F246_kpi_definitions_fictional_retail/"
JOBS = [(F247 + f, ROOT / "data" / "mart" / f) for f in
        ["dim_store.csv", "dim_category.csv", "dim_date.csv", "store_month.csv",
         "fact_store_day.csv.gz", "fact_store_day_category.csv.gz"]]
JOBS += [(F246 + "src/02_整形.py", ROOT / "data" / "f246" / "src" / "02_整形.py")]
JOBS += [(F246 + "data/raw/" + f, ROOT / "data" / "f246" / "data" / "raw" / f) for f in
         ["calendar_daily.csv.gz", "sales_monthly_6types.csv", "kakei_items.csv"]]

for url, p in JOBS:
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        urllib.request.urlretrieve(urllib.parse.quote(url, safe=":/"), p)
    print(p.relative_to(ROOT), p.stat().st_size, hashlib.md5(p.read_bytes()).hexdigest())
