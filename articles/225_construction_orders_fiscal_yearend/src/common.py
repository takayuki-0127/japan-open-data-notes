"""共通：建設工事受注動態統計調査（大手50社調査、国土交通省）の月次受注高 2011年1月〜2026年8月を読む"""
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
SOURCE = "出典：国土交通省「建設工事受注動態統計調査（大手50社調査）」をもとに作成者が加工して作成"
COLS = {"total": "総計", "private_mfg": "民間・製造業", "private_nonmfg": "民間・非製造業", "public_national": "公共・国の機関",
        "public_local": "公共・地方の機関", "overseas": "海外"}


def load():
    """月次の受注高（百万円）。fy は4月始まりの年度"""
    d = pd.read_csv(DATA / "big50_orders_monthly_2011_2026.csv")
    d["date"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
    d["fy"] = np.where(d.month >= 4, d.year, d.year - 1)
    return d.set_index("date")


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
