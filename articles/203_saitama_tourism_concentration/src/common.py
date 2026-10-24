"""共通：埼玉県「観光入込客統計」の市町村別観光入込客数（2011〜2025年）を読む"""
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
SOURCE = "出典：埼玉県「観光入込客統計調査結果」（県内市町村観光入込客数）をもとに作成者が加工して作成"


def load():
    """63市町村×15年。空欄（'-'）はNaNのまま、合計は県の表の値。
    白岡市の2011・2012年は合計欄がふじみ野市と同じ値になっているため、観光地点＋イベントに置き換える。"""
    d = pd.read_csv(DATA / "saitama_muni_visitors_2011_2025.csv")
    m = (d.muni == "白岡市") & d.year.isin([2011, 2012])
    d.loc[m, "total"] = d.loc[m, "spot"] + d.loc[m, "event"]
    d["total"] = d.total.fillna(0)
    return d


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return (2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum())


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
