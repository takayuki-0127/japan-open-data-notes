"""共通：農林水産省「牛乳乳製品統計調査」の累年統計（全国・年計）を読む"""
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
SOURCE = "出典：農林水産省「牛乳乳製品統計調査」累年統計（e-Stat）をもとに作成者が加工して作成"



LABEL = {"gyunyu": "牛乳", "kakounyu_seibun": "加工乳・成分調整牛乳", "nyuinryo": "乳飲料",
         "hakkonyu": "はっ酵乳（ヨーグルト等）", "nyusankin": "乳酸菌飲料"}


def load():
    """1985〜2024年の年計。牛乳等5品目はkl、生乳の処理量（用途別）と生乳生産量はt"""
    return pd.read_csv(DATA / "milk_annual_1985_2024.csv")


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
