"""01 取得：F247 の mart（コミット e8ba90f）と、F246 の合成データを作るコード（コミット 3006b82）を data/in/ に写す。

- 会社・数字は架空（サンプルマート（架空）、合成データ）。公開データの新しい取得はない。
- 隣に F246・F247 のフォルダがあればそこから写し、なければ GitHub の raw から取る。
- data/in/ はリポジトリに入れていない（このスクリプトで作り直せる）。
"""
import pathlib, shutil, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "in"; IN.mkdir(parents=True, exist_ok=True)
RAW = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/{c}/articles/{a}/{p}"
F247 = ("F247_data_mart_fictional_retail", "e8ba90fcb3b50f8875ed90a0120fbd1015537599")
F246 = ("F246_kpi_definitions_fictional_retail", "3006b82")
FILES = [(F247, f"mart/{f}", f"mart/{f}") for f in [
    "dim_category.csv", "dim_date.csv", "dim_store.csv", "fact_member_month.csv",
    "fact_store_day.csv.gz", "fact_store_day_category.csv.gz", "store_month.csv"]]
FILES += [(F246, "src/02_整形.py", "f246/src/02_整形.py")]
FILES += [(F246, f"data/raw/{f}", f"f246/data/raw/{f}") for f in ["calendar_daily.csv.gz", "kakei_items.csv", "sales_monthly_6types.csv"]]


def main():
    for (art, commit), p, dst in FILES:
        out = IN / dst; out.parent.mkdir(parents=True, exist_ok=True)
        local = ROOT.parent / art / p
        if local.exists():
            shutil.copy(local, out)
        else:
            urllib.request.urlretrieve(RAW.format(c=commit, a=art, p=p), out)
        print(dst, out.stat().st_size)


if __name__ == "__main__":
    main()
