"""共通：住宅市場動向調査（分譲住宅）の平均世帯年収と住宅購入資金を読む"""
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
SOURCE = "出典：国土交通省「住宅市場動向調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00600630）をもとに作成者が加工して作成"



COLS = {"all": "分譲住宅計", "shutoken": "首都圏", "detached": "分譲戸建て", "condo": "分譲マンション", "condo_first": "マンション一次取得", "condo_second": "マンション二次取得"}


def load():
    d = pd.read_csv(DATA / "bunjo_income_price.csv")
    inc = d[d.item == "income"].set_index("survey_fy").drop(columns="item")
    pr = d[d.item == "price"].set_index("survey_fy").drop(columns="item")
    return inc, pr, pr / inc


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
