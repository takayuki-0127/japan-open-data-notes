"""580 傾向スコアで重みを付けるとき、極端な重みを切り詰めると、偏りとばらつきはどう変わるか（seed 580）"""
import json
import numpy as np, pandas as pd, duckdb
from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(580)
SRC = "架空のデータ（作成者が乱数で作成、seed 580）"
N, SIMS = 2000, 500
GAMMAS = [1.0, 2.0, 3.0]          # 施策を受けるかどうかが x にどれだけ強く結びつくか（大きいほど重なりが少ない）
TRUE_ATE = 1.0                    # 効果は 1 + 0.5x。x の平均は 0 なので、全体の平均効果は 1
METHODS = ["unadjusted", "ipw", "cap99", "cap95", "trim05"]
LAB = {"unadjusted": "重みなし（単純な差）", "ipw": "逆確率の重み（切り詰めなし）", "cap99": "重みを99%点で頭打ち",
       "cap95": "重みを95%点で頭打ち", "trim05": "傾向スコア0.05〜0.95の人だけ残す"}


def make(gamma):
    x = rng.normal(0, 1, N)
    p = 1 / (1 + np.exp(-(-0.5 + gamma * x)))
    t = rng.binomial(1, p)
    y = 1 + 2 * x + (1 + 0.5 * x) * t + rng.normal(0, 1, N)
    return x, t, y


def hajek(y, t, w):
    return np.sum(w * t * y) / np.sum(w * t) - np.sum(w * (1 - t) * y) / np.sum(w * (1 - t))


def estimate(x, t, y):
    ps = LogisticRegression(penalty=None, max_iter=1000).fit(x[:, None], t).predict_proba(x[:, None])[:, 1]
    w = np.where(t == 1, 1 / ps, 1 / (1 - ps))
    out = {"unadjusted": y[t == 1].mean() - y[t == 0].mean(), "ipw": hajek(y, t, w)}
    for k, q in [("cap99", 99), ("cap95", 95)]:
        out[k] = hajek(y, t, np.minimum(w, np.percentile(w, q)))
    keep = (ps >= 0.05) & (ps <= 0.95)
    out["trim05"] = hajek(y[keep], t[keep], w[keep])
    info = {"max_w_share": float(w.max() / w.sum()), "ess": float(w.sum() ** 2 / (w ** 2).sum()),
            "share_outside": float(1 - keep.mean()), "max_w": float(w.max()), "trim_target_ate": float(1 + 0.5 * x[keep].mean())}
    return out, info, ps, w


rows, infos = [], []
example = None
for g in GAMMAS:
    for s in range(SIMS):
        x, t, y = make(g)
        o, inf, ps, w = estimate(x, t, y)
        rows += [{"gamma": g, "sim": s, "method": m, "est": o[m]} for m in METHODS]
        inf.update(gamma=g, sim=s); infos.append(inf)
        if g == 2.0 and s == 0: example = (x, t, y, ps, w)
sim = pd.DataFrame(rows); sim.to_csv(RES / "simulation.csv", index=False)
inf = pd.DataFrame(infos); inf.to_csv(RES / "overlap_info.csv", index=False)
summ = sim.groupby(["gamma", "method"]).est.agg(mean="mean", sd="std").reset_index()
summ["bias"] = summ["mean"] - TRUE_ATE
summ["rmse"] = np.sqrt(summ.bias ** 2 + summ.sd ** 2)
summ.to_csv(RES / "summary.csv", index=False)
ov = inf.groupby("gamma").agg(max_w_share=("max_w_share", "median"), ess=("ess", "median"), share_outside=("share_outside", "median"),
                              max_w=("max_w", "median"), trim_target_ate=("trim_target_ate", "mean")).reset_index()
ov.to_csv(RES / "overlap_summary.csv", index=False)

