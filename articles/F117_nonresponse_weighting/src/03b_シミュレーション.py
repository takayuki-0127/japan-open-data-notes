"""F117 03b シミュレーション：答えが分かっている「架空の日本の世帯」で、回収率を下げていったときに、
平均所得・中央値・低所得の割合がどれだけずれるか。人数と世帯主の年齢で重み付けし直すと、どこまで戻るか。

- 母集団：2025年国勢調査の「世帯主の年齢（7区分）×世帯人員（6区分）」の構成。各セルの所得は、
  国民生活基礎調査（2024年の所得）の表から作った分布（03_分析.py と同じ「同じ所得階級なら人数と年齢は独立」の仮定）。
- 回答の確率：logit p = b0 + βs・単独 + βy・世帯主40歳未満 (+ 所得による項)。βs, βy は、回収率62.6%のときに
  回答者の構成が2025年の所得票（単独31.4%、世帯主29歳以下3.6%）に近づくように決めた。b0 で全体の回収率を動かす。
- 所得による項（答えに影響する「見えない」理由）：
  MAR       ：なし（回答は人数と年齢だけで決まる）
  低所得ほど答えない：+γ・(u−0.5)     u はセルの中での所得の順位（0〜1）
  高所得ほど答えない：−γ・(u−0.5)
  両端が答えない     ：−γ・|u−0.5|・2
"""
from pathlib import Path
import numpy as np
import pandas as pd
from common import SIZES, AGES

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
R = ROOT / "results"
SEED = 1170
rng = np.random.default_rng(SEED)

i22 = pd.read_csv(D / "income_by_size_2024.csv")
i26 = pd.read_csv(D / "income_by_headage_2024.csv")
T_size = i22[SIZES].values.T.astype(float)
T_age = i26[AGES].values.T.astype(float)
nk_age = T_age.sum(axis=0)
J = np.einsum("sk,ak->sak", T_size, T_age / np.where(nk_age > 0, nk_age, 1))  # 6×7×25
lo = i22.lo.values.astype(float)
hi = i22.hi.values.astype(float)
ALPHA = 3.4
cj = pd.read_csv(D / "census2025_headage_by_size.csv").set_index("a").loc[AGES, SIZES].values.T.astype(float)  # 6×7

# ---------- 母集団 ----------
N = 300_000
cellp = (cj / cj.sum()).ravel()
cells = rng.choice(len(cellp), size=N, p=cellp)
s_idx, a_idx = np.divmod(cells, len(AGES))
inc = np.empty(N)
u_in_cell = np.empty(N)
for c in np.unique(cells):
    m = cells == c
    s, a = divmod(c, len(AGES))
    pk = J[s, a]
    if pk.sum() == 0:  # 調査にいないセル：同じ人数の分布で代用
        pk = T_size[s]
    pk = pk / pk.sum()
    k = rng.choice(len(pk), size=m.sum(), p=pk)
    x = np.where(np.isnan(hi[k]), lo[k] * (1 - rng.random(m.sum())) ** (-1 / ALPHA),
                 lo[k] + rng.random(m.sum()) * (np.nan_to_num(hi[k]) - lo[k]))
    inc[m] = x
    # セルの中での所得の順位
    order = x.argsort().argsort()
    u_in_cell[m] = (order + 0.5) / m.sum()
single = (s_idx == 0).astype(float)
young = (a_idx <= 1).astype(float)   # 世帯主40歳未満
age29 = (a_idx == 0)


def wstats(x, w):
    o = np.argsort(x)
    xs, ws = x[o], w[o]
    cw = np.cumsum(ws) / ws.sum()
    med = xs[np.searchsorted(cw, 0.5)]
    return dict(mean=float((x * w).sum() / w.sum()), median=float(med),
                below200=float(w[x < 200].sum() / w.sum() * 100))


TRUTH = wstats(inc, np.ones(N))
pop_size = np.bincount(s_idx, minlength=6).astype(float)
pop_age = np.bincount(a_idx, minlength=7).astype(float)


def rake_w(si, ai, iters=50):
    w = np.ones(len(si))
    for _ in range(iters):
        cs = np.bincount(si, weights=w, minlength=6)
        w *= (pop_size / pop_size.sum() * w.sum() / np.where(cs > 0, cs, 1))[si]
        ca = np.bincount(ai, weights=w, minlength=7)
        w *= (pop_age / pop_age.sum() * w.sum() / np.where(ca > 0, ca, 1))[ai]
    return w


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def b0_for(rate, lin):
    lo_, hi_ = -10.0, 10.0
    for _ in range(60):
        mid = (lo_ + hi_) / 2
        if sigmoid(mid + lin).mean() < rate:
            lo_ = mid
        else:
            hi_ = mid
    return (lo_ + hi_) / 2


