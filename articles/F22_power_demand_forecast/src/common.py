"""共通の設定（パス・フォント・乱数の種・色）"""
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

MODEL_NAMES = {
    "naive_week": "1週間前の同じ時刻",
    "naive_day": "前日の同じ時刻",
    "ridge": "線形回帰（Ridge）",
    "lgbm": "LightGBM",
}
COLORS = {"1週間前の同じ時刻": "#9aa0a6", "前日の同じ時刻": "#5f6368",
          "線形回帰（Ridge）": "#1a73e8", "LightGBM": "#188038"}
