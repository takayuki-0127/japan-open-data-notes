"""600 過去の年の損害から分布を推定するとき、推定の誤差を入れないと 99.5%点はどれだけ小さく出るか（seed 600）"""
import json
import numpy as np, pandas as pd, duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(600)
SRC = "架空のデータ（作成者が乱数で作成、seed 600）"
MU = np.log(10000)                       # 年間の総損害：対数正規、中央値1億円（単位：万円）
Z = stats.norm.ppf(0.995)
NS, SIGS, REPS, BREPS, B = [5, 10, 20, 50], [0.2, 0.4, 0.6], 20000, 2000, 2000
METH = {"plugin": "推定値をそのまま使う", "boot": "パラメトリック・ブートストラップ", "bayes": "ベイズの予測分布"}


def estimates(logx):
    n = logx.shape[-1]
    m = logx.mean(-1); s_mle = logx.std(-1); s = logx.std(-1, ddof=1)
    return m, s_mle, s


rows = []
for sig in SIGS:
    q_true = np.exp(MU + Z * sig)
    for n in NS:
        lx = rng.normal(MU, sig, (REPS, n))
        m, s_mle, s = estimates(lx)
        q_plug = np.exp(m + Z * s_mle)
        q_bayes = np.exp(m + s * np.sqrt(1 + 1 / n) * stats.t.ppf(0.995, n - 1))
        # パラメトリック・ブートストラップ（計算量のため最初の BREPS 回だけ）
        mb, sb = m[:BREPS], s_mle[:BREPS]
        lb = rng.normal(mb[:, None, None], sb[:, None, None], (BREPS, B, n))
        m2, s2, _ = estimates(lb)
        fut = rng.normal(m2, s2)                                     # 推定し直した分布から、次の1年を1つずつ引く
        q_boot = np.exp(np.quantile(fut, 0.995, axis=1))
        exc = lambda q: 1 - stats.norm.cdf((np.log(q) - MU) / sig)   # 本当に超える確率
        rows.append({"sigma": sig, "n_years": n, "q_true": q_true,
                     "plugin_exceed": exc(q_plug).mean(), "bayes_exceed": exc(q_bayes).mean(), "boot_exceed": exc(q_boot).mean(),
                     "plugin_exceed_first": exc(q_plug[:BREPS]).mean(),
                     "plugin_ratio_median": np.median(q_plug / q_true), "plugin_below_true_share": (q_plug < q_true).mean(),
                     "plugin_ratio_p10": np.quantile(q_plug / q_true, 0.1), "plugin_ratio_p90": np.quantile(q_plug / q_true, 0.9),
                     "bayes_over_plugin_median": np.median(q_bayes / q_plug), "boot_over_plugin_median": np.median(q_boot / q_plug[:BREPS])})
tab = pd.DataFrame(rows); tab.round(6).to_csv(RES / "summary.csv", index=False)

# 例：10年分のデータ（σ 0.4）で、3つの99.5%点を出し、SQL（DuckDB）で数え直す
x = np.round(np.exp(rng.normal(MU, 0.4, 10)), 1)
ex = pd.DataFrame({"year": range(2016, 2026), "total_loss": x}); ex.to_csv(DATA / "annual_losses.csv", index=False)
lx = np.log(x); m, s_mle, s = lx.mean(), lx.std(), lx.std(ddof=1)
t995 = stats.t.ppf(0.995, 9)
py = {"mu_hat": m, "sigma_mle": s_mle, "q_plugin": np.exp(m + Z * s_mle), "q_bayes": np.exp(m + s * np.sqrt(1 + 1 / 10) * t995)}
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("annual_losses", ex)
con.register("params", pd.DataFrame({"z995": [Z], "t995_df9": [t995]}))
sq = con.execute(open(SQL / "02_quantile_duckdb.sql").read()).df().iloc[0]
chk = {**{k: float(v) for k, v in py.items()}, **{k + "_duckdb": float(sq[k]) for k in py},
       "q_true": float(np.exp(MU + Z * 0.4)), "match": all(np.isclose(py[k], sq[k], rtol=1e-10) for k in py)}
pd.DataFrame([chk]).to_csv(RES / "sql_example.csv", index=False)

