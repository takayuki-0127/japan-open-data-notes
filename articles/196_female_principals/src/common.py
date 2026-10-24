"""共通：学校基本調査（公立小・中学校）の都道府県別・職名別・男女別の本務教員数を読む"""
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
SOURCE = "出典：文部科学省「学校基本調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400001）をもとに作成者が加工して作成"


def load():
    d = pd.read_csv(DATA / "principals_by_pref.csv")
    d["head_share"] = d.head_f / (d.head_m + d.head_f)
    d["vk_share"] = (d.vice_f + d.kyoto_f) / (d.vice_m + d.vice_f + d.kyoto_m + d.kyoto_f)
    d["tf_share"] = d.tot_f / (d.tot_m + d.tot_f)
    return d


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
