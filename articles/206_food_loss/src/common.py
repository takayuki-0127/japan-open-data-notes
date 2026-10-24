"""共通：食品ロス量の推計値（環境省・農林水産省、2012〜2024年度）を読む"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：環境省「我が国の食品ロスの発生量の推計値（令和6年度）」（農林水産省・環境省推計）をもとに作成者が加工して作成"



COMP = {"b_manufacturing": "食品製造業", "b_wholesale": "食品卸売業", "b_retail": "食品小売業", "b_restaurant": "外食産業",
        "h_direct": "直接廃棄", "h_overpeel": "過剰除去", "h_leftover": "食べ残し"}


def load():
    """年度別の食品ロス量（万トン）。事業系は業種別、家庭系は発生要因別（いずれも公表資料の図の値）"""
    d = pd.read_csv(DATA / "food_loss_2012_2024.csv").set_index("fy")
    g = pd.read_csv(DATA / "targets.csv").set_index("kind")
    return d, g


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
