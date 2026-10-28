"""F109 データの取得：新しい取得はせず、F03 で作った特徴量（地価公示2026年・25,565地点）をそのまま使う。
F03 の data/features.csv（作り方は F03 の src/01_features.py）を data/ にコピーする。"""
import shutil
from pathlib import Path
from common import DATA
src = Path(__file__).resolve().parents[2] / "F03_land_price_ml" / "data" / "features.csv"
if src.exists():
    shutil.copy(src, DATA / "features.csv")
    print("copied", src)
else:
    print("F03 の features.csv が見つかりません。japan-open-data-notes/articles/F03_land_price_ml/data/features.csv を data/ に置いてください")
