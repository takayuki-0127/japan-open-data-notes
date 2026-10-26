"""共通の設定（パス・フォント・乱数の種）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

COLORS = {"前月の値（ナイーブ）": "#9aa0a6", "AR（失業率だけ）": "#5f6368",
          "SARIMAX": "#1a73e8", "ElasticNet": "#e37400", "LightGBM": "#188038", "平均（3モデル）": "#a142f4"}
