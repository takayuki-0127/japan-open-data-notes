"""共通：気象庁の都道府県庁所在地などの年間日照時間（1987〜2025年）を読む"""
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
SOURCE = "出典：気象庁「過去の気象データ」（https://www.data.jma.go.jp/stats/etrn/）をもとに作成者が加工して作成"


Y0, Y1 = 1987, 2025  # 1986年に日照計が変わったため1987年から使う


def load():
    d = pd.read_csv(DATA / "sunshine_annual.csv")
    d.loc[d.flag == "]", "sunshine_h"] = np.nan  # 資料不足値は使わない
    d = d[(d.year >= Y0) & (d.year <= Y1)]
    w = d.pivot(index="year", columns="pref", values="sunshine_h")
    w = w[d.pref.drop_duplicates()]
    return d, w


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