# ---------- βs, βy を決める（回収率62.6%で、回答者の単独31.4%・世帯主29歳以下3.6%に近づける）----------
TARGET_SINGLE, TARGET_A29 = 31.37, 3.62
best = None
for bs in np.arange(-1.6, 0.01, 0.05):
    for by in np.arange(-2.0, 0.01, 0.05):
        lin = bs * single + by * young
        p = sigmoid(b0_for(0.626, lin) + lin)
        sh_s = (p * single).sum() / p.sum() * 100
        sh_a = (p * age29).sum() / p.sum() * 100
        err = (sh_s - TARGET_SINGLE) ** 2 + (sh_a - TARGET_A29) ** 2
        if best is None or err < best[0]:
            best = (err, bs, by, sh_s, sh_a)
_, BS, BY, sh_s, sh_a = best
print(f"beta_single={BS:.2f} beta_young={BY:.2f} -> 単独 {sh_s:.1f}% 29歳以下 {sh_a:.1f}%")

SCEN = {
    "MAR（人数と年齢だけ）": lambda g: 0 * u_in_cell,
    "低所得ほど答えない": lambda g: g * (u_in_cell - 0.5),
    "高所得ほど答えない": lambda g: -g * (u_in_cell - 0.5),
    "両端が答えない": lambda g: -g * np.abs(u_in_cell - 0.5) * 2,
}
RATES = [0.95, 0.90, 0.80, 0.70, 0.626, 0.50, 0.40]
GAMMAS = {"基本": 1.0, "弱い": 0.5, "強い": 2.0}
N_SAMPLE = 28_000
REPS = 30

rows = []
for gname, g in GAMMAS.items():
    for sname, f in SCEN.items():
        if sname.startswith("MAR") and gname != "基本":
            continue
        lin = BS * single + BY * young + f(g)
        for rate in RATES:
            b0 = b0_for(rate, lin)
            p_all = sigmoid(b0 + lin)
            for rep in range(REPS):
                samp = rng.choice(N, size=N_SAMPLE, replace=False)
                resp = samp[rng.random(N_SAMPLE) < p_all[samp]]
                x = inc[resp]
                un = wstats(x, np.ones(len(x)))
                rk = wstats(x, rake_w(s_idx[resp], a_idx[resp]))
                rows.append(dict(gamma=gname, scenario=sname, rate=rate, rep=rep, n_resp=len(resp),
                                 single_share=single[resp].mean() * 100,
                                 **{f"un_{k}": v for k, v in un.items()}, **{f"rk_{k}": v for k, v in rk.items()}))
sim = pd.DataFrame(rows)
for k in ["mean", "median", "below200"]:
    sim[f"un_{k}_bias"] = sim[f"un_{k}"] - TRUTH[k]
    sim[f"rk_{k}_bias"] = sim[f"rk_{k}"] - TRUTH[k]
sim.to_csv(R / "sim_runs.csv", index=False)

agg = sim.groupby(["gamma", "scenario", "rate"]).agg(
    n_resp=("n_resp", "mean"), single_share=("single_share", "mean"),
    un_mean_bias=("un_mean_bias", "mean"), rk_mean_bias=("rk_mean_bias", "mean"),
    un_median_bias=("un_median_bias", "mean"), rk_median_bias=("rk_median_bias", "mean"),
    un_below200_bias=("un_below200_bias", "mean"), rk_below200_bias=("rk_below200_bias", "mean"),
    rk_mean_sd=("rk_mean", "std"), un_mean_sd=("un_mean", "std")).reset_index()
agg.to_csv(R / "sim_summary.csv", index=False)
pd.DataFrame([dict(N=N, n_sample=N_SAMPLE, reps=REPS, seed=SEED, beta_single=BS, beta_young=BY,
                   resp_single_at_626=sh_s, resp_a29_at_626=sh_a, **{f"truth_{k}": v for k, v in TRUTH.items()})]
             ).to_csv(R / "sim_setup.csv", index=False)
pd.set_option("display.width", 250)
print(TRUTH)
print(agg[agg.gamma == "基本"].round(2).to_string())
print(agg[agg.gamma != "基本"][agg.rate.isin([0.626, 0.5])].round(2).to_string())
