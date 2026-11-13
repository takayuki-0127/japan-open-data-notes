"""597 年間の総損害を件数×金額の複合分布で作るとき、件数の年ごとの揺れを無視すると 99.5%点はどれだけ小さく出るか（seed 597）"""
import json
import numpy as np, pandas as pd, duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(597)
SRC = "架空のデータ（作成者が乱数で作成、seed 597）"
SEV_MEAN, SEV_CV = 100.0, 2.0                       # 1件の損害額：平均100万円、変動係数2の対数正規
SIG = np.sqrt(np.log(1 + SEV_CV ** 2)); MU = np.log(SEV_MEAN) - SIG ** 2 / 2
LAMS, CVS, QS = [20, 100, 500], [0.1, 0.2, 0.3], [0.9, 0.99, 0.995]
N = 2 ** 20


def agg_dist(lam, c):
    """FFT で年間の総損害の分布を出す。c = 0 は複合ポアソン、c > 0 は件数が負の二項（ガンマで混ぜたポアソン）"""
    top = max(lam * SEV_MEAN * (1 + 12 * np.sqrt((1 + SEV_CV ** 2) / lam + c ** 2)), stats.lognorm.ppf(1 - 1e-8, SIG, scale=np.exp(MU)))
    h = top / N
    edges = (np.arange(N + 1) - 0.5) * h; edges[0] = 0
    f = np.diff(stats.lognorm.cdf(edges, SIG, scale=np.exp(MU))); f[-1] += 1 - f.sum()     # 丸めて格子に置く
    phi = np.fft.rfft(f)
    if c == 0:
        g = np.exp(lam * (phi - 1))
    else:
        r, beta = 1 / c ** 2, lam * c ** 2
        g = (1 - beta * (phi - 1)) ** (-r)
    p = np.maximum(np.fft.irfft(g, N), 0)
    return np.arange(N) * h, p / p.sum()


def quant(x, p, q):
    return float(x[np.searchsorted(np.cumsum(p), q)])


rows = []
for lam in LAMS:
    for c in [0.0] + CVS:
        x, p = agg_dist(lam, c)
        m = float((x * p).sum()); sd = float(np.sqrt(((x - m) ** 2 * p).sum()))
        rows.append({"lam": lam, "cv_count": c, "mean": m, "sd": sd, **{f"q{q}": quant(x, p, q) for q in QS}})
tab = pd.DataFrame(rows)
base = tab[tab.cv_count == 0].set_index("lam")
# 件数の揺れが本当にあるとき、複合ポアソンの99.5%点を超える本当の確率
ex_p = []
for lam in LAMS:
    for c in [0.0] + CVS:
        x, p = agg_dist(lam, c)
        ex_p.append(float(p[x > base.loc[lam, "q0.995"]].sum()))
tab["true_exceed_of_poisson_q995"] = ex_p
for q in QS:
    tab[f"ratio_q{q}"] = tab.apply(lambda r: r[f"q{q}"] / base.loc[r.lam, f"q{q}"], axis=1)
tab.round(4).to_csv(RES / "quantiles.csv", index=False)

# 10年分の件数から、揺れ（ポアソンより大きい散らばり）に気づけるか：分散の指数による検定（5%水準）
pw = []
for lam in LAMS:
    for c in [0.0] + CVS:
        m = rng.gamma(1 / c ** 2, c ** 2, (20000, 10)) if c > 0 else np.ones((20000, 10))
        n = rng.poisson(lam * m)
        d = ((n - n.mean(1, keepdims=True)) ** 2).sum(1) / n.mean(1)
        cv_hat = np.sqrt(np.maximum(n.var(1, ddof=1) - n.mean(1), 0)) / n.mean(1)
        pw.append({"lam": lam, "cv_count": c, "detect_rate": float((d > stats.chi2.ppf(0.95, 9)).mean()),
                   "cv_hat_median": float(np.median(cv_hat)), "cv_hat_zero_share": float((cv_hat == 0).mean())})
power = pd.DataFrame(pw); power.round(4).to_csv(RES / "dispersion_test.csv", index=False)

# 例：年100件・揺れ20% をシミュレーションでも作り、SQL（DuckDB）で 99.5%点を数え直す
Y = 200000
def sim(lam, c):
    n = rng.poisson(lam * (rng.gamma(1 / c ** 2, c ** 2, Y) if c > 0 else np.ones(Y)))
    tot = np.zeros(Y); idx = np.repeat(np.arange(Y), n)
    np.add.at(tot, idx, rng.lognormal(MU, SIG, n.sum()))
    return n, tot
rec = []
for name, c in [("poisson", 0.0), ("negbin", 0.2)]:
    n, tot = sim(100, c)
    rec.append(pd.DataFrame({"model": name, "year_id": np.arange(Y), "claim_count": n, "total_loss": np.round(tot, 2)}))
