"""F110 データの取得：新しくは取らず、F03（地価公示の特徴量）と F67（東京の日次電力需要と気温）で作った表をそのまま使う
同じリポジトリの articles/ から data/ にコピーする"""
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]; A = ROOT.parent
(ROOT / "data").mkdir(exist_ok=True)
shutil.copy(A / "F03_land_price_ml/data/features.csv", ROOT / "data/land_features.csv")
shutil.copy(A / "F67_temp_power_gam/data/daily_tokyo.csv", ROOT / "data/power_daily_tokyo.csv")
print("copied")
