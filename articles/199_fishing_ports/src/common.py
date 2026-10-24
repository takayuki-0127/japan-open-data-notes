"""共通：水産物流通調査の漁港別上場水揚量・卸売価格を読む"""
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
SOURCE = "出典：農林水産省「水産物流通調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00502005）をもとに作成者が加工して作成"




def load():
    d = pd.read_csv(DATA / "port_landings.csv", na_values="-")
    d["label"] = d.port.where(~d.duplicated(["year", "port"], keep=False), d.port + "（" + d.pref + "）")
    d["value_oku"] = d.qty_t * d.price_yen_kg * 1000 / 1e8  # 億円（数量×平均価格）
    return d


def lorenz(x):
    x = np.sort(np.asarray(x, float))
    c = np.r_[0, np.cumsum(x)] / x.sum()
    return np.linspace(0, 1, len(c)), c


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
