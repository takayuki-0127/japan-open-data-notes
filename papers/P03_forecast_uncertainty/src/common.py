"""P03 共通：パス・図の体裁・コンフォーマルと整合の小さな関数"""
from pathlib import Path
import logging, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10.5, "axes.titlesize": 12,
                     "figure.dpi": 130, "savefig.bbox": "tight"})

ROOT = Path(__file__).resolve().parents[1]
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, GREEN, PURPLE, RED = "#1f5f8b", "#c0692b", "#9a9a94", "#2e7d4f", "#6b4c9a", "#b5452b"
SEED = 3


def conformal_q(scores, alpha):
    """分割コンフォーマルの分位点：n 個の点数の、ceil((n+1)(1-alpha)) 番目に小さい値"""
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    if k > n:
        return np.inf
    return s[k - 1]


def save(fig, name, source):
    fig.text(0.01, -0.02, source, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
