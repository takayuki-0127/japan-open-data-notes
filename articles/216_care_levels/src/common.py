"""共通：厚生労働省「介護保険事業状況報告（年報）」全国計の要介護（要支援）認定者数（年度末現在）"""
from pathlib import Path
import logging, warnings
import pandas as pd
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
SOURCE = "出典：厚生労働省「介護保険事業状況報告（年報）」全国計（e-Stat）をもとに作成者が加工して作成"
LEVELS = ["s1", "s2", "k1", "k2", "k3", "k4", "k5"]
NAMES = {"s1": "要支援1", "s2": "要支援2", "k1": "要介護1", "k2": "要介護2", "k3": "要介護3", "k4": "要介護4", "k5": "要介護5"}


def load():
    """年度×区分（tot＝総数、d1＝第1号、d2＝第2号、a65_74、a75p、a85p＝2014年度〜）。経過的要介護は要介護1に含める"""
    d = pd.read_csv(DATA / "care_levels_national_2007_2024.csv")
    d["k1"] = d["k1"] + d["trans"]
    d = d.drop(columns="trans")
    d["total"] = d[LEVELS].sum(axis=1)
    pop = pd.read_csv(DATA / "insured_65plus_2007_2024.csv").set_index("year")["insured_65plus_end"]
    return d, pop
