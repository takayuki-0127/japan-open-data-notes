"""488 事故0件の契約が多いデータをポアソンで見ると、件数の見積もりはどれだけずれるのか（架空の件数）"""
import json
import numpy as np
import pandas as pd
from scipy import optimize, special, stats
from common import plt, save, RES, DATA, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 488
REPS = 300
NS = [1000, 5000, 20000]
MAIN_N = 5000
SRC = "架空の事故件数（作成者が乱数で作成、seed 488）"
MODELS = ["ポアソン", "負の二項", "ゼロ過剰ポアソン", "ゼロ過剰負の二項"]
MCOL = {"ポアソン": BLUE, "負の二項": ORANGE, "ゼロ過剰ポアソン": GREEN, "ゼロ過剰負の二項": GRAY}

# 正解の4場面（平均はどれも1契約あたり年0.10件前後）
SCEN = [
    dict(key="P", name="A：ポアソン（0は過剰でない）", pi=0.0, mu=0.10, r=np.inf),
    dict(key="NB", name="B：負の二項（事故の起こしやすさに差）", pi=0.0, mu=0.10, r=0.5),
    dict(key="ZIP", name="C：ゼロ過剰ポアソン（半数は事故を起こさない）", pi=0.5, mu=0.20, r=np.inf),
    dict(key="ZINB", name="D：ゼロ過剰負の二項", pi=0.5, mu=0.20, r=1.0),
]


def pmf_nb(k, mu, r):
    if np.isinf(r):
        return stats.poisson.pmf(k, mu)
    p = r / (r + mu)
    return stats.nbinom.pmf(k, r, p)


def pmf(k, s):
    base = pmf_nb(k, s["mu"], s["r"])
    return s["pi"] * (k == 0) + (1 - s["pi"]) * base


def draw(s, n, rng):
    if np.isinf(s["r"]):
        y = rng.poisson(s["mu"], n)
    else:
        lam = rng.gamma(s["r"], s["mu"] / s["r"], n)
        y = rng.poisson(lam)
    if s["pi"] > 0:
        y = np.where(rng.random(n) < s["pi"], 0, y)
    return y


# ---- 4つのモデルを、件数ごとの度数から最尤法で当てはめる（説明変数なし）
def fit(model, cnt):
    k = np.arange(len(cnt))
    n = cnt.sum()
    mean = (k * cnt).sum() / n

    def ll_nb(mu, r, pi):
        if np.isinf(r):
            lp = stats.poisson.logpmf(k, mu)
        else:
            lp = special.gammaln(k + r) - special.gammaln(r) - special.gammaln(k + 1) + r * np.log(r / (r + mu)) + k * np.log(mu / (r + mu))
        if pi > 0:
            p0 = np.log(pi + (1 - pi) * np.exp(lp[0]))
            lp = np.concatenate([[p0], np.log(1 - pi) + lp[1:]])
        return (cnt * lp).sum()

    if model == "ポアソン":
        par = dict(mu=mean, r=np.inf, pi=0.0); npar = 1
    elif model == "負の二項":
        f = lambda t: -ll_nb(np.exp(t[0]), np.exp(t[1]), 0.0)
        o = optimize.minimize(f, [np.log(mean), 0.0], method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-9, maxiter=4000))
        par = dict(mu=np.exp(o.x[0]), r=np.exp(o.x[1]), pi=0.0); npar = 2
        if par["r"] > 1e5: par["r"] = np.inf
    elif model == "ゼロ過剰ポアソン":
        f = lambda t: -ll_nb(np.exp(t[0]), np.inf, special.expit(t[1]))
        o = optimize.minimize(f, [np.log(mean * 2), 0.0], method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-9, maxiter=4000))
        par = dict(mu=np.exp(o.x[0]), r=np.inf, pi=special.expit(o.x[1])); npar = 2
    else:
        f = lambda t: -ll_nb(np.exp(t[0]), np.exp(t[1]), special.expit(t[2]))
        best = None
        for st in ([np.log(mean * 2), 0.0, 0.0], [np.log(mean), 1.0, -3.0], [np.log(mean * 3), -1.0, 1.0]):
            o = optimize.minimize(f, st, method="Nelder-Mead", options=dict(xatol=1e-7, fatol=1e-9, maxiter=6000))
            if best is None or o.fun < best.fun: best = o
        par = dict(mu=np.exp(best.x[0]), r=np.exp(best.x[1]), pi=special.expit(best.x[2])); npar = 3
        if par["r"] > 1e5: par["r"] = np.inf
    ll = ll_nb(par["mu"], par["r"], par["pi"])
    return par, ll, 2 * npar - 2 * ll


