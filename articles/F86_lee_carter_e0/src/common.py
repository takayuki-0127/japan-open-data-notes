"""共通の設定（パス・フォント・年齢の範囲）"""
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
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42
AGE_MAX = 99          # 0〜99歳を各歳、100歳以上をまとめて1つ（開いた階級）
SEXES = ["男", "女"]

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

COL = {"男": "#1f77b4", "女": "#d62728"}


def e0_from_mx(mx):
    """年齢別死亡率 mx（0..AGE_MAX と最後が開いた階級）から0歳平均余命を計算する。
    各歳は a=0.5（0歳は 0.1）、開いた階級は L = l / m。"""
    mx = np.asarray(mx, dtype=float)
    n = len(mx)
    a = np.full(n, 0.5)
    a[0] = 0.1
    q = mx / (1 + (1 - a) * mx)
    q = np.clip(q, 0, 1)
    l = np.empty(n)
    l[0] = 1.0
    for i in range(1, n):
        l[i] = l[i - 1] * (1 - q[i - 1])
    d = l * q
    L = l - (1 - a) * d
    L[-1] = l[-1] / mx[-1] if mx[-1] > 0 else 0.0
    return L.sum() / l[0]


def e0_from_mx_age(mx, start_age):
    """start_age 歳の平均余命（mx は 0 歳から）"""
    mx = np.asarray(mx, dtype=float)
    n = len(mx)
    a = np.full(n, 0.5); a[0] = 0.1
    q = np.clip(mx / (1 + (1 - a) * mx), 0, 1)
    l = np.empty(n); l[0] = 1.0
    for i in range(1, n):
        l[i] = l[i - 1] * (1 - q[i - 1])
    d = l * q
    L = l - (1 - a) * d
    L[-1] = l[-1] / mx[-1]
    return L[start_age:].sum() / l[start_age]
