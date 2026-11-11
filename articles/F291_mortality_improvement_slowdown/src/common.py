"""F291 共通の設定（パス・フォント・年齢区分・生命表）"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; RAW = DATA / "raw"; RES = ROOT / "results"; FIG = ROOT / "figures"
SEXES = ["男", "女"]
COL = {"男": "#1f77b4", "女": "#d62728"}
# 5歳階級：0, 1-4, 5-9, ..., 95-99, 100+
GROUPS = [(0, 0), (1, 4)] + [(a, a + 4) for a in range(5, 100, 5)] + [(100, 200)]
GLABEL = ["0", "1〜4"] + [f"{a}〜{a+4}" for a in range(5, 100, 5)] + ["100以上"]
GSTART = [g[0] for g in GROUPS]

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110


def group_of(age):
    for i, (a, b) in enumerate(GROUPS):
        if a <= age <= b:
            return i
    raise ValueError(age)


def life_table(mx):
    """各歳 mx（0〜99＋100以上の開いた階級）から lx・Lx・ex0。a=0.5（0歳0.1）。"""
    mx = np.asarray(mx, float); n = len(mx)
    a = np.full(n, 0.5); a[0] = 0.1
    q = mx / (1 + (1 - a) * mx); q[-1] = 1.0
    l = np.ones(n); 
    for i in range(1, n):
        l[i] = l[i - 1] * (1 - q[i - 1])
    d = l * q
    L = l - (1 - a) * d
    L[-1] = l[-1] / mx[-1]
    T = L[::-1].cumsum()[::-1]
    return l, L, T


def arriaga(mx1, mx2):
    """Arriaga 法：mx1→mx2 の e0 の差を各歳の寄与に分ける（合計＝差）。"""
    l1, L1, T1 = life_table(mx1); l2, L2, T2 = life_table(mx2)
    n = len(l1); c = np.zeros(n)
    for x in range(n - 1):
        c[x] = l1[x] * (L2[x] / l2[x] - L1[x] / l1[x]) + T2[x + 1] * (l1[x] / l2[x] - l1[x + 1] / l2[x + 1])
    c[n - 1] = l1[n - 1] * (T2[n - 1] / l2[n - 1] - T1[n - 1] / l1[n - 1])
    return c, T1[0], T2[0]
