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

def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 130

def num(s):
    s = str(s).replace(",", "").replace(" ", "").strip()
    if s in ("", "…", "***", "-", "x"):
        return float("nan")
    return float(s)
