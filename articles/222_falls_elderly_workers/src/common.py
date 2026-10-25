"""共通：労働災害統計（厚生労働省、労働者死傷病報告）を読む"""
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
SOURCE = "出典：厚生労働省「労働災害統計」（職場のあんぜんサイト）をもとに作成者が加工して作成"



def load():
    """事故の型別・年齢別の休業4日以上の死傷者数（全産業）と、2025年の年齢別事故の型別死傷度数率"""
    r = lambda f: pd.read_csv(DATA / f)
    return (r("injuries_by_accident_type_2009_2025.csv").set_index("year"), r("injuries_by_age_2009_2025.csv").set_index("year"),
            r("frequency_rate_by_age_type_2025.csv"))


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
