"""マルコフ連鎖で「今の人の流れが続いたら、人口の分布は最後にどうなるか」を計算する。

推移確率 P[i,j] = (i→j の移動者数) / (i の日本人人口)、P[i,i] = 1 − 転出率。
定常分布 π は π P = π を満たす分布（P の固有値1の左固有ベクトル）。
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, TOKYO_AREA, SEED

flows = pd.read_csv(DATA / "flows.csv")
dem = pd.read_csv(DATA / "demog.csv")
shares = pd.read_csv(DATA / "pop_shares.csv")
names = shares[["code", "pref"]].sort_values("code").pref.tolist()
N = 47
ta = np.array([p in TOKYO_AREA for p in names])
tk = np.array([p == "東京都" for p in names])


def flow_mat(years):
    f = flows[flows.year.isin(years)].groupby(["o", "d"]).flow.sum() / len(years)
    M = np.zeros((N, N))
    for (o, d), v in f.items():
        M[o - 1, d - 1] = v
    return M


def pop_vec(year, col="jp_pop"):
    y = min(max(year, dem.year.min()), dem.year.max())
    return dem[dem.year == y].sort_values("code")[col].to_numpy(float)


def trans(M, pop):
    P = M / pop[:, None]
    np.fill_diagonal(P, 0.0)
    np.fill_diagonal(P, 1.0 - P.sum(axis=1))
    return P


def stationary(P):
    w, v = np.linalg.eig(P.T)
    k = np.argmin(np.abs(w - 1))
    pi = np.real(v[:, k]); pi = pi / pi.sum()
    lam = np.sort(np.abs(w))[::-1]
    return pi, lam


def half_life(lam2):
    return np.log(0.5) / np.log(lam2)


res = {}
# ---- 基本：2025年の流れ（人口は SSDSE の最新 2023年）----
M25 = flow_mat([2025]); pop25 = pop_vec(2023)
P25 = trans(M25, pop25)
pi25, lam25 = stationary(P25)
now = shares.sort_values("code").census2025.to_numpy(float)
now_s = now / now.sum()
res["base"] = dict(
    out_rate_med=float(np.median(1 - np.diag(P25))),
    tokyo_area_now=float(now_s[ta].sum()), tokyo_area_pi=float(pi25[ta].sum()),
    tokyo_now=float(now_s[tk].sum()), tokyo_pi=float(pi25[tk].sum()),
    lam2=float(lam25[1]), half_life=float(half_life(lam25[1])),
)
tab = pd.DataFrame(dict(pref=names, now=now_s, pi=pi25))
tab["ratio"] = tab.pi / tab.now
tab["net_rate_2025"] = (M25.sum(axis=0) - M25.sum(axis=1)) / pop25
tab.to_csv(RES / "stationary_2025.csv", index=False)
res["base"]["n_gain"] = int((tab.ratio > 1).sum())
res["base"]["ratio_min"] = float(tab.ratio.min()); res["base"]["ratio_max"] = float(tab.ratio.max())
res["base"]["n_below_half"] = int((tab.ratio < 0.5).sum())

# ---- どれくらいで近づくか：2025年の分布から P を繰り返す ----
x = now_s.copy(); path = []
for t in range(0, 301):
    path.append(dict(t=t, tokyo_area=x[ta].sum(), tokyo=x[tk].sum(),
                     dist=0.5 * np.abs(x - pi25).sum()))
    x = x @ P25
path = pd.DataFrame(path); path.to_csv(RES / "path_migration_only.csv", index=False)
d0 = path.dist.iloc[0]
res["base"]["years_to_half_gap"] = int(path[path.dist <= d0 / 2].t.iloc[0])
res["base"]["tokyo_area_2050_mig"] = float(path.tokyo_area.iloc[25])
res["base"]["tokyo_area_2075_mig"] = float(path.tokyo_area.iloc[50])

# ---- 年ごとの定常分布（2012〜2025）----
rows = []
for y in range(2012, 2026):
    P = trans(flow_mat([y]), pop_vec(y))
    pi, lam = stationary(P)
    rows.append(dict(year=y, tokyo_area_pi=pi[ta].sum(), tokyo_pi=pi[tk].sum(),
                     lam2=lam[1], half_life=half_life(lam[1])))
yr = pd.DataFrame(rows); yr.to_csv(RES / "stationary_by_year.csv", index=False)
res["by_year"] = yr.round(4).to_dict(orient="records")

# ---- 出生・死亡も入れた投影（2023年の率を固定）と社人研の比較 ----
b = pop_vec(2023, "births") / pop25; d = pop_vec(2023, "deaths") / pop25
A = P25 + np.diag(b - d)
x = now.copy(); proj = [x.copy()]
for t in range(25):
    x = x @ A; proj.append(x.copy())
p2050 = proj[-1]
ip50 = shares.sort_values("code").ipss2050.to_numpy(float)
cmp = pd.DataFrame(dict(pref=names, census2025=now, mine2050=p2050, ipss2050=ip50,
                        mig_only2050_share=path_share if False else None))
cmp = cmp.drop(columns="mig_only2050_share")
x = now_s.copy()
for t in range(25):
    x = x @ P25
cmp["mig_only_share2050"] = x
cmp["mine_share2050"] = p2050 / p2050.sum(); cmp["ipss_share2050"] = ip50 / ip50.sum()
cmp["now_share"] = now_s
cmp.to_csv(RES / "projection_2050.csv", index=False)
w, v = np.linalg.eig(A.T); k = np.argmax(np.real(w))
gr = np.real(v[:, k]); gr = gr / gr.sum()
res["growth"] = dict(
    total2050_mine=float(p2050.sum()), total2050_ipss=float(ip50.sum()),
    tokyo_area_share2050_mine=float(cmp.mine_share2050[ta].sum()),
    tokyo_area_share2050_ipss=float(cmp.ipss_share2050[ta].sum()),
    tokyo_area_share2050_mig=float(cmp.mig_only_share2050[ta].sum()),
    corr_share_change_vs_ipss=float(np.corrcoef(cmp.mine_share2050 / now_s, cmp.ipss_share2050 / now_s)[0, 1]),
    mad_share_change=float(np.median(np.abs(cmp.mine_share2050 / cmp.ipss_share2050 - 1))),
    annual_growth=float(np.real(w[k]) - 1), tokyo_area_longrun_with_births=float(gr[ta].sum()),
)

# ---- 頑健性 ----
rob = []
def add(label, P):
    pi, lam = stationary(P)
    rob.append(dict(setting=label, tokyo_area_pi=pi[ta].sum(), tokyo_pi=pi[tk].sum(),
                    half_life=half_life(lam[1]),
                    corr_with_base=np.corrcoef(pi, pi25)[0, 1]))
add("基本：2025年の流れ", P25)
add("コロナ前 2017〜19年の平均", trans(flow_mat([2017, 2018, 2019]), pop_vec(2018)))
add("コロナ期 2020〜22年の平均", trans(flow_mat([2020, 2021, 2022]), pop_vec(2021)))
add("直近 2023〜25年の平均", trans(flow_mat([2023, 2024, 2025]), pop_vec(2023)))
add("人口に外国人も含める", trans(M25, pop_vec(2023, "pop")))
add("人口を2025年国勢調査に", trans(M25, now))
# 北海道・沖縄を除く（行・列を落とす）
keep = np.array([p not in ("北海道", "沖縄県") for p in names])
Pk = trans(M25[np.ix_(keep, keep)], pop25[keep])
pik, lamk = stationary(Pk)
rob.append(dict(setting="北海道・沖縄を除く", tokyo_area_pi=pik[ta[keep]].sum(),
                tokyo_pi=pik[tk[keep]].sum(), half_life=half_life(lamk[1]), corr_with_base=np.nan))
rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)
res["robustness"] = rob.round(4).to_dict(orient="records")

# ---- 移動者数のゆらぎ（ポアソン）での区間 ----
rng = np.random.default_rng(SEED)
bs = []
for _ in range(500):
    Mb = rng.poisson(M25).astype(float)
    pi, lam = stationary(trans(Mb, pop25))
    bs.append((pi[ta].sum(), pi[tk].sum(), half_life(lam[1])))
bs = np.array(bs)
res["bootstrap"] = dict(tokyo_area_pi_ci=[float(np.percentile(bs[:, 0], 2.5)), float(np.percentile(bs[:, 0], 97.5))],
                        tokyo_pi_ci=[float(np.percentile(bs[:, 1], 2.5)), float(np.percentile(bs[:, 1], 97.5))],
                        half_life_ci=[float(np.percentile(bs[:, 2], 2.5)), float(np.percentile(bs[:, 2], 97.5))])

json.dump(res, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "by_year"}, ensure_ascii=False, indent=1))
print(yr.round(3).to_string())
print(tab.sort_values("ratio").round(3).head(6).to_string()); print(tab.sort_values("ratio").round(3).tail(6).to_string())
