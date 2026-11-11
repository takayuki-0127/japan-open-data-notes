"""共通：パス・フォント・色・出典・データの読み込み"""
from pathlib import Path
import logging, warnings, calendar, datetime as dt
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "sans-serif"], "axes.unicode_minus": False,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, RAW, RES, FIG = ROOT / "data", ROOT / "data" / "raw", ROOT / "results", ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(exist_ok=True)
C = ["#2a78d6", "#eb6834", "#3aa07a", "#7a5bd6", "#c9a227", "#d64b8a", "#5b8c9e", "#8c6d4f", "#a3a29c"]
GRAY, INK = "#a3a29c", "#222222"
SOURCE = "出典：観光庁「宿泊旅行統計調査」（年の確定値）をもとに作成者が加工して作成"
SIZES = ["s0_9", "s10_29", "s30_99", "s100"]
SIZE_JA = {"s0_9": "0〜9人", "s10_29": "10〜29人", "s30_99": "30〜99人", "s100": "100人以上", "total": "全体"}


def table(n):
    """data/table<n>_national.csv（全国の行。month=0 は年計）"""
    return pd.read_csv(DATA / f"table{n}_national.csv")


def days(y, m):
    return calendar.monthrange(y, m)[1]


def note(ax, text=SOURCE, y=-0.02):
    ax.figure.text(0.01, y, text, fontsize=8, color="#666666", ha="left", va="top")
