"""共通：パス、定数、必要な標本の大きさの式。"""
from pathlib import Path

import numpy as np
from scipy.stats import norm

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RES = BASE / "results"
FIG = BASE / "figures"
for d in (RES, FIG):
    d.mkdir(parents=True, exist_ok=True)
SEED = 20261105

Z95 = norm.ppf(0.975)          # 1.96
Z80 = norm.ppf(0.80)           # 0.84（検出力80%）

# 労働力調査（2025年平均）：15歳以上人口 = 労働力人口 + 非労働力人口（万人）
LFS_POP15 = 7004 + 3962        # 10,966万人
LFS_LABOR = 7004
LFS_UNEMP = 176
LFS_N_MONTH = 100_000          # 毎月の15歳以上の調査対象（約10万人）


def n_margin(p, e, deff=1.0, z=Z95):
    """割合 p を ±e（絶対値）で推定するのに要る標本の大きさ。"""
    return deff * z**2 * p * (1 - p) / e**2


def n_cv(p, cv, deff=1.0):
    """割合 p の推定値の標準誤差率（相対）を cv にするのに要る標本の大きさ。"""
    return deff * (1 - p) / (p * cv**2)


def n_change(p, d, rho=0.0, deff=1.0, z_a=Z95, z_b=Z80):
    """2時点の割合の差 d を検出力80%・両側5%で見分けるのに要る、各時点の標本の大きさ。
    rho は2時点の推定値の相関（標本の重なりによる）。"""
    return deff * (z_a + z_b) ** 2 * 2 * (1 - rho) * p * (1 - p) / d**2


def srs_se_total(N, X, n):
    """母集団 N のうち X 人が持つ属性の総数を、n 人の単純無作為で推定したときの標準誤差。"""
    p = X / N
    fpc = 1 - n / N
    return N * np.sqrt(p * (1 - p) / n * fpc)
