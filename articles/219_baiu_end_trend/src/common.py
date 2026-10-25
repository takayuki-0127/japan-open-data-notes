"""共通：気象庁「過去の梅雨入りと梅雨明け」（確定値、1951〜2026年）を読む"""
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
SOURCE = "出典：気象庁「過去の梅雨入りと梅雨明け」（確定値）をもとに作成者が加工して作成"



REGIONS = ["沖縄", "奄美", "九州南部", "九州北部", "四国", "中国", "近畿", "東海", "関東甲信", "北陸", "東北南部", "東北北部"]


def load():
    """地方別・年別の梅雨入り・梅雨明け（確定値）。*_doy は1月1日を1とする日付（うるう年も平年の暦で数える）。特定しなかった年は空欄"""
    return pd.read_csv(DATA / "baiu_onset_end_1951_2026.csv")


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
