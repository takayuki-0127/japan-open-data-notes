"""共通：NDBオープンデータ（第10回）特定健診のHbA1c・BMIの都道府県別分布を読む"""
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
SOURCE = "出典：厚生労働省「第10回NDBオープンデータ」（特定健診 検査値、2022年度）をもとに作成者が加工して作成"



def load():
    """都道府県×性×5歳階級（40〜74歳）の受診者数。h65=HbA1c 6.5%以上、h60=6.0以上6.5未満、h56=5.6以上6.0未満、hlo=5.6未満、
    b30=BMI 30以上、b25=25以上30未満、bmid=18.5以上25未満、blo=18.5未満（NGSP値、kg/m2）"""
    d = pd.read_csv(DATA / "ndb_checkup_hba1c_bmi_2022.csv")
    d["hn"] = d[["h65", "h60", "h56", "hlo"]].sum(axis=1)
    d["bn"] = d[["b30", "b25", "bmid", "blo"]].sum(axis=1)
    return d


def std_rate(d, num, den):
    """全国の受診者の性・年齢構成を重みにした、直接法の年齢調整割合（%）"""
    w = d.groupby(["sex", "age"])[den].sum(); w = w / w.sum()
    x = d.assign(r=d[num] / d[den], w=[w[(s, a)] for s, a in zip(d.sex, d.age)])
    return x.groupby("pref", sort=False).apply(lambda g: (g.r * g.w).sum() * 100)


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)

