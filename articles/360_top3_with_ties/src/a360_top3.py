"""360 「上位3件」を取る SQL は、同じ点数があると何件返すのか（架空の店別・商品別売上）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import SQL, RES, save, BLUE, ORANGE, GRAY, GREEN, INK, LIGHT

SEED = 360
SRC = "架空の店別・商品別の売上（作成者が乱数で作成、seed 360）"
N_STORE, N_PROD = 300, 40
Q1 = (SQL / "01_top3_duckdb.sql").read_text(encoding="utf-8")
Q2 = (SQL / "02_row_number_only_duckdb.sql").read_text(encoding="utf-8")


def make(mean_units, seed):
    """店×商品の1か月の販売数。商品の人気に差をつけ、店ごとの揺れはポアソン"""
    r = np.random.default_rng([SEED, seed])
    pop = r.dirichlet(np.full(N_PROD, 1.2)) * N_PROD                    # 商品の人気（平均1）
    price = r.integers(3, 40, N_PROD) * 100 - 20                         # 単価（280〜3,880円）
    size = r.lognormal(0, 0.4, N_STORE)                                   # 店の大きさ
    lam = mean_units * np.outer(size, pop)
    units = r.poisson(lam)
    df = pd.DataFrame({"store_id": np.repeat(np.arange(1, N_STORE + 1), N_PROD), "product_id": np.tile(np.arange(1, N_PROD + 1), N_STORE),
                       "units": units.ravel()})
    df["amount"] = df["units"] * price[df["product_id"].values - 1]
    return df


def q(df, sql, threads=1):
    con = duckdb.connect(); con.execute(f"SET threads={threads}")
    con.register("d_df", df); con.execute("CREATE TABLE store_sales AS SELECT * FROM d_df")
    out = con.execute(sql).df(); con.close(); return out


def tie_stats(df, col="units"):
    """3位と4位が同じ値の店の割合など（pandas で別に計算）"""
    out = []
    for s, g in df.groupby("store_id"):
        v = np.sort(g[col].values)[::-1]
        out.append({"store_id": s, "tie_at_cut": v[2] == v[3], "n_rank": int((v >= v[2]).sum()),
                    "n_dense": int((v >= np.unique(v)[::-1][2]).sum()), "tie_in_top3": len(set(v[:3])) < 3})
    return pd.DataFrame(out)


# ---------- ① 基本の場面：1商品あたり月に平均12個 ----------
base = make(12, 0)
res = q(base, Q1)
ts = tie_stats(base)
assert (res["n_rank"].values == ts["n_rank"].values).all() and (res["n_dense_rank"].values == ts["n_dense"].values).all()
assert (res["n_row_number"] == 3).all() and (res["n_row_number_tiebreak"] == 3).all()
dist = pd.DataFrame({"返った件数": ["3件", "4件", "5件", "6件以上"]})
for name, col in [("ROW_NUMBER", "n_row_number"), ("RANK（TOP 3 WITH TIES と同じ）", "n_rank"), ("DENSE_RANK", "n_dense_rank")]:
    c = res[col].clip(upper=6).value_counts()
    dist[name] = [int(c.get(k, 0)) for k in (3, 4, 5, 6)]
dist.to_csv(RES / "rows_returned_distribution.csv", index=False)
r1 = {"stores": N_STORE, "products": N_PROD, "tie_at_cut_pct": float(ts["tie_at_cut"].mean() * 100),
      "rank_more_than3_pct": float((res["n_rank"] > 3).mean() * 100), "rank_max": int(res["n_rank"].max()), "rank_total_rows": int(res["n_rank"].sum()),
      "dense_more_than3_pct": float((res["n_dense_rank"] > 3).mean() * 100), "dense_max": int(res["n_dense_rank"].max()),
      "dense_mean": float(res["n_dense_rank"].mean()), "dense_total_rows": int(res["n_dense_rank"].sum()), "row_number_total_rows": int(res["n_row_number"].sum())}

# ---------- ② ROW_NUMBER の顔ぶれ：表に入っている順だけを変えて20回 ----------
sets = []
for i in range(20):
    sh = base.sample(frac=1, random_state=SEED + i)
    o = q(sh, Q2, threads=1 if i < 10 else 2)
    sets.append(o.groupby("store_id")["product_id"].apply(frozenset))
sets = pd.concat(sets, axis=1); sets.columns = range(20)
n_variants = sets.apply(lambda r: len(set(r)), axis=1)
unstable = n_variants > 1
# 同点の決まり（商品番号の小さい順）を書いた版は、20回とも同じか
Q4 = "SELECT store_id, product_id FROM (SELECT store_id, product_id, ROW_NUMBER() OVER (PARTITION BY store_id ORDER BY units DESC, product_id) AS rn FROM store_sales) AS t WHERE rn <= 3"
s4 = pd.concat([q(base.sample(frac=1, random_state=SEED + i), Q4, threads=1 if i < 10 else 2).groupby("store_id")["product_id"].apply(frozenset) for i in range(20)], axis=1)
# 下流：「上位3件に入った店の数」を商品ごとに数えると、実行によってどれだけ違うか
cnts = pd.DataFrame({i: pd.Series([p for fs in sets[c] for p in fs]).value_counts() for i, c in enumerate(sets.columns)}).fillna(0)
spread = (cnts.max(axis=1) - cnts.min(axis=1))
r2 = {"runs": 20, "unstable_stores_pct": float(unstable.mean() * 100), "unstable_equals_tie_at_cut": bool((unstable.values == ts["tie_at_cut"].values).all()),
      "unstable_among_tie_at_cut_pct": float(unstable.values[ts["tie_at_cut"].values].mean() * 100),
      "max_variants_per_store": int(n_variants.max()), "tiebreak_unstable_stores": int((s4.apply(lambda r: len(set(r)), axis=1) > 1).sum()),
      "products_count_changes": int((spread > 0).sum()), "max_spread_stores": int(spread.max()),
      "max_spread_product_min": int(cnts.loc[spread.idxmax()].min()), "max_spread_product_max": int(cnts.loc[spread.idxmax()].max())}

# ---------- ③ 数の大きさと、何で並べるかを変える ----------
sw = []
for mu in [3, 6, 12, 25, 50, 100, 300]:
    for rep in range(5):
        d = make(mu, 100 + rep)
        t = tie_stats(d); ta = tie_stats(d, "amount")
        sw.append({"mean_units": mu, "rep": rep, "tie_at_cut_units": t["tie_at_cut"].mean() * 100, "rank_rows": t["n_rank"].mean(),
                   "dense_rows": t["n_dense"].mean(), "tie_at_cut_amount": ta["tie_at_cut"].mean() * 100})
sw = pd.DataFrame(sw).groupby("mean_units").mean(numeric_only=True).drop(columns="rep").reset_index()
sw.round(2).to_csv(RES / "ties_by_volume.csv", index=False)

# ---------- 例：1つの店 ----------
ex_store = int(ts[(ts["n_rank"] == 5)]["store_id"].iloc[0]) if (ts["n_rank"] == 5).any() else int(ts[ts["tie_at_cut"]]["store_id"].iloc[0])
g = base[base["store_id"] == ex_store].sort_values(["units", "product_id"], ascending=[False, True]).head(8).copy()
g["rn"] = np.arange(1, len(g) + 1)
g["rk"] = g["units"].rank(method="min", ascending=False).astype(int)
g["dr"] = g["units"].rank(method="dense", ascending=False).astype(int)
g.to_csv(RES / "example_store.csv", index=False)

# ---------- 図 ----------
fig, ax = plt.subplots(figsize=(9, 4.0))
x = np.arange(4); bw = 0.27
for i, (name, c) in enumerate(zip(["ROW_NUMBER", "RANK（TOP 3 WITH TIES と同じ）", "DENSE_RANK"], [GRAY, BLUE, ORANGE])):
    ax.bar(x + (i - 1) * bw, dist[name], bw, color=c, label=name)
    for xi, v in zip(x + (i - 1) * bw, dist[name]):
        if v: ax.text(xi, v + 3, str(v), ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(dist["返った件数"]); ax.set_ylabel(f"店の数（{N_STORE}店中）"); ax.set_xlabel("「上位3件」として返った件数")
ax.set_title("同じ「上位3件」でも、関数によって返る件数が違う"); ax.legend(frameon=False)
save(fig, "a360_rows_returned.png", SRC)

fig, ax = plt.subplots(figsize=(9, 3.4)); ax.axis("off")
cells = [[f"商品{int(r.product_id)}", f"{int(r.units)}", str(r.rn), str(r.rk), str(r.dr)] for r in g.itertuples()]
tb = ax.table(cellText=cells, colLabels=["商品", "販売数", "ROW_NUMBER", "RANK", "DENSE_RANK"], loc="center", cellLoc="center", colWidths=[0.16, 0.14, 0.2, 0.16, 0.2])
tb.auto_set_font_size(False); tb.set_fontsize(10.5); tb.scale(1, 1.55)
for (i, j), c in tb.get_celld().items():
    c.set_edgecolor("#d0d0d0")
    if i == 0: c.set_facecolor("#f0f0f0")
    elif j in (2, 3, 4) and int(cells[i - 1][j]) <= 3: c.set_facecolor("#dbe9fa")
ax.set_title(f"店{ex_store}の販売数の上位8商品と、3つの関数の番号（色つきが「3以下」で返る行）", pad=10)
save(fig, "a360_example_store.png", "ROW_NUMBER の同点の順は、この表では商品番号の小さい順に置いた。" + SRC, y=0.03)

fig, ax = plt.subplots(figsize=(9, 4.0))
ax.plot(sw["mean_units"], sw["tie_at_cut_units"], "o-", color=ORANGE, label="販売数で並べる")
ax.plot(sw["mean_units"], sw["tie_at_cut_amount"], "o-", color=BLUE, label="売上金額で並べる")
for r in sw.itertuples():
    ax.annotate(f"{r.tie_at_cut_units:.0f}%", (r.mean_units, r.tie_at_cut_units), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
ax.set_xscale("log"); ax.set_xticks(sw["mean_units"]); ax.set_xticklabels([str(int(v)) for v in sw["mean_units"]])
ax.set_xlabel("1商品あたりの月の販売数の平均（個）"); ax.set_ylabel("3位と4位が同点の店の割合（%）")
ax.set_title("数が小さいほど同点が増える。金額で並べるとほとんど起きない"); ax.legend(frameon=False)
save(fig, "a360_ties_by_volume.png", "300店×40商品を5回ずつ作った平均。" + SRC)

main = {"base": r1, "row_number_runs": r2, "distribution": dist.to_dict("records"), "sweep": sw.round(3).to_dict("records"),
        "tie_in_top3_pct": float(ts["tie_in_top3"].mean() * 100), "example_store": ex_store}
json.dump(main, open(RES / "a360_main.json", "w"), ensure_ascii=False, indent=1)
print(r1); print(r2); print(dist.to_string()); print(sw.round(1).to_string()); print(g.to_string())
