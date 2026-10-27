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
for p in (RES, FIG):
    p.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
AGES = ["20-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64"]
SEED = 54
