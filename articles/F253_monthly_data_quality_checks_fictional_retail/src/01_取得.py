"""01 取得：前の回の成果物を data/ に写す（公開データの新しい取得はなし）。

- F247 の mart（コミット e8ba90f）：店×日・店×日×部門・店・日付 → data/in/
  毎月のチェックは「確定した mart の、その月の分」にかける。前の月までの mart は「その店のふだんの値」を作るのに使う。
- F246 の合成のコード（src/02_整形.py）と、その入力（data/raw/、コミット 3006b82）→ data/f246/
  乱数の種だけを変えた20通りのデータを作り直し、「汚れのないデータで、チェックがどれだけ誤って鳴るか」を測る（03_分析.py）。
- リポジトリの隣のフォルダ（../F246_*, ../F247_*）があればそこから写し、なければ GitHub から取る。
- data/in/ と data/f246/ はリポジトリに入れない（元の回にあるので）。このスクリプトで取り直せる。
会社・数字はすべて架空（合成データ）。
"""
import hashlib, pathlib, shutil, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
ART = ROOT.parent
GH = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/"
JOBS = []
for f in ["dim_store.csv", "dim_date.csv", "dim_category.csv", "fact_store_day.csv.gz", "fact_store_day_category.csv.gz"]:
    JOBS.append(("e8ba90fcb3b50f8875ed90a0120fbd1015537599", "F247_data_mart_fictional_retail", "mart/" + f, ROOT / "data" / "in" / f))
JOBS.append(("3006b8208d", "F246_kpi_definitions_fictional_retail", "src/02_整形.py", ROOT / "data" / "f246" / "src" / "02_整形.py"))
for f in ["calendar_daily.csv.gz", "sales_monthly_6types.csv", "kakei_items.csv"]:
    JOBS.append(("3006b8208d", "F246_kpi_definitions_fictional_retail", "data/raw/" + f, ROOT / "data" / "f246" / "data" / "raw" / f))

for commit, folder, sub, dst in JOBS:
    dst.parent.mkdir(parents=True, exist_ok=True)
    local = ART / folder / sub
    if local.exists():
        shutil.copyfile(local, dst)
    elif not dst.exists():
        urllib.request.urlretrieve(urllib.parse.quote(f"{GH}{commit}/articles/{folder}/{sub}", safe=":/"), dst)
    print(dst.relative_to(ROOT), dst.stat().st_size, hashlib.md5(dst.read_bytes()).hexdigest()[:10])
