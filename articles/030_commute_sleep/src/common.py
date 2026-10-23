"""共通：SSDSE（教育用標準データセット）の読み込みと図の設定"""
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef"


def source(name):
    return f"出典：独立行政法人統計センター「{name}」（https://www.nstac.go.jp/use/literacy/ssdse/）をもとに作成者が加工して作成"


def read(name):
    """1行目＝項目コード、2行目＝項目名。項目名の辞書も返す"""
    h = pd.read_csv(RAW / f"{name}.csv", encoding="cp932", header=None, nrows=2)
    d = pd.read_csv(RAW / f"{name}.csv", encoding="cp932", header=None, skiprows=2)
    d.columns = list(h.iloc[0])
    labels = dict(zip(h.iloc[0], h.iloc[1]))
    return d, labels
