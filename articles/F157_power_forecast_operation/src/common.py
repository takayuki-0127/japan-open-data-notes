"""共通の設定（パス・フォント・乱数の種・モデルの設定）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
# 電力と気象のデータは F22 のものをそのまま使う（同じリポジトリの articles/F22_power_demand_forecast/data）
F22DATA = ROOT.parent / "F22_power_demand_forecast" / "data"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
CACHE = ROOT.parent.parent / "f157_cache"   # 途中結果（リポジトリには入れない）
SEED = 42

# F22 と同じ LightGBM の木の数を900→300、学習率を0.04→0.1にした「軽い版」を基本にする（運用で数十〜数百回学習し直すため）。
# 固定のモデルだけ、F22 と同じ設定でも学習して差を確かめる
LGB_FULL = dict(n_estimators=900, learning_rate=0.04, num_leaves=63, min_child_samples=40,
                subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                random_state=SEED, verbose=-1, n_jobs=2)
LGB_LIGHT = dict(LGB_FULL, n_estimators=300, learning_rate=0.1)

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110