def summarize(par):
    k = np.arange(0, 40)
    pr = par["pi"] * (k == 0) + (1 - par["pi"]) * pmf_nb(k, par["mu"], par["r"])
    m = (k * pr).sum(); v = (k * k * pr).sum() - m * m
    return dict(p0=pr[0], p1=pr[1], p2plus=1 - pr[0] - pr[1], p3plus=1 - pr[:3].sum(), mean=m, var=v)


def truth_summary(s):
    return summarize(dict(mu=s["mu"], r=s["r"], pi=s["pi"]))


def run():
    rng = np.random.default_rng(SEED)
    rows, sel = [], []
    for s in SCEN:
        tr = truth_summary(s)
        for n in NS:
            for rep in range(REPS):
                y = draw(s, n, rng)
                cnt = np.bincount(y, minlength=1)
                fits = {m: fit(m, cnt) for m in MODELS}
                aics = {m: fits[m][2] for m in MODELS}
                best = min(aics, key=aics.get)
                sel.append(dict(scen=s["key"], n=n, rep=rep, best=best))
                if n == MAIN_N:
                    for m in MODELS:
                        sm = summarize(fits[m][0])
                        rows.append(dict(scen=s["key"], model=m, rep=rep, obs_p0=cnt[0] / n,
                                         obs_p2plus=(y >= 2).mean(), obs_var=y.var(),
                                         **{"err_" + k: (sm[k] / tr[k] - 1) * 100 for k in ("p0", "p2plus", "p3plus", "mean", "var")},
                                         **{"fit_" + k: sm[k] for k in ("p0", "p2plus", "var")}))
    R = pd.DataFrame(rows)
    S = pd.DataFrame(sel)
    truth = pd.DataFrame([dict(scen=s["key"], name=s["name"], pi=s["pi"], mu=s["mu"], r=s["r"], **truth_summary(s)) for s in SCEN])
    truth.round(6).to_csv(RES / "truth.csv", index=False)
    agg = R.groupby(["scen", "model"]).agg(err_p0=("err_p0", "mean"), err_p2plus=("err_p2plus", "mean"),
                                            err_p3plus=("err_p3plus", "mean"), err_mean=("err_mean", "mean"),
                                            err_var=("err_var", "mean"),
                                            rmse_p2plus=("err_p2plus", lambda v: np.sqrt((v ** 2).mean()))).reset_index()
    agg.round(3).to_csv(RES / "fit_errors_n5000.csv", index=False)
    rate = S.groupby(["scen", "n", "best"]).size().unstack(fill_value=0).reindex(columns=MODELS, fill_value=0) / REPS * 100
    rate.round(2).to_csv(RES / "aic_selection_rate.csv")
    rate = rate.reset_index()

    # 例：場面Cの1回分（5,000契約）の度数
    ex_rng = np.random.default_rng(SEED + 1)
    yC = draw(SCEN[2], MAIN_N, ex_rng)
    cntC = np.bincount(yC)
    pd.DataFrame({"claims": np.arange(len(cntC)), "policies": cntC}).to_csv(DATA / "example_counts_C_n5000.csv", index=False)

    # ---- 図1：場面C（ゼロ過剰）の度数と、4モデルの当てはまり
    fitsC = {m: fit(m, cntC)[0] for m in MODELS}
    K = 4
    obs = [cntC[0], cntC[1], cntC[2] if len(cntC) > 2 else 0, cntC[3:].sum()]
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw=dict(width_ratios=[1, 1.4]))
    ax = axes[0]
    labs = ["0件", "1件", "2件", "3件以上"]
    ax.bar(range(K), obs, color=LIGHT, edgecolor=GRAY, label="データ（5,000契約）")
    for j, m in enumerate(MODELS):
        sm = summarize(fitsC[m]); pr = [sm["p0"], sm["p1"], sm["p2plus"] - sm["p3plus"], sm["p3plus"]]
        ax.plot(np.arange(K) + (j - 1.5) * 0.12, np.array(pr) * MAIN_N, "o", color=MCOL[m], label=m, ms=6)
    ax.set_yscale("log"); ax.set_xticks(range(K)); ax.set_xticklabels(labs)
    ax.set_ylabel("契約の数（対数目盛り）"); ax.set_title("件数ごとの契約の数（場面C）", fontsize=11.5)
    ax.legend(frameon=False, fontsize=8.5)
    ax = axes[1]
    sub = R[R.scen == "ZIP"]
    data = [sub[sub.model == m].err_p2plus.values for m in MODELS]
    bp = ax.boxplot(data, widths=.6, whis=(5, 95), showfliers=False, patch_artist=True, medianprops=dict(color=INK))
    for b, m in zip(bp["boxes"], MODELS):
        b.set_facecolor(MCOL[m]); b.set_alpha(.55)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticklabels(MODELS, fontsize=9.5); ax.set_ylabel("2件以上の契約の割合の誤差（%）")
    ax.set_title("2件以上の事故を起こす契約の割合の見積もり（300回）", fontsize=11.5)
    fig.suptitle("半数が事故を起こさない集団（場面C）を、4つのモデルで当てはめる", fontsize=13, y=1.02)
    save(fig, "a488_fit_zip.png", SRC + "。場面C：半数は事故0件、残りは年平均0.2件のポアソン。左は1回分、右は300回の5〜95%", y=-0.03)

    # ---- 図2：4場面×4モデルの、2件以上の割合の平均誤差
    fig, ax = plt.subplots(figsize=(10, 4.3))
    w = 0.2
    for j, m in enumerate(MODELS):
        v = [agg[(agg.scen == s["key"]) & (agg.model == m)].err_p2plus.iloc[0] for s in SCEN]
        b = ax.bar(np.arange(4) + (j - 1.5) * w, v, w, color=MCOL[m], label=m)
        for x, val in zip(np.arange(4) + (j - 1.5) * w, v):
            ax.text(x, val + (1 if val >= 0 else -1), f"{val:.0f}", ha="center", va="bottom" if val >= 0 else "top", fontsize=7.5)
    ax.axhline(0, color=INK, lw=.8)
    ax.set_xticks(range(4)); ax.set_xticklabels([s["name"].replace("（", "\n（") for s in SCEN], fontsize=9)
    ax.set_ylabel("2件以上の契約の割合の誤差（%、300回の平均）")
    ax.legend(frameon=False, fontsize=9, ncol=4, loc="lower left")
    ax.set_title("2件以上の事故を起こす契約の割合を、どのモデルがどれだけ外すか（5,000契約）")
    save(fig, "a488_p2plus_error.png", SRC + "。正解の割合は " + "、".join(f"{r.name[0]} {r.p2plus * 100:.2f}%" for r in truth.itertuples()))

    # ---- 図3：AIC で正しいモデルを選べた割合
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.9), sharey=True)
    truth_model = dict(P="ポアソン", NB="負の二項", ZIP="ゼロ過剰ポアソン", ZINB="ゼロ過剰負の二項")
    for ax, s in zip(axes, SCEN):
        sub = rate[rate.scen == s["key"]]
        bottom = np.zeros(len(NS))
        for m in MODELS:
            v = sub[m].values
            ax.bar(range(len(NS)), v, bottom=bottom, color=MCOL[m], alpha=1 if m == truth_model[s["key"]] else .35, label=m)
            bottom += v
        ax.set_xticks(range(len(NS))); ax.set_xticklabels([f"{n:,}" for n in NS])
        ax.set_title(s["name"].split("（")[0] + "\n正解は" + truth_model[s["key"]], fontsize=10)
        ax.set_xlabel("契約の数")
    axes[0].set_ylabel("AIC で選ばれたモデル（%）")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=MCOL[m], label=m) for m in MODELS], frameon=False, fontsize=9, ncol=4,
               loc="upper center", bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("AIC（当てはまりの指標）で選ぶと、正しいモデルを何%で選べるか（濃い色が正解、薄い色は別のモデル）", fontsize=12.5, y=1.08)
    save(fig, "a488_aic_selection.png", SRC + "。各300回", y=-0.1)

    main = dict(truth=truth.set_index("scen")[["p0", "p2plus", "p3plus", "mean", "var"]].round(5).to_dict("index"),
                err=agg.set_index(["scen", "model"]).round(2).reset_index().to_dict("records"),
                aic=rate.round(1).to_dict("records"))
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=str)
    print(truth.round(5).to_string()); print(agg.round(2).to_string()); print(rate.round(1).to_string())


if __name__ == "__main__":
    run()
