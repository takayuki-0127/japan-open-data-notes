"""590 比率の分母が小さい項目を並べると、上位と下位にどれだけ小さい項目が集まるか（seed 590）"""
import json
import numpy as np, pandas as pd, duckdb
from scipy import stats, optimize, special
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(590)
SRC = "架空のデータ（作成者が乱数で作成、seed 590）"
K, TOP, REPS, P0 = 300, 10, 500, 0.05
METH = {"raw": "そのままの率", "eb": "縮める推定（ベータ・二項）", "wilson": "信頼区間の下限（ウィルソン）"}


def sizes():
    return np.round(np.exp(rng.uniform(np.log(20), np.log(5000), K))).astype(int)   # 来店客数 20〜5,000人


def eb(y, n):
    """ベータ分布を事前分布にした縮める推定。事前の a, b は全項目の y, n から最尤で決める"""
    def nll(p):
        a, b = np.exp(p)
        return -(special.betaln(y + a, n - y + b) - special.betaln(a, b)).sum()
    m = y.sum() / n.sum()
    r = optimize.minimize(nll, [np.log(m * 50), np.log((1 - m) * 50)], method="Nelder-Mead", options={"maxiter": 3000})
    a, b = np.exp(r.x)
    return (y + a) / (n + a + b)


def wilson_low(y, n, z=1.96):
    p = y / n
    return (p + z * z / (2 * n) - z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def run(sd):
    n = sizes(); small = n < np.quantile(n, 0.2)
    if sd == 0:
        p = np.full(K, P0)
    else:                                     # 本当の率がばらつく（平均5%、標準偏差 sd）
        m, v = P0, sd ** 2; k = m * (1 - m) / v - 1
        p = rng.beta(m * k, (1 - m) * k, K)
    y = rng.binomial(n, p)
    sc = {"raw": y / n, "eb": eb(y, n), "wilson": wilson_low(y, n)}
    out = {"n_small_cut": float(np.quantile(n, 0.2))}
    true_top = set(np.argsort(-p)[:TOP]) if sd > 0 else set()
    for k_, s in sc.items():
        o = np.argsort(-s, kind="stable")
        top, bot = o[:TOP], o[-TOP:]
        out[k_ + "_small_top"] = float(small[top].mean()); out[k_ + "_small_bot"] = float(small[bot].mean())
        out[k_ + "_median_n_top"] = float(np.median(n[top]))
        if sd > 0:
            out[k_ + "_hit_top"] = len(true_top & set(top)) / TOP
            out[k_ + "_rho"] = float(stats.spearmanr(s, p)[0])
    return out


rows = []
for sd in [0.0, 0.01, 0.02]:
    for r in range(REPS):
        rows.append({"sd": sd, "rep": r, **run(sd)})
sim = pd.DataFrame(rows); sim.to_csv(RES / "simulation.csv", index=False)
summ = sim.groupby("sd").mean(numeric_only=True).drop(columns="rep").round(4).reset_index()
summ.to_csv(RES / "summary.csv", index=False)

# 例の1回（本当の率はすべて5%）
n = sizes(); y = rng.binomial(n, P0)
ex = pd.DataFrame({"store": [f"S{i:03d}" for i in range(K)], "visitors": n, "buyers": y})
ex.to_csv(DATA / "example_stores.csv", index=False)
p_all = y.sum() / n.sum(); lim = 1.96 * np.sqrt(p_all * (1 - p_all) / n)
out_py = int(((y / n > p_all + lim) | (y / n < p_all - lim)).sum())
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("stores", ex)
sq = con.execute(open(SQL / "a590_funnel.sql").read()).df()
out_sql = int(sq.outside.sum())
pd.DataFrame([{"overall_rate": p_all, "outside_python": out_py, "outside_duckdb": out_sql, "match": out_py == out_sql,
               "top10_median_visitors": float(np.median(n[np.argsort(-(y / n), kind='stable')[:TOP]])),
               "bottom10_median_visitors": float(np.median(n[np.argsort(-(y / n), kind='stable')[-TOP:]])),
               "median_visitors_all": float(np.median(n))}]).to_csv(RES / "sql_example.csv", index=False)

# 図1 漏斗図（例の1回）
rate = y / n; o = np.argsort(-rate, kind="stable")
fig, ax = plt.subplots(figsize=(9, 5))
xs = np.exp(np.linspace(np.log(18), np.log(5200), 200)); l = 1.96 * np.sqrt(p_all * (1 - p_all) / xs)
ax.plot(xs, (p_all + l) * 100, color=GRAY, lw=1); ax.plot(xs, np.maximum(p_all - l, 0) * 100, color=GRAY, lw=1)
ax.axhline(p_all * 100, color=INK, lw=0.8)
ax.scatter(n, rate * 100, s=10, color=GRAY, alpha=0.6, label="ほかの店")
ax.scatter(n[o[:TOP]], rate[o[:TOP]] * 100, s=28, color=ORANGE, label="率の上位10店")
ax.scatter(n[o[-TOP:]], rate[o[-TOP:]] * 100, s=28, color=BLUE, label="率の下位10店")
ax.set_xscale("log"); ax.set_xlabel("来店客数（対数目盛）"); ax.set_ylabel("購入率（%）"); ax.legend(fontsize=9); ax.grid(alpha=0.3)
ax.set_title("本当の率はどの店も5%：それでも上位と下位は来店客数の少ない店ばかり")
save(fig, "a590_funnel.png", "出典：" + SRC + "。灰色の線は全体の率±1.96標準誤差（漏斗の線）")

# 図2 上位10・下位10に入った「小さい店」（来店客数の下位20%）の割合
fig, axs = plt.subplots(1, 3, figsize=(12, 4.3), sharey=True)
for ax, sd, ttl in zip(axs, [0.0, 0.01, 0.02], ["本当の率はすべて5%", "本当の率がばらつく（標準偏差1%）", "本当の率がばらつく（標準偏差2%）"]):
    g = summ[summ.sd == sd].iloc[0]; xx = np.arange(3)
    ax.bar(xx - 0.18, [g[k + "_small_top"] * 100 for k in METH], 0.36, color=ORANGE, label="上位10に入った割合")
    ax.bar(xx + 0.18, [g[k + "_small_bot"] * 100 for k in METH], 0.36, color=BLUE, label="下位10に入った割合")
    ax.axhline(20, color=INK, lw=0.8, ls=":")
    ax.set_xticks(xx); ax.set_xticklabels(["そのまま", "縮める推定", "区間の下限"], fontsize=9); ax.set_title(ttl, fontsize=10); ax.grid(axis="y", alpha=0.3)
axs[0].set_ylabel("小さい店（来店客数の下位20%）の割合（%）"); axs[0].set_ylim(0, 100)
h_, l_ = axs[0].get_legend_handles_labels(); fig.legend(h_, l_, fontsize=9, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.07), frameon=False)
fig.suptitle("上位・下位10店に占める小さい店の割合（各500回の平均。点線は全体での割合20%）", fontsize=12, y=1.03)
save(fig, "a590_small_share.png", "出典：" + SRC, y=-0.1)

# 図3 本当の上位10店をどれだけ当てたか
fig, ax = plt.subplots(figsize=(9, 4.3))
xx = np.arange(2)
for j, (k, c) in enumerate(zip(METH, [GRAY, GREEN, BLUE])):
    v = [summ[summ.sd == sd].iloc[0][k + "_hit_top"] * 10 for sd in [0.01, 0.02]]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=c, label=METH[k])
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv + 0.08, f"{vv:.1f}", ha="center", fontsize=9)
ax.set_xticks(xx); ax.set_xticklabels(["本当の率の標準偏差1%", "本当の率の標準偏差2%"]); ax.set_ylabel("本当の上位10店のうち当たった数")
ax.set_ylim(0, 10); ax.legend(fontsize=9); ax.grid(axis="y", alpha=0.3); ax.set_title("並べた上位10店のうち、本当に上位10店だった数（各500回の平均）")
save(fig, "a590_hits.png", "出典：" + SRC)

json.dump({"summary": summ.to_dict("records"), "sql": pd.read_csv(RES / "sql_example.csv").to_dict("records")},
          open(RES / "a590_main.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250); print(summ.T.to_string()); print(pd.read_csv(RES / "sql_example.csv").T.to_string())
