"""共通：介護給付費等実態統計（年度報告）の介護サービス年間実受給者数を読む"""
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
SOURCE = "出典：厚生労働省「介護給付費等実態統計」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00450049）をもとに作成者が加工して作成"


def load():
    nat = pd.read_csv(DATA / "national.csv").set_index("fiscal_year")
    # 2016年度から小規模な通所介護は「地域密着型通所介護」に移ったので、両方を足して通所介護とする
    nat["tsusho_all"] = nat.tsusho_kaigo + nat.chiiki_tsusho.fillna(0)
    pref = pd.read_csv(DATA / "pref_2015_2025.csv")
    pref["tsusho_all_2015"] = pref.tsusho_kaigo_2015
    pref["tsusho_all_2025"] = pref.tsusho_kaigo_2025 + pref.chiiki_tsusho_2025
    return nat, pref


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
