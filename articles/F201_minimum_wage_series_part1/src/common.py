from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for d in (DATA, RES, FIG):
    d.mkdir(parents=True, exist_ok=True)

SEED = 201
EXCL = [2020, 2021, 2022]   # コロナ期（主分析から外す）


def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "NotoSansJP" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans JP", "sans-serif"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
