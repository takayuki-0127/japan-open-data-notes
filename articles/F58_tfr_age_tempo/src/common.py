"""共通の設定（パス・フォント・乱数の種）と、年齢別出生率の計算の関数"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110



AGES = np.arange(15, 50)


def mean_age(asfr):
    """年齢別出生率（各歳）から平均出生年齢（年齢 x の出生は x+0.5 歳とみなす）"""
    a = np.asarray(asfr, float)
    return float(((AGES + 0.5) * a).sum() / a.sum())


def bf_adjust(tfr, mab, how="center", smooth=1):
    """Bongaarts–Feeney のテンポ調整：TFR' = TFR / (1 - r)、r は平均出生年齢の年変化。
    how: center は (m[t+1]-m[t-1])/2、back は m[t]-m[t-1]。smooth>1 なら平均出生年齢を先に移動平均する"""
    m = pd.Series(mab, dtype=float)
    if smooth > 1:
        m = m.rolling(smooth, center=True, min_periods=1).mean()
    if how == "center":
        r = (m.shift(-1) - m.shift(1)) / 2
    else:
        r = m - m.shift(1)
    return pd.Series(tfr, index=m.index) / (1 - r), r
