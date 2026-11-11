"""F268 共通の設定（パス・フォント・生命表と年金現価の計算）"""
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
AGE_MAX = 99          # JMD：0〜99歳を各歳、100歳以上を開いた階級
SEXES = ["男", "女"]
RATE_BASE = 0.017     # 基本の割引率（令和6年財政検証のスプレッド＝賃金に対する運用利回り）
RATES = [0.0, 0.013, 0.017, 0.022, 0.032]
AGE_GROUPS = [(65, 69), (70, 74), (75, 79), (80, 84), (85, 89), (90, 94), (95, 200)]
AGE_GROUP_LABELS = ["65〜69", "70〜74", "75〜79", "80〜84", "85〜89", "90〜94", "95以上"]

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110
COL = {"男": "#1f77b4", "女": "#d62728"}


def qx_from_mx(mx):
    """各歳の mx から qx（a=0.5、0歳は0.1）。最後の要素（開いた階級）は mx のまま返す。"""
    mx = np.asarray(mx, dtype=float)
    a = np.full(len(mx), 0.5); a[0] = 0.1
    q = np.clip(mx / (1 + (1 - a) * mx), 0, 1)
    return q


def survival_from(q, start, open_m=None, tail="const", horizon=60):
    """start 歳から先の t 年生存率 t_p_start（t=0..horizon-1）。
    q は 0 歳からの各歳の死亡確率。最後の年齢以降は
      tail="const"：開いた階級の死亡率 open_m を一定として q=1-exp(-m) で延ばす
      tail="cut"  ：最後の年齢で打ち切る（以降の生存は0）
      tail="grow" ：最後の年齢の q から、死亡率 m を年10%ずつ上げて延ばす"""
    q = np.asarray(q, dtype=float)
    last = len(q) - 1
    qs = []
    for t in range(horizon):
        age = start + t
        if age < last:
            qs.append(q[age])
        else:
            if tail == "cut":
                qs.append(1.0)
            elif tail == "const":
                m = open_m
                qs.append(1 - np.exp(-m))
            elif tail == "grow":
                m = open_m * (1.10 ** (age - last))
                qs.append(1 - np.exp(-m))
    qs = np.array(qs)
    p = np.empty(horizon)
    p[0] = 1.0
    p[1:] = np.cumprod(1 - qs[:-1])
    return p


def annuity_due(p, rate):
    """毎年はじめに1円を払う終身年金の現価 Σ v^t · t_p"""
    v = 1.0 / (1.0 + rate)
    t = np.arange(len(p))
    return float(np.sum(p * v ** t))


def a_x_from_mx(mx, start=65, rate=RATE_BASE, tail="const"):
    """JMD 形式の mx（0..AGE_MAX、最後が開いた階級）から start 歳の年金現価"""
    mx = np.asarray(mx, dtype=float)
    q = qx_from_mx(mx[:-1])          # 0..99 歳
    p = survival_from(q, start, open_m=mx[-1], tail=tail)
    return annuity_due(p, rate)


def e_x_from_mx(mx, start):
    """start 歳の平均余命（F86 と同じ作り方）"""
    mx = np.asarray(mx, dtype=float)
    n = len(mx)
    a = np.full(n, 0.5); a[0] = 0.1
    q = np.clip(mx / (1 + (1 - a) * mx), 0, 1)
    l = np.empty(n); l[0] = 1.0
    for i in range(1, n):
        l[i] = l[i - 1] * (1 - q[i - 1])
    d = l * q
    L = l - (1 - a) * d
    L[-1] = l[-1] / mx[-1] if mx[-1] > 0 else 0.0
    return L[start:].sum() / l[start]
