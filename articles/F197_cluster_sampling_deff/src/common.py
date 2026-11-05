"""共通：データの読み込み、指標、地区（クラスター）の作り方、分散の式。"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RES = BASE / "results"
FIG = BASE / "figures"
for d in (DATA / "raw", RES, FIG):
    d.mkdir(parents=True, exist_ok=True)
SEED = 20261105
# 避難指示区域が設定された福島県の12市町村（F180 と同じ）
EVAC = {"07211", "07212", "07308", "07541", "07542", "07543", "07544", "07545", "07546", "07547", "07548", "07564"}

# 推定したい値：市区町村の値の単純平均（households_total だけは全国の合計）
IND = {
    "aging": "高齢化率（%）",
    "hh_size": "1世帯あたり人数",
    "births": "人口千人あたり出生数",
    "emp_ratio": "人口あたり従業者数",
    "farms": "千世帯あたり農家数",
    "pop_change": "5年間の人口増減率（%）",
    "households_total": "世帯数の全国合計",
}
IND_ORDER = list(IND)
MEAN_IND = [k for k in IND_ORDER if k != "households_total"]


def load(year="y"):
    """1行＝市区町村。year='y' は今の値（2026年版）、'x' は前回の値（2021年版）。
    避難指示区域が設定された福島県の12市町村（2015年の値が極端になる）と、
    前回の人口が0の町を母集団から除く。"""
    df = pd.read_csv(DATA / "frame.csv")
    df = df[(df["x_pop"] > 0) & ~df["area_code"].str[1:].isin(EVAC)].sort_values("area_code").reset_index(drop=True)
    p = year
    out = pd.DataFrame({"area_code": df["area_code"], "pref": df["pref"]})
    out["aging"] = df[f"{p}_elderly"] / df[f"{p}_pop"] * 100
    out["hh_size"] = df[f"{p}_pop"] / df[f"{p}_households"]
    out["births"] = df[f"{p}_births"] / df[f"{p}_pop"] * 1000
    out["emp_ratio"] = df[f"{p}_employees"] / df[f"{p}_pop"]
    out["farms"] = df[f"{p}_farms"] / df[f"{p}_households"] * 1000
    # 人口増減は 2015→2020 の1通りしかない（年の頑健性では同じ値を使う）
    out["pop_change"] = (df["y_pop"] / df["x_pop"] - 1) * 100
    out["households_total"] = df[f"{p}_households"]
    return out


# ---------------------------------------------------------------- 地区の作り方
def clusters(df, kind, m, rng):
    """地区の番号（0..M-1）を返す。都道府県をまたがない（national_random を除く）。
    adjacent : 都道府県の中で地域コード順に m 個ずつ（コードが近い＝同じ郡などにまとまりやすい）
    pref_random : 都道府県の中でランダムに並べ替えてから m 個ずつ
    national_random : 全国でランダムに並べ替えてから m 個ずつ（地域のまとまりなし）
    prefecture : 都道府県そのものを1つの地区にする（m は使わない）"""
    n = len(df)
    lab = np.empty(n, dtype=int)
    if kind == "prefecture":
        return pd.factorize(df["pref"])[0]
    if kind == "national_random":
        order = rng.permutation(n)
        lab[order] = np.arange(n) // m
        return lab
    nxt = 0
    for p, idx in df.groupby("pref").indices.items():
        idx = np.sort(idx)
        if kind == "pref_random":
            idx = rng.permutation(idx)
        g = np.arange(len(idx)) // m
        lab[idx] = g + nxt
        nxt += g.max() + 1
    return lab


def icc_anova(y, lab):
    """級内相関（大きさの違う地区での ANOVA 推定）。"""
    y = np.asarray(y, float)
    s = pd.Series(y).groupby(lab)
    k = s.ngroups
    ni = s.size().to_numpy()
    N = ni.sum()
    gm = y.mean()
    ssb = (ni * (s.mean().to_numpy() - gm) ** 2).sum()
    ssw = ((y - pd.Series(lab).map(s.mean()).to_numpy()) ** 2).sum()
    msb = ssb / (k - 1)
    msw = ssw / (N - k)
    n0 = (N - (ni ** 2).sum() / N) / (k - 1)
    return (msb - msw) / (msb + (n0 - 1) * msw)


def var_cluster_mean(y, lab, k):
    """地区を k 個、単純無作為に選び全部調べるときの、拡大推定（平均）の分散（厳密）。
    推定量 = (M/k) Σ T_c / N。"""
    y = np.asarray(y, float)
    T = pd.Series(y).groupby(lab).sum().to_numpy()
    M = len(T)
    N = len(y)
    return (M ** 2) * (1 - k / M) * T.var(ddof=1) / k / N ** 2


def var_srs_mean(y, n):
    y = np.asarray(y, float)
    N = len(y)
    return (1 - n / N) * y.var(ddof=1) / n


def var_cluster_ratio(y, lab, k):
    """地区を k 個選んだときの、比推定（選んだ地区の合計÷選んだ市区町村の数）の分散（線形化）。
    実際の調査で平均を出すときのふつうの形。"""
    y = np.asarray(y, float)
    g = pd.Series(y).groupby(lab)
    T = g.sum().to_numpy()
    cnt = g.size().to_numpy()
    M = len(T)
    N = len(y)
    R = y.mean()
    d = T - R * cnt
    return (M ** 2) * (1 - k / M) * d.var(ddof=1) / k / N ** 2
