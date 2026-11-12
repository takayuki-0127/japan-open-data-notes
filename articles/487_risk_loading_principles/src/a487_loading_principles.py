"""487 保険料の上乗せを「標準偏差」「分散」「期待効用」で決めると、契約の大きさでどう違うのか（架空の損害）"""
import json
import numpy as np
import pandas as pd
from scipy import optimize, stats
from common import plt, save, RES, DATA, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 487
TARGET = 0.10          # 基準の契約で、どの決め方も上乗せ10%になるように合わせる
REF = dict(lam=10.0, m=10.0, k=1.0)   # 基準：事故の件数の平均10件、1件の平均10万円（指数分布）→ 損害の平均100万円
SRC = "架空の損害（作成者が式で計算。乱数での確かめは seed 487）"
PR = [("sd", "標準偏差に比例", BLUE), ("var", "分散に比例", ORANGE), ("exp", "期待効用（指数）", GREEN)]


# 件数はポアソン、1件の損害はガンマ（形 k、平均 m）。損害の合計 S の平均・分散・指数効用の保険料
def mean_S(c):
    return c["lam"] * c["m"]


def var_S(c):
    return c["lam"] * c["m"] ** 2 * (1 + 1 / c["k"])


def exp_prem(c, a):
    th = c["m"] / c["k"]
    if a * th >= 1:                       # 1件の損害の大きさに対して a が大きすぎると、保険料は無限大
        return np.inf
    return c["lam"] * ((1 - a * th) ** (-c["k"]) - 1) / a


def calib():
    E, V = mean_S(REF), var_S(REF)
    beta = TARGET * E / np.sqrt(V)
    gamma = TARGET * E / V
    a = optimize.brentq(lambda a: exp_prem(REF, a) / E - 1 - TARGET, 1e-8, 0.999 * REF["k"] / REF["m"])
    return beta, gamma, a


def rates(c, beta, gamma, a):
    E, V = mean_S(c), var_S(c)
    return dict(sd=beta * np.sqrt(V) / E, var=gamma * V / E, exp=exp_prem(c, a) / E - 1)


