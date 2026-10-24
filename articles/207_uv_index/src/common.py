"""共通：気象庁の紫外線観測（日最大UVインデックスの月平均値）を読む"""
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
SOURCE = "出典：気象庁「紫外線のデータ集」（日最大UVインデックスの月平均値）をもとに作成者が加工して作成"



SITES = {"sap": "札幌", "tsu": "つくば", "nah": "那覇", "syo": "南極昭和基地"}
MON = [f"m{i}" for i in range(1, 13)]


def load():
    """地点×年×月の日最大UVインデックスの月平均値。値の後ろの「]」は資料不足値（観測日20日未満）で、値は使い、flagに印を付ける"""
    raw = pd.read_csv(DATA / "uvimax_monthave_raw.csv", dtype=str)
    rows = []
    for _, r in raw.iterrows():
        for m, c in enumerate(MON, 1):
            v = r[c]
            if isinstance(v, str) and v.strip():
                rows.append({"site": r.site, "year": int(r.year), "month": m,
                             "uvi": float(v.rstrip("]")), "insufficient": v.endswith("]")})
    return pd.DataFrame(rows)


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