# 図1 本当に超える確率（σ 0.4）
s4 = tab[tab.sigma == 0.4]
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for k, col, mk in zip(METH, [ORANGE, GREEN, BLUE], ["o", "s", "^"]):
    ax.plot(s4.n_years, s4[k + "_exceed"] * 100, marker=mk, color=col, label=METH[k])
    for xv, yv in zip(s4.n_years, s4[k + "_exceed"] * 100): ax.text(xv * (1.07 if k == "boot" else 1), yv + {"plugin": 0.15, "boot": -0.05, "bayes": -0.4}[k], f"{yv:.2f}", ha="center", fontsize=8, color=col)
ax.axhline(0.5, color=INK, lw=0.8, ls=":"); ax.text(5.2, 0.6, "目標の0.5%", ha="left", fontsize=8.5)
ax.set_xscale("log"); ax.set_xticks(NS); ax.set_xticklabels([f"{n}年" for n in NS]); ax.set_xlabel("推定に使ったデータの年数")
ax.set_ylabel("翌年の損害が99.5%点を本当に超える確率（%）"); ax.set_ylim(0, 6); ax.xaxis.set_minor_locator(plt.NullLocator()); ax.grid(alpha=0.3); ax.legend(fontsize=9)
ax.set_title("推定値をそのまま使った99.5%点は、200年に1度ではなく、もっと頻繁に超える")
save(fig, "a600_exceed.png", "出典：" + SRC + "。年間の総損害は対数正規（σ 0.4）。各2万回（ブートストラップは2,000回）")

# 図2 推定した99.5%点のばらつき（10年分、σ 0.4）
lx = rng.normal(MU, 0.4, (REPS, 10)); m, s_mle, s = estimates(lx)
r_plug = np.exp(m + Z * s_mle) / np.exp(MU + Z * 0.4); r_bayes = np.exp(m + s * np.sqrt(1.1) * t995) / np.exp(MU + Z * 0.4)
fig, ax = plt.subplots(figsize=(9.5, 4.6)); bins = np.linspace(0.3, 2.6, 70)
ax.hist(r_plug, bins=bins, color=ORANGE, alpha=0.6, label=f"推定値をそのまま使う（中央値 {np.median(r_plug):.2f}）")
ax.hist(r_bayes, bins=bins, color=BLUE, alpha=0.45, label=f"ベイズの予測分布（中央値 {np.median(r_bayes):.2f}）")
ax.axvline(1, color=INK, lw=1); ax.text(1.02, ax.get_ylim()[1] * 0.92, "本当の99.5%点", fontsize=8.5)
ax.set_xlabel("推定した99.5%点 ÷ 本当の99.5%点"); ax.set_ylabel("回数（2万回）"); ax.grid(alpha=0.3); ax.legend(fontsize=9)
ax.set_title(f"10年分から推定した99.5%点は大きくぶれ、そのまま使うと{(r_plug < 1).mean() * 100:.0f}%の回で本当より小さい")
save(fig, "a600_spread.png", "出典：" + SRC + "。σ 0.4")

# 図3 誤差を入れると、99.5%点は何%大きくなるか（年数 × σ）
fig, ax = plt.subplots(figsize=(9.5, 4.6)); xx = np.arange(len(NS))
for j, (sig, col) in enumerate(zip(SIGS, [GREEN, BLUE, ORANGE])):
    v = [(tab[(tab.sigma == sig) & (tab.n_years == n)].iloc[0].bayes_over_plugin_median - 1) * 100 for n in NS]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=col, label=f"年ごとのばらつき σ {sig}")
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv + 1, f"{vv:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(xx); ax.set_xticklabels([f"{n}年" for n in NS]); ax.set_xlabel("推定に使ったデータの年数")
ax.set_ylabel("ベイズの予測分布の99.5%点 ÷ 推定値そのまま − 1（%）"); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9)
ax.set_title("データが短く、年ごとのばらつきが大きいほど、誤差を入れた分の上乗せが大きい")
save(fig, "a600_markup.png", "出典：" + SRC + "。2万回の中央値")

json.dump({"summary": tab.round(6).to_dict("records"), "example": chk,
           "n10_sigma04": {"plugin_median_ratio": float(np.median(r_plug)), "plugin_below_share": float((r_plug < 1).mean()),
                           "bayes_median_ratio": float(np.median(r_bayes)), "bayes_below_share": float((r_bayes < 1).mean())}},
          open(RES / "a600_main.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 250); print(tab.round(4).to_string()); print(chk)
print(np.median(r_plug), (r_plug < 1).mean(), np.median(r_bayes), (r_bayes < 1).mean())