simdf = pd.concat(rec, ignore_index=True)
for name, d in simdf.groupby("model"):
    d.to_csv(DATA / f"simulated_years_{name}.csv", index=False)       # 10MB を超えないようモデル別に分ける
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("simulated_years", simdf)
sq = con.execute(open(SQL / "02_quantile_duckdb.sql").read()).df().set_index("model")
chk = []
for name, c in [("poisson", 0.0), ("negbin", 0.2)]:
    s = simdf[simdf.model == name]
    r = tab[(tab.lam == 100) & (tab.cv_count == c)].iloc[0]
    chk.append({"model": name, "q995_fft": r["q0.995"], "q995_sim_python": float(np.quantile(s.total_loss, 0.995)),
                "q995_sim_duckdb": float(sq.loc[name, "q995"]), "mean_sim": float(s.total_loss.mean()),
                "count_var_over_mean": float(s.claim_count.var() / s.claim_count.mean()),
                "count_var_over_mean_duckdb": float(sq.loc[name, "count_var_over_mean"])})
chk = pd.DataFrame(chk); chk["py_sql_match"] = np.isclose(chk.q995_sim_python, chk.q995_sim_duckdb, rtol=1e-9)
chk.to_csv(RES / "sql_check.csv", index=False)

# 図1 年100件：総損害の上側の確率（対数目盛）
fig, ax = plt.subplots(figsize=(9.5, 4.8))
for c, col, lab in [(0.0, BLUE, "複合ポアソン（件数の揺れを無視）"), (0.2, ORANGE, "複合負の二項（件数の揺れ20%）")]:
    x, p = agg_dist(100, c); sf = 1 - np.cumsum(p)
    ax.plot(x / 100, sf, color=col, lw=1.6, label=lab)
    qv = tab[(tab.lam == 100) & (tab.cv_count == c)].iloc[0]["q0.995"]
    ax.axvline(qv / 100, color=col, ls=":", lw=1)
    ax.text(qv / 100 + (4 if c else -4), 0.3 if c else 0.05, f"99.5%点\n{qv / 100:,.0f}百万円", color=col, fontsize=9, va="top", ha="left" if c else "right")
ax.axhline(0.005, color=GRAY, lw=0.8)
ax.set_yscale("log"); ax.set_ylim(1e-4, 1); ax.set_xlim(0, 400)
ax.set_xlabel("年間の総損害（百万円）"); ax.set_ylabel("これを超える確率（対数目盛）"); ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="lower left")
ax.set_title("年100件・1件平均100万円：平均は同じ1億円でも、上側の裾が違う")
save(fig, "a597_tail.png", "出典：" + SRC + "。1件の損害額は平均100万円・変動係数2の対数正規。FFT で計算")

# 図2 99.5%点が何%小さく出るか（件数の期待値・揺れの大きさ別）
fig, ax = plt.subplots(figsize=(9.5, 4.6)); xx = np.arange(len(LAMS))
for j, (c, col) in enumerate(zip(CVS, [GREEN, ORANGE, BLUE])):
    v = [(1 - 1 / tab[(tab.lam == l) & (tab.cv_count == c)].iloc[0]["ratio_q0.995"]) * 100 for l in LAMS]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=col, label=f"件数の揺れ {int(c * 100)}%")
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv + 0.4, f"{vv:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(xx); ax.set_xticklabels([f"年{l}件" for l in LAMS]); ax.set_xlabel("1年の件数の期待値")
ax.set_ylabel("複合ポアソンの99.5%点が小さく出る割合（%）"); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9)
ax.set_title("件数が多い会社ほど、件数の揺れを無視したときの不足が大きい")
save(fig, "a597_shortfall.png", "出典：" + SRC + "。不足の割合 = 1 − 複合ポアソンの99.5%点 ÷ 複合負の二項の99.5%点")

# 図3 10年分の件数で揺れに気づける割合
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for l, col in zip(LAMS, [GRAY, ORANGE, BLUE]):
    s = power[power.lam == l]
    ax.plot(s.cv_count * 100, s.detect_rate * 100, marker="o", color=col, label=f"年{l}件")
    for xv, yv in zip(s.cv_count * 100, s.detect_rate * 100): ax.text(xv, yv + 2.5, f"{yv:.0f}", ha="center", fontsize=8, color=col)
ax.axhline(5, color=INK, lw=0.8, ls=":")
ax.set_xticks([0, 10, 20, 30]); ax.set_xlabel("本当の件数の揺れ（%）"); ax.set_ylabel("10年分で「揺れあり」と出る割合（%）")
ax.set_ylim(0, 105); ax.grid(alpha=0.3); ax.legend(fontsize=9)
ax.set_title("10年分の件数で、ポアソンより大きい揺れに気づける割合（5%水準、各2万回）")
save(fig, "a597_detect.png", "出典：" + SRC + "。分散の指数（Σ(件数−平均)²／平均）を自由度9のカイ二乗分布と比べた。点線は5%")

json.dump({"quantiles": tab.round(4).to_dict("records"), "dispersion": power.round(4).to_dict("records"), "check": chk.to_dict("records")},
          open(RES / "a597_main.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); print(tab.round(3).to_string()); print(power.to_string()); print(chk.T.to_string())
