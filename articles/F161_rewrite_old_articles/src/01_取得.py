"""01 取得：元記事 008・019・020 のフォルダにあるデータを、元の版（コミット 8090888 時点）からそのまま取ってくる。
data/raw/ に置いたファイルは、下の URL のファイルとバイト単位で同じ。"""
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/8090888/articles/"
FILES = {"data/raw/municipal_base.csv": "008_migration_income/data/municipal_base.csv",   # 019 も同じファイル
         "data/raw/municipal_extra.csv": "008_migration_income/data/municipal_extra.csv",
         "data/raw/lt01-a10.xlsx": "020_unemployment_sarima/data/raw/lt01-a10.xlsx",
         # 元記事の結果（比べるため）
         "data/original/008_a3_steps.csv": "008_migration_income/results/a3_steps.csv",
         "data/original/008_a3_full.csv": "008_migration_income/results/a3_full.csv",
         "data/original/019_c1_summary.csv": "019_municipal_clusters/results/c1_summary.csv",
         "data/original/019_c1_groups.csv": "019_municipal_clusters/results/c1_groups.csv",
         "data/original/019_c1_assignments.csv": "019_municipal_clusters/results/c1_assignments.csv",
         "data/original/020_t1_mae_by_h.csv": "020_unemployment_sarima/results/t1_mae_by_h.csv",
         "data/original/020_t1_summary.csv": "020_unemployment_sarima/results/t1_summary.csv"}
if __name__ == "__main__":
    for dst, src in FILES.items():
        p = ROOT / dst; p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            urllib.request.urlretrieve(BASE + src, p)
        print(dst, p.stat().st_size)
