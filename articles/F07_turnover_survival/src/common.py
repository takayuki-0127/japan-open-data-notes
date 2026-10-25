"""F07 共通：パス・図の体裁"""
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
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#8a5cc2"
EDU = ["中学", "高校", "短大等", "大学"]
EDU_COL = {"中学": GRAY, "高校": ORANGE, "短大等": GREEN, "大学": BLUE}
SOURCE = "出典：厚生労働省「新規学卒就職者の離職状況」「一般職業紹介状況」、総務省「労働力調査」をもとに作成者が加工して作成"
SEED = 20260325

def note(fig, text=SOURCE):
    fig.text(0.01, -0.02, text, fontsize=8, color=GRAY, ha="left", va="top")
