"""共通の設定（パス・フォント）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (RES, FIG):
    p.mkdir(exist_ok=True)


def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["svg.hashsalt"] = "fixed"
