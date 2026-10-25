"""共通：総務省統計局「小売物価統計調査（構造編）」の2024年 消費者物価地域差指数（10大費目）とウエイトを読む"""
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
SOURCE = "出典：総務省統計局「小売物価統計調査（構造編）」2024年 消費者物価地域差指数（e-Stat）をもとに作成者が加工して作成"



ITEMS = ["食料", "住居", "光熱・水道", "家具・家事用品", "被服及び履物", "保健医療", "交通・通信", "教育", "教養娯楽", "諸雑費"]


def load():
    """index：全国=100の地域差指数、weight：ウエイト。地域は全国・地方・都道府県・都市"""
    d = pd.read_csv(DATA / "cpi_regional_difference_2024.csv", dtype={"area_code": str}, na_values=["...", "…", "-"])
    I = d[d.table == "index"].set_index("area")
    W = d[d.table == "weight"].set_index("area")
    pref = I.index[I.area_code.str.endswith("000") & (I.area_code != "00000")]
    return I, W, list(pref)


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
