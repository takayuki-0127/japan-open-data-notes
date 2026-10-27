from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)


def setup_font():
    for name in ["Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic"]:
        if any(name in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
