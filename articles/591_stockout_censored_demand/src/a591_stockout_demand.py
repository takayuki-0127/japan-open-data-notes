"""591 欠品していた日の売上を0と見るか欠測と見るかで、平均の需要はどれだけ少なく見えるのか。
架空の200品目・1年分の日次の需要と在庫（seed 591）。欠品日の売上は「その日の在庫まで」で打ち切られる"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from scipy import stats, optimize
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "出典：架空の日次の需要と在庫（作成者が乱数で作成、seed 591）"
rng = np.random.default_rng(591)
NI, ND, LEAD, K = 200, 365, 3, 4.0       # 品目数・日数・発注から入荷までの日数・需要の負の二項分布のサイズ
days = pd.date_range("2025-01-01", periods=ND, freq="D")

# ---- 1. 品目：平均需要と、在庫の持ち方（安全在庫の係数）を品目ごとに変える ----
lam = np.round(rng.lognormal(np.log(8), 0.7, NI), 2)
z = rng.uniform(-2.0, 1.6, NI)           # 小さいほど欠品しやすい
rows = []
for i in range(NI):
    p = K / (K + lam[i])
    dem = rng.negative_binomial(K, p, ND)
    sd_l = np.sqrt(LEAD * (lam[i] + lam[i] ** 2 / K))
    s_pt = max(1, int(round(lam[i] * LEAD + z[i] * sd_l)))           # 発注点
    S = s_pt + int(round(lam[i] * 7))                                  # 補充後の目標（1週間分を上乗せ）
    stock, pipe = S, {}
    for d in range(ND):
        stock += pipe.pop(d, 0)
        sales = min(dem[d], stock)
        stock -= sales
        rows.append((f"I{i + 1:03d}", d, int(dem[d]), int(sales), int(stock)))
        pos = stock + sum(pipe.values())
        if pos <= s_pt:
            pipe[d + LEAD] = pipe.get(d + LEAD, 0) + (S - pos)
df = pd.DataFrame(rows, columns=["item", "d", "demand", "sales", "end_stock"])
df["date"] = days[df.d.values]
df["stockout"] = df.end_stock == 0
df[["date", "item", "sales", "end_stock"]].assign(stockout=df.stockout).to_csv(DATA / "daily.csv", index=False, date_format="%Y-%m-%d")
df[["date", "item", "demand"]].to_csv(DATA / "true_demand.csv", index=False, date_format="%Y-%m-%d")


# ---- 2. 打ち切りとして推定（負の二項分布の最尤法。欠品日は「需要 ≥ 売上」として扱う） ----
def censored_nb(y, cens):
    yu, yc = y[~cens], y[cens]
    def nll(th):
        mu, k = np.exp(th)
        p = k / (k + mu)
        return -(stats.nbinom.logpmf(yu, k, p).sum() + stats.nbinom.logsf(yc - 1, k, p).sum())
    m0 = max(y.mean(), 0.5)
    r = optimize.minimize(nll, [np.log(m0), np.log(3.0)], method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-8, "maxiter": 4000})
    return float(np.exp(r.x[0]))


g = df.groupby("item")
it = pd.DataFrame({"true_mean": g.demand.mean(), "stockout_rate": g.stockout.mean() * 100,
                   "mean_all": g.sales.mean(),
                   "mean_zero": g.apply(lambda x: np.where(x.stockout, 0, x.sales).mean()),
                   "mean_excl": g.apply(lambda x: x.sales[~x.stockout].mean())})
it["mean_cens"] = [censored_nb(x.sales.values, x.stockout.values) for _, x in g]
for c in ["all", "zero", "excl", "cens"]:
    it[f"err_{c}"] = (it[f"mean_{c}"] / it.true_mean - 1) * 100
it["lost_pct"] = (1 - g.sales.sum() / g.demand.sum()) * 100
it.to_csv(RES / "per_item.csv", float_format="%.4f")

bands = pd.cut(it.stockout_rate, [-0.01, 2, 5, 10, 20, 100], labels=["2%以下", "2〜5%", "5〜10%", "10〜20%", "20%超"])
by_band = it.groupby(bands, observed=False)[["err_all", "err_zero", "err_excl", "err_cens"]].median().round(1)
by_band["n_items"] = it.groupby(bands, observed=False).size()
by_band.to_csv(RES / "by_stockout_band.csv")


def summ(c):
    return {"median": round(float(it[c].median()), 1), "p10": round(float(it[c].quantile(0.1)), 1), "min": round(float(it[c].min()), 1)}


tot = {c: round(float((it[f"mean_{c}"].sum() / it.true_mean.sum() - 1) * 100), 1) for c in ["all", "zero", "excl", "cens"]}
res = {"n_items": NI, "n_days": ND, "stockout_rate_all_pct": round(float(df.stockout.mean() * 100), 1),
       "stockout_rate_items": {"median": round(float(it.stockout_rate.median()), 1), "max": round(float(it.stockout_rate.max()), 1),
                               "n_over_10": int((it.stockout_rate > 10).sum()), "n_zero": int((it.stockout_rate == 0).sum())},
       "lost_sales_pct_total": round(float((1 - df.sales.sum() / df.demand.sum()) * 100), 1),
       "total_err_pct": tot, "item_err": {c: summ(f"err_{c}") for c in ["all", "zero", "excl", "cens"]},
       "by_band_median_err": by_band.reset_index().astype({"stockout_rate": str}).to_dict(orient="records"),
       "items_under_by_5pct": {c: int((it[f"err_{c}"] < -5).sum()) for c in ["all", "zero", "excl", "cens"]}}

# 欠品日の需要は、欠品しなかった日より大きいか（除くと低く出る理由）
so = df[df.stockout]; ns = df[~df.stockout]
rel = (so.demand.values / it.true_mean.reindex(so.item).values).mean(), (ns.demand.values / it.true_mean.reindex(ns.item).values).mean()
res["demand_vs_item_mean_on_stockout_days"] = round(float(rel[0]), 2)
res["demand_vs_item_mean_on_other_days"] = round(float(rel[1]), 2)

# ---- 3. SQL（DuckDB、1スレッド）で3通りの平均を出し、Python と突き合わせる ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE daily AS SELECT * FROM read_csv_auto('{DATA / 'daily.csv'}')")
sq = con.execute((SQL / "02_stockout_duckdb.sql").read_text()).df().set_index("item")
sq.to_csv(RES / "sql_per_item.csv", float_format="%.6f")
res["sql_match_python"] = bool(np.allclose(sq.reindex(it.index)[["mean_all_days", "mean_zero_on_stockout", "mean_excl_stockout"]].values,
                                           it[["mean_all", "mean_zero", "mean_excl"]].values, atol=1e-9)
                               and np.allclose(sq.reindex(it.index).stockout_rate.values * 100, it.stockout_rate.values))
json.dump(res, open(RES / "a591_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 4. 図 ----
lab = {"zero": "欠品日を0", "all": "そのまま平均", "excl": "欠品日を除く", "cens": "打ち切りとして推定"}
col = {"zero": ORANGE, "all": GRAY, "excl": BLUE, "cens": GREEN}
fig, ax = plt.subplots(figsize=(8, 4.4))
x = np.arange(len(by_band)); w = 0.2
for j, c in enumerate(["zero", "all", "excl", "cens"]):
    ax.bar(x + (j - 1.5) * w, by_band[f"err_{c}"], w, color=col[c], label=lab[c])
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(x, [f"{b}\n（{n}品目）" for b, n in zip(by_band.index, by_band.n_items)])
ax.set_xlabel("その品目で欠品した日の割合"); ax.set_ylabel("本当の平均需要とのずれ（%、中央値）")
ax.set_title("欠品の多い品目ほど、平均の需要は少なく見える")
ax.set_ylim(-36, 3); ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower left")
save(fig, "a591_by_band.png", SRC)

fig, ax = plt.subplots(figsize=(7, 5))
for c in ["zero", "excl", "cens"]:
    ax.scatter(it.stockout_rate, it[f"err_{c}"], s=12, color=col[c], alpha=0.7, label=lab[c])
ax.axhline(0, color=INK, lw=0.8)
ax.set_xlabel("欠品した日の割合（%）"); ax.set_ylabel("本当の平均需要とのずれ（%）")
ax.set_title("品目ごとのずれ（200品目）")
ax.legend(frameon=False, fontsize=9)
save(fig, "a591_scatter.png", SRC)

ex = it.sort_values("stockout_rate").index[int(NI * 0.95)]
e = df[(df.item == ex) & (df.d < 120)]
fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(e.date, e.demand, color=GRAY, lw=1, label="本当の需要（データには残らない）")
ax.plot(e.date, e.sales, color=BLUE, lw=1.4, label="売上（記録される数）")
ax.scatter(e.date[e.stockout], e.sales[e.stockout], color=ORANGE, s=18, zorder=3, label="欠品した日")
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%-m/%-d"))
ax.set_ylabel("1日の数量"); ax.set_title(f"欠品した日は、売上が需要より小さく記録される（品目{ex}・1〜4月）")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a591_example.png", SRC)