# 例の1回：DuckDB で重み付きの平均の差を出し直す
x, t, y, ps, w = example
exd = pd.DataFrame({"id": np.arange(N), "x": x.round(6), "treated": t, "y": y.round(6), "ps": ps.round(8)})
DATA.mkdir(exist_ok=True); exd.to_csv(DATA / "example_gamma2.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("units", exd)
sq = con.execute(open(SQL / "a580_ipw.sql", encoding="utf-8").read()).df()
sq.to_csv(RES / "sql_example.csv", index=False)
pr, pw_ = exd.ps.to_numpy(), None
wr = np.where(exd.treated == 1, 1 / pr, 1 / (1 - pr)); keep = (pr >= .05) & (pr <= .95)
py_ipw = hajek(exd.y.to_numpy(), exd.treated.to_numpy(), wr)
py_trim = hajek(exd.y.to_numpy()[keep], exd.treated.to_numpy()[keep], wr[keep])
ok = bool(np.isclose(sq.ipw[0], py_ipw) and np.isclose(sq.trim05[0], py_trim))

# 図1：傾向スコアの分布（例の1回、γ=2）
fig, ax = plt.subplots(figsize=(8, 4))
b = np.linspace(0, 1, 41)
ax.hist(ps[t == 1], bins=b, color=BLUE, alpha=0.6, label="施策を受けた人")
ax.hist(ps[t == 0], bins=b, color=ORANGE, alpha=0.6, label="受けなかった人")
for v in [0.05, 0.95]: ax.axvline(v, color=INK, lw=1, ls="--")
ax.set_xlabel("傾向スコア（施策を受ける確率の推定値）"); ax.set_ylabel("人数"); ax.legend(fontsize=9)
top = np.sort(w)[::-1]
ax.set_title(f"重なりの少ない例：重み最大 {w.max():.0f}、上位5人で重み全体の {top[:5].sum()/w.sum()*100:.1f}%")
save(fig, "a580_ps_dist.png", SRC + "。結びつきγ=2の例の1回、2,000人。点線は0.05と0.95")

# 図2：方法ごとの推定値の分布（γ=1,2,3）
fig, axes = plt.subplots(1, 3, figsize=(14, 4.3), sharey=True)
ms = ["ipw", "cap99", "cap95", "trim05", "unadjusted"]
for ax, g in zip(axes, GAMMAS):
    data = [sim[(sim.gamma == g) & (sim.method == m)].est for m in ms]
    bp = ax.boxplot(data, vert=False, widths=0.6, patch_artist=True, showfliers=False)
    for patch, c in zip(bp["boxes"], [BLUE, GREEN, GREEN, GRAY, ORANGE]): patch.set_facecolor(c); patch.set_alpha(0.5)
    ax.axvline(TRUE_ATE, color=INK, lw=1, ls="--")
    ax.set_title(f"結びつき γ={g:g}"); ax.set_xlabel("推定した平均効果（正解は1）")
    ax.set_xlim(-0.5, 5.5)
axes[0].set_yticks(range(1, len(ms) + 1), [LAB[m] for m in ms], fontsize=9)
save(fig, "a580_estimates.png", SRC + "。各500回、箱は25〜75%、ひげは外れ値を除く範囲。重みなしは図の外に出る場合がある")

# 図3：偏りとばらつき（RMSE）
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for m, c, mk in [("ipw", BLUE, "o"), ("cap99", GREEN, "s"), ("cap95", "#1d6b4f", "^"), ("trim05", GRAY, "D")]:
    s = summ[summ.method == m]
    axes[0].plot(s.gamma, s.bias, mk + "-", color=c, label=LAB[m]); axes[1].plot(s.gamma, s.sd, mk + "-", color=c, label=LAB[m])
axes[0].axhline(0, color=INK, lw=0.8); axes[0].set_title("偏り（平均−正解）"); axes[1].set_title("ばらつき（標準偏差）")
for ax in axes: ax.set_xticks(GAMMAS); ax.set_xlabel("結びつき γ（大きいほど重なりが少ない）")
axes[0].legend(fontsize=8.5)
save(fig, "a580_bias_sd.png", SRC + "。各500回")

main = {"n": N, "sims": SIMS, "true_ate": TRUE_ATE, "sql_matches_python": ok,
        "summary": summ.round(4).to_dict(orient="records"), "overlap": ov.round(4).to_dict(orient="records")}
json.dump(main, open(RES / "a580_main.json", "w"), ensure_ascii=False, indent=1)
print(summ.round(3).to_string()); print(ov.round(3).to_string()); print("sql ok", ok)
