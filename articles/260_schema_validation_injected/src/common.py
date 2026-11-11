"""共通：フォント・保存先・SSDSE-B の読み込み"""
from pathlib import Path
import logging, warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight", "svg.hashsalt": "ssdse", "path.simplify": False})
ROOT = Path(__file__).resolve().parents[1]
DATA, FIG, RES = ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：独立行政法人統計センター「SSDSE-県別推移（SSDSE-B）」をもとに作成者が加工して作成"


def read_raw(path):
    """SSDSE-B の CSV を、1行目（コード）・2行目（項目名）・本体に分けて読む。文字はすべて文字列のまま"""
    d = pd.read_csv(path, encoding="cp932", header=None, dtype=str, keep_default_na=False)
    codes, names = list(d.iloc[0]), list(d.iloc[1])
    body = d.iloc[2:].reset_index(drop=True)
    return codes, names, body


def save(fig, name, source=SOURCE, y=-0.02):
    fig.text(0.0, y, source, fontsize=8, color=GRAY, ha="left", va="top", transform=fig.transFigure)
    fig.savefig(FIG / name, metadata={"Software": None})
    plt.close(fig)
