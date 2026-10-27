"""平均への回帰の分析。
1) 都道府県の4指標：その年に「いちばん悪かった5県」は、翌年どれだけ良くなって見えるか（全国の中央値からの差で比べる）
2) 何年あけるか（1〜5年）での違い
3) 「悪かった県に施策をした」と仮定した見かけの効果と、その補正
4) 市区町村の検診受診率：規模が小さいほど回帰が大きいか
5) シミュレーション：信頼性（毎年の値のうち、地域の持続的な差の割合）と回帰の大きさ
6) 頑健性
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
pref = pd.read_csv(DATA / "pref_long.csv")
IND = ["完全失業率", "就業率", "有効求人倍率", "合計特殊出生率"]
out = {}


def wide(ind):
    d = pref[pref.indicator == ind].pivot(index="year", columns="code", values="good").sort_index()
    return d


def rel(w):
    """各年の全国（47都道府県）の中央値からの差。全国共通の動きを除く"""
    return w.sub(w.median(axis=1), axis=0)


def pairs(w, gap=1, k=5, exclude_years=(), select_avg=False, log=False):
    """年 t に下位 k の県の、t+gap での相対位置の変化（元の単位と、t の標準偏差の単位）"""
    if log:
        w = np.log(w.abs()) * np.sign(w)
    r = rel(w)
    years = [y for y in r.index if y + gap in r.index]
    rec = []
    for y in years:
        if y in exclude_years or (y + gap) in exclude_years:
            continue
        a = r.loc[y]
        if select_avg:
            if y - 1 not in r.index or (y - 1) in exclude_years:
                continue
            sel_score = (r.loc[y] + r.loc[y - 1]) / 2
        else:
            sel_score = a
        b = r.loc[y + gap]
        sd = a.std()
        order = sel_score.sort_values()
        worst = order.index[:k]
        best = order.index[-k:]
        mid = order.index[k:-k]
        slope = np.cov(a, b)[0, 1] / a.var()
        rec.append(dict(year=y, sd=sd, slope=slope, corr=np.corrcoef(a, b)[0, 1],
                        worst_t=a[worst].mean(), worst_d=(b[worst] - a[worst]).mean(),
                        best_t=a[best].mean(), best_d=(b[best] - a[best]).mean(),
                        mid_d=(b[mid] - a[mid]).mean(),
                        worst_rank_next=b.rank()[worst].mean(),
                        worst_still=(b.rank()[worst] <= k).mean()))
    return pd.DataFrame(rec)


def summary(df):
    return dict(n_pairs=len(df), worst_d=df.worst_d.mean(), best_d=df.best_d.mean(), mid_d=df.mid_d.mean(),
                worst_d_sd=(df.worst_d / df.sd).mean(), best_d_sd=(df.best_d / df.sd).mean(),
                worst_t_sd=(df.worst_t / df.sd).mean(),
                share_worst_improved=(df.worst_d > 0).mean(), slope=df.slope.mean(), corr=df["corr"].mean(),
                worst_rank_next=df.worst_rank_next.mean(), worst_still=df.worst_still.mean(),
                pred_worst_d=((df.slope - 1) * df.worst_t).mean())


# ---- 1) 1年あけた基本の結果 ----
base = {}
allpairs = []
for ind in IND:
    df = pairs(wide(ind))
    df["indicator"] = ind
    allpairs.append(df)
    base[ind] = summary(df)
pd.concat(allpairs).to_csv(RES / "pairs_gap1.csv", index=False)
out["base"] = base

# ---- 2) 何年あけるか ----
gaps = []
for ind in IND:
    for g in range(1, 6):
        s = summary(pairs(wide(ind), gap=g))
        s.update(indicator=ind, gap=g)
        gaps.append(s)
gaps = pd.DataFrame(gaps)
gaps.to_csv(RES / "gaps.csv", index=False)

# ---- 3) 見かけの施策効果（完全失業率） ----
# 「その年に失業率が高い順に5県へ施策をした」とみなし、翌年の改善を3つのやり方で測る
w = wide("完全失業率")
r = rel(w)
pol = []
for y in r.index[:-1]:
    a, b = r.loc[y], r.loc[y + 1]
    order = a.sort_values()
    tr = order.index[:5]
    nxt = order.index[5:10]
    others = order.index[5:]
    naive = (b[tr] - a[tr]).mean()                       # 前後比較（全国の中央値からの差）
    vs_next = naive - (b[nxt] - a[nxt]).mean()          # 6〜10位の県と比べる
    # 施策のない県だけで「翌年の位置 = 定数 + 傾き×今年の位置」を当てはめ、5県の予測からのずれを効果とみなす
    X = np.column_stack([np.ones(len(others)), a[others].values])
    beta = np.linalg.lstsq(X, b[others].values, rcond=None)[0]
    pred = beta[0] + beta[1] * a[tr].values
    adj = (b[tr].values - pred).mean()
    pol.append(dict(year=y, naive=naive, vs_next=vs_next, adjusted=adj))
pol = pd.DataFrame(pol)
pol.to_csv(RES / "placebo_policy_unemp.csv", index=False)
out["placebo_policy_unemp"] = {c: float(pol[c].mean()) for c in ["naive", "vs_next", "adjusted"]}
out["placebo_policy_unemp"].update({c + "_share_pos": float((pol[c] > 0).mean()) for c in ["naive", "vs_next", "adjusted"]})
# 符号は「良い向き」（失業率なら下がるほど正）

# ---- 4) 市区町村の検診受診率 ----
s = pd.read_csv(DATA / "muni_screening.csv", dtype={"code": str})
sw = s.pivot(index="year", columns="code", values="rate").sort_index()
nw = s.pivot(index="year", columns="code", values="n_colon").sort_index()
keep = sw.notna().all() & nw.notna().all()
sw, nw = sw.loc[:, keep], nw.loc[:, keep]
sr = rel(sw)
size_bins = [0, 500, 2000, 10000, 1e9]
size_lab = ["500人未満", "500〜2,000人", "2,000〜1万人", "1万人以上"]
mrec = []
for y in sr.index[:-1]:
    a, b = sr.loc[y], sr.loc[y + 1]
    n = nw.loc[y]
    cat = pd.cut(n, size_bins, labels=size_lab, right=False)
    q10 = a.quantile(0.1)
    q90 = a.quantile(0.9)
    for lab in size_lab:
        m = cat == lab
        aa, bb = a[m], b[m]
        slope = np.cov(aa, bb)[0, 1] / aa.var()
        lo = aa <= q10
        hi = aa >= q90
        mrec.append(dict(year=y, size=lab, n_muni=int(m.sum()), slope=slope,
                         low_n=int(lo.sum()), low_d=(bb[lo] - aa[lo]).mean(),
                         high_n=int(hi.sum()), high_d=(bb[hi] - aa[hi]).mean()))
    # 全体：下位10%に入った団体のうち、翌年も下位10%に残った割合
mrec = pd.DataFrame(mrec)
mrec.to_csv(RES / "muni_screening_by_size.csv", index=False)
msum = mrec.groupby("size", sort=False).apply(lambda g: pd.Series(dict(
    n_muni=g.n_muni.mean(), slope=g.slope.mean(),
    low_d=np.average(g.low_d.fillna(0), weights=g.low_n) if g.low_n.sum() else np.nan, low_n=g.low_n.sum(),
    high_d=np.average(g.high_d.fillna(0), weights=g.high_n) if g.high_n.sum() else np.nan, high_n=g.high_n.sum()))).reset_index()
msum.to_csv(RES / "muni_screening_summary.csv", index=False)
stay = []
for y in sr.index[:-1]:
    a, b = sr.loc[y], sr.loc[y + 1]
    lo = a <= a.quantile(0.1)
    stay.append((b[lo] <= b.quantile(0.1)).mean())
out["muni"] = dict(n=int(sr.shape[1]), years=[int(y) for y in sr.index], stay_low10=float(np.mean(stay)),
                   by_size=msum.to_dict(orient="records"))

# ---- 5) シミュレーション ----
# X_it = μ_i + e_it、信頼性 ρ = Var(μ)/(Var(μ)+Var(e))。47地域、下位5を選び、翌年の変化（全体の標準偏差の単位）を測る
sim = []
for rho in [0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99]:
    ds, ctrl = [], []
    for _ in range(2000):
        mu = rng.normal(0, np.sqrt(rho), 47)
        x0 = mu + rng.normal(0, np.sqrt(1 - rho), 47)
        x1 = mu + rng.normal(0, np.sqrt(1 - rho), 47)
        o = np.argsort(x0)
        w5 = o[:5]
        ds.append((x1[w5] - x0[w5]).mean())
        # 下位10をくじで5と5に分ける（施策の比較を「くじ」でした場合）
        w10 = rng.permutation(o[:10])
        ctrl.append((x1[w10[:5]] - x0[w10[:5]]).mean() - (x1[w10[5:]] - x0[w10[5:]]).mean())
    sim.append(dict(rho=rho, worst5_d=np.mean(ds), worst5_d_q05=np.quantile(ds, .05), worst5_d_q95=np.quantile(ds, .95),
                    randomized_diff=np.mean(ctrl), randomized_sd=np.std(ctrl)))
sim = pd.DataFrame(sim)
sim.to_csv(RES / "simulation.csv", index=False)

# 実データの信頼性（1年あけた相関）と、シミュレーションから読む「回帰の大きさ」を並べる
fit = []
for ind in IND:
    b = base[ind]
    fit.append(dict(indicator=ind, corr=b["corr"], worst_d_sd=b["worst_d_sd"], worst_t_sd=b["worst_t_sd"],
                    pred_sd=-(1 - b["corr"]) * b["worst_t_sd"]))
pd.DataFrame(fit).to_csv(RES / "reliability_vs_rtm.csv", index=False)

# ---- 6) 頑健性 ----
rob = []
def add(name, ind, df):
    s = summary(df)
    s.update(setting=name, indicator=ind)
    rob.append(s)
for ind in IND:
    w = wide(ind)
    add("基本（下位5・1年）", ind, pairs(w))
    add("下位3", ind, pairs(w, k=3))
    add("下位10", ind, pairs(w, k=10))
    add("2年平均で選ぶ", ind, pairs(w, select_avg=True))
    if ind != "合計特殊出生率":
        add("2020・21年を除く", ind, pairs(w, exclude_years=(2020, 2021)))
        add("対数", ind, pairs(w, log=True))
    else:
        tw = w
        add("1972〜99年", ind, pairs(tw.loc[:1999]))
        add("2000〜23年", ind, pairs(tw.loc[2000:]))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 200)
print(pd.DataFrame(base).T[["n_pairs", "worst_d", "best_d", "mid_d", "worst_d_sd", "best_d_sd", "worst_t_sd", "share_worst_improved", "slope", "corr", "worst_rank_next", "worst_still", "pred_worst_d"]].round(3))
print(gaps[["indicator", "gap", "worst_d_sd", "corr", "share_worst_improved"]].round(3).to_string())
print(out["placebo_policy_unemp"])
print(msum.round(3).to_string())
print("muni stay", out["muni"]["stay_low10"], out["muni"]["n"])
print(sim.round(3).to_string())
print(pd.DataFrame(fit).round(3))
print(rob[["indicator", "setting", "worst_d_sd", "share_worst_improved", "corr"]].round(3).to_string())
