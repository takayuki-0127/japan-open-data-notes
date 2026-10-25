"""共通：財務省「法人企業統計調査」四半期別調査の時系列（1954年4〜6月期〜）と内閣府の景気基準日付"""
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
SOURCE = "出典：財務省「法人企業統計調査」（四半期別調査、時系列データ）、内閣府「景気基準日付」をもとに作成者が加工して作成"



# 内閣府「景気基準日付」（山・谷の年月）
PEAKS = ["1954-01", "1957-06", "1961-12", "1964-10", "1970-07", "1973-11", "1977-01", "1980-02", "1985-06", "1991-02", "1997-05", "2000-11", "2008-02", "2012-03", "2018-10"]
TROUGHS = ["1954-11", "1958-06", "1962-10", "1965-10", "1971-12", "1975-03", "1977-10", "1983-02", "1986-11", "1993-10", "1999-01", "2002-01", "2009-03", "2012-11", "2020-05"]


def load():
    """四半期（開始月）×項目。単位は億円。all＝全規模、large＝資本金10億円以上、mid＝1億〜10億円、small＝1千万〜1億円、mfg/nonmfg＝製造業/非製造業（全規模）。金融業・保険業を除く"""
    d = pd.read_csv(DATA / "mof_quarterly_1954_2026.csv")
    d.index = pd.PeriodIndex(d.quarter_start, freq="Q")
    return d.drop(columns="quarter_start")


def labor_share(d, g):
    """労働分配率＝人件費÷（人件費＋経常利益＋支払利息等＋減価償却費）。四半期調査で取れる項目による近似"""
    va = d[f"personnel_{g}"] + d[f"ordinary_profit_{g}"] + d[f"interest_expense_{g}"] + d[f"depreciation_{g}"]
    return d[f"personnel_{g}"] / va * 100


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