def run():
    beta, gamma, a = calib()

    # 乱数で式を確かめる（基準の契約、200万回）
    rng = np.random.default_rng(SEED)
    N = rng.poisson(REF["lam"], 2_000_000)
    S = np.zeros(len(N))
    tot = N.sum()
    y = rng.gamma(REF["k"], REF["m"] / REF["k"], tot)
    idx = np.repeat(np.arange(len(N)), N)
    np.add.at(S, idx, y)
    chk = dict(mean_formula=mean_S(REF), mean_sim=float(S.mean()), var_formula=var_S(REF), var_sim=float(S.var()),
               exp_formula=exp_prem(REF, a), exp_sim=float(np.log(np.mean(np.exp(a * S))) / a))
    pd.DataFrame([chk]).round(3).to_csv(RES / "formula_check.csv", index=False)

    # 1) 金額の大きさを c 倍（件数は同じ）
    cs = [0.1, 0.2, 0.5, 1, 2, 3, 5, 10, 20, 50, 100]
    r1 = []
    for c in cs:
        k = dict(REF, m=REF["m"] * c)
        r = rates(k, beta, gamma, a)
        r1.append(dict(scale=c, mean=mean_S(k), **{p: r[p] * 100 for p in r}))
    T1 = pd.DataFrame(r1)
    T1.round(3).to_csv(RES / "rate_by_money_scale.csv", index=False)

    # 2) 同じ契約を n 件束ねる（独立）
    ns = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
    r2 = []
    for n in ns:
        k = dict(REF, lam=REF["lam"] * n)
        r = rates(k, beta, gamma, a)
        r2.append(dict(n=n, mean=mean_S(k), **{p: r[p] * 100 for p in r}))
    T2 = pd.DataFrame(r2)
    T2.round(3).to_csv(RES / "rate_by_pool_size.csv", index=False)

    # 3) 24の契約（金額の大きさ3通り×件数4通り×1件の損害のばらつき2通り）での順位
    rows = []
    for sc in (0.2, 1, 5):
        for lam in (0.5, 2, 10, 50):
            for k in (0.5, 2.0):
                m = 100 * sc / lam
                cc = dict(lam=lam, m=m, k=k)
                r = rates(cc, beta, gamma, a)
                rows.append(dict(scale=sc, lam=lam, k=k, sev_mean=m, mean=mean_S(cc), cv=np.sqrt(var_S(cc)) / mean_S(cc),
                                 **{p: r[p] * 100 for p in r}))
    T3 = pd.DataFrame(rows)
    for p, _, _ in PR:
        T3["rank_" + p] = T3[p].rank(ascending=False, method="min").astype(int)
    T3.round(3).to_csv(RES / "rate_24_contracts.csv", index=False)
    pairs = {}
    fin = T3[np.isfinite(T3["exp"])]
    for p1, p2 in (("sd", "var"), ("sd", "exp"), ("var", "exp")):
        D = T3 if "exp" not in (p1, p2) else T3
        x, z = D[p1].values, D[p2].values
        n_rev = 0; n_all = 0
        for i in range(len(D)):
            for j in range(i + 1, len(D)):
                if np.isinf(x[i]) and np.isinf(x[j]) or np.isinf(z[i]) and np.isinf(z[j]):
                    continue
                n_all += 1
                if (x[i] - x[j]) * (z[i] - z[j]) < 0:
                    n_rev += 1
        rho = stats.spearmanr(x, z).statistic
        pairs[f"{p1}_vs_{p2}"] = dict(reversed=n_rev, pairs=n_all, spearman=round(float(rho), 3))
    n_inf = int((~np.isfinite(T3["exp"])).sum())

    pd.DataFrame([dict(beta=beta, gamma=gamma, a=a)]).to_csv(RES / "calibration.csv", index=False)
    T3[["scale", "lam", "k", "sev_mean", "mean", "cv"]].round(4).to_csv(DATA / "contracts_24.csv", index=False)

    # ---- 図1：金額の大きさ
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for p, lab, col in PR:
        s = T1[np.isfinite(T1[p])]
        ax.plot(s.scale, s[p], "o-", color=col, label=lab)
        if p == "exp" and len(s) < len(T1):
            last = s.iloc[-1]
            ax.annotate("この先は無限大\n（計算できない）", (last.scale, last[p]), xytext=(last.scale * 1.6, last[p] * 0.55),
                        fontsize=9, color=GREEN, arrowprops=dict(arrowstyle="->", color=GREEN))
    ax.axvline(1, color=GRAY, ls=":", lw=1); ax.text(1.05, 1.4, "基準の契約", color=GRAY, fontsize=9)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(cs); ax.set_xticklabels([f"{c:g}倍" for c in cs], fontsize=8.5)
    ax.set_yticks([1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]); ax.set_yticklabels([1, 2, 5, 10, 20, 50, 100, 200, 500, 1000])
    ax.set_xlabel("1件の損害の金額の大きさ（基準の契約の何倍か）"); ax.set_ylabel("上乗せ率（損害の平均に対する%）")
    ax.grid(alpha=.3); ax.legend(frameon=False)
    ax.set_title("金額だけを大きくしたとき：同じ契約でも、決め方で上乗せ率が変わる")
    save(fig, "a487_rate_by_money.png", SRC + "。基準（件数の平均10件、1件の平均10万円、指数分布）で3つとも上乗せ10%に合わせた")

    # ---- 図2：束ねる件数
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    for p, lab, col in PR:
        st = dict(sd=dict(ls="-", lw=1.8), var=dict(ls="-", lw=5, alpha=.45), exp=dict(ls="--", lw=1.8))[p]
        ax.plot(T2.n, T2[p], marker="o", color=col, label=lab + ("（2つの線は重なる）" if p == "exp" else ""), **st)
    ax.set_xscale("log"); ax.set_xticks(ns); ax.set_xticklabels(ns)
    ax.set_xlabel("同じ契約を束ねた数（独立）"); ax.set_ylabel("上乗せ率（%）")
    ax.set_ylim(0, 11); ax.grid(alpha=.3); ax.legend(frameon=False)
    ax.set_title("同じ契約を束ねたとき：標準偏差に比例させた決め方だけが下がる")
    save(fig, "a487_rate_by_pool.png", SRC + "。分散に比例・期待効用（指数）は、束ねても上乗せ率が変わらない")

    # ---- 図3：24の契約の順位
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    xs = [0, 1, 2]
    colmap = {0.2: GRAY, 1: BLUE, 5: ORANGE}
    for _, r in T3.iterrows():
        ys = [r.rank_sd, r.rank_var, r.rank_exp]
        ax.plot(xs, ys, "-", color=colmap[r.scale], alpha=.6, lw=1.3)
        ax.plot(xs, ys, "o", color=colmap[r.scale], ms=4)
    for sc, col in colmap.items():
        ax.plot([], [], "-", color=col, label=f"損害の平均{100 * sc:g}万円の契約")
    ax.set_xticks(xs); ax.set_xticklabels([lab for _, lab, _ in PR])
    ax.invert_yaxis(); ax.set_ylabel("上乗せ率の順位（1が最も高い）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("24の契約の上乗せ率の順位は、決め方で入れ替わる")
    save(fig, "a487_rank_24.png", SRC + "。損害の平均（20・100・500万円）×事故の件数の平均（0.5・2・10・50件）×1件の損害のばらつき（2通り）。期待効用（指数）で無限大になった5契約は、同じ順位（1位）とした")

    main = dict(calibration=dict(beta=beta, gamma=gamma, a=a), check=chk,
                money={str(r.scale): {p: (round(float(r[p]), 2) if np.isfinite(r[p]) else "inf") for p, _, _ in PR} for _, r in T1.iterrows()},
                pool={str(int(r.n)): {p: round(float(r[p]), 2) for p, _, _ in PR} for _, r in T2.iterrows()},
                pairs=pairs, exp_infinite_of_24=n_inf,
                exp_limit_scale=float(REF["k"] / (a * REF["m"])))
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(T1.round(2).to_string()); print(T2.round(2).to_string()); print(T3.round(2).to_string()); print(pairs, n_inf, main["exp_limit_scale"], chk)


if __name__ == "__main__":
    run()
