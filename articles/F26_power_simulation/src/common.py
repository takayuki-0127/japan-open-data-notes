"""F26 共通：パス・図の体裁・差の差の高速推定（バランスパネル・二方向固定効果）"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#c8423b"
SOURCE = ("出典：総務省「労働力調査（都道府県別モデル推計値）」、国土交通省「国土数値情報（人口集中地区）」ほか"
          "（F01・F14 で整えたデータ）をもとに作成者が加工・シミュレーション")
SEED = 20261027


def save(fig, name, source=SOURCE):
    fig.text(0.01, -0.02, source, fontsize=7, color=GRAY, ha="left", va="top", wrap=True)
    fig.savefig(FIG / name)
    plt.close(fig)


def wide(df, col, years):
    """県×年の行列（47 × T）"""
    w = df.pivot(index="pref", columns="year", values=col).loc[:, years]
    return w.to_numpy(float), list(w.index)


def demean2(Y):
    """二方向の平均を引く（バランスパネル）"""
    return Y - Y.mean(1, keepdims=True) - Y.mean(0, keepdims=True) + Y.mean()


def did_twfe(Y, D):
    """Y, D: N×T。二方向固定効果の DID 係数と各種標準誤差を返す。
    se_ols：普通の OLS、se_hc1：不均一分散に頑健、se_cl：県クラスター（CR1）"""
    N, T = Y.shape
    y, d = demean2(Y), demean2(D)
    sdd = (d * d).sum()
    b = (d * y).sum() / sdd
    e = y - b * d
    dof = N * T - N - T  # 固定効果と係数1つ
    se_ols = np.sqrt((e * e).sum() / dof / sdd)
    se_hc1 = np.sqrt(((d * e) ** 2).sum() * (N * T) / dof) / sdd
    g = (d * e).sum(1)
    c = N / (N - 1) * (N * T - 1) / dof
    se_cl = np.sqrt(c * (g ** 2).sum()) / sdd
    return b, se_ols, se_hc1, se_cl


def wild_cluster_p(Y, D, B, rng):
    """帰無仮説（効果0）を課した wild cluster bootstrap（Rademacher、県単位）の両側 p 値"""
    N, T = Y.shape
    y, d = demean2(Y), demean2(D)
    sdd = (d * d).sum()
    b = (d * y).sum() / sdd
    e = y - b * d
    g = (d * e).sum(1)
    c = N / (N - 1)
    t0 = b / np.sqrt(c * (g ** 2).sum() / sdd ** 2)
    # 帰無の下での残差は y そのもの（係数0）
    W = rng.choice([-1.0, 1.0], size=(B, N))
    ystar = W[:, :, None] * y[None]                       # B×N×T
    bs = (d[None] * ystar).sum((1, 2)) / sdd
    es = ystar - bs[:, None, None] * d[None]
    gs = (d[None] * es).sum(2)                            # B×N
    ts = bs / np.sqrt(c * (gs ** 2).sum(1) / sdd ** 2)
    return (np.abs(ts) >= abs(t0)).mean()
