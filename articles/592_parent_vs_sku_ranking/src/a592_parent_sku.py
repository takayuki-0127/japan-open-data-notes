"""592 同じ商品の色・サイズ違いを1品目と数えるか別々に数えるかで、売れ筋の順位はどれだけ変わるのか。
架空の商品マスタ（親品番と色・サイズ）と1年分の売上（seed 592）。実在のブランド・商品名は使わない"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "出典：架空の商品マスタと売上（作成者が乱数で作成、seed 592）"
rng = np.random.default_rng(592)
NP = 150
COLORS = ["BK", "WH", "GY", "NV", "BE", "RD", "GR", "BL"]
SIZES = ["XS", "SS", "SM", "MM", "LL", "XL"]
SIZE_W = np.array([0.04, 0.12, 0.26, 0.30, 0.20, 0.08])

# ---- 1. 親品番と SKU ----
# 親品番は6文字（A00001…）。後から入った20商品だけ7文字（A100011…）で、先頭6文字が同じものが10個ずつ並ぶ
codes = [f"A{i:05d}" for i in range(1, NP - 20 + 1)] + [f"A1000{j}{k}" for j in (1, 2) for k in range(10)]
codes = [str(c) for c in rng.permutation(codes)]   # 7文字の商品が売れ筋に偏らないよう、並びを混ぜる
pop = rng.lognormal(0, 1.0, NP)
ncol = rng.choice(np.arange(1, 9), NP, p=[0.12, 0.12, 0.14, 0.16, 0.14, 0.12, 0.10, 0.10])
size_kind = rng.choice(["free", "S-L", "XS-XL"], NP, p=[0.25, 0.35, 0.40])
rows = []
for i, c in enumerate(codes):
    cols = COLORS[:ncol[i]]
    cw = rng.dirichlet(np.full(ncol[i], 1.2))
    if size_kind[i] == "free":
        sz, sw = ["FR"], np.array([1.0])
    elif size_kind[i] == "S-L":
        sz, sw = SIZES[1:5], SIZE_W[1:5] / SIZE_W[1:5].sum()
    else:
        sz, sw = SIZES, SIZE_W
    for a, ca in zip(cols, cw):
        for b, wb in zip(sz, sw):
            rows.append((c + a + b, c, a, b, pop[i] * ca * wb))
sku = pd.DataFrame(rows, columns=["sku", "parent", "color", "size", "w"])
sku["n_var"] = sku.groupby("parent").sku.transform("size")

# ---- 2. 1年分の売上（日別・SKU別の数量） ----
TOTAL = 400_000
lam = sku.w / sku.w.sum() * TOTAL
qty_year = rng.poisson(lam)
days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
recs = []
for s, q in zip(sku.sku, qty_year):
    if q == 0:
        continue
    d = rng.choice(len(days), q)
    u, n = np.unique(d, return_counts=True)
    recs.append(pd.DataFrame({"sold_on": days[u], "sku": s, "qty": n}))
sales = pd.concat(recs).sort_values(["sold_on", "sku"]).reset_index(drop=True)
sales.to_csv(DATA / "sales.csv", index=False, date_format="%Y-%m-%d")
sku[["sku", "parent", "color", "size"]].to_csv(DATA / "sku_master.csv", index=False)

# ---- 3. 集計：SKU 単位・親品番単位（マスタ）・親品番単位（先頭6文字） ----
q_sku = sales.groupby("sku").qty.sum().reindex(sku.sku).fillna(0).astype(int)
sku["qty"] = q_sku.values
par = sku.groupby("parent").agg(qty=("qty", "sum"), n_var=("sku", "size"), best_sku_qty=("qty", "max")).sort_values("qty", ascending=False)
par["rank"] = par.qty.rank(ascending=False, method="min")
sku["rank"] = sku.qty.rank(ascending=False, method="min")
best_rank = sku.groupby("parent")["rank"].min()
par["best_sku_rank"] = best_rank.reindex(par.index)
pre = sales.assign(p6=sales.sku.str[:6]).groupby("p6").qty.sum().sort_values(ascending=False)
par.to_csv(RES / "by_parent.csv")
sku.drop(columns="w").to_csv(RES / "by_sku.csv", index=False)
pre.rename("qty").to_csv(RES / "by_prefix6.csv")

top20_par = list(par.index[:20])
top20_sku = sku.sort_values(["qty", "sku"], ascending=[False, True]).head(20)
parents_in_sku_top20 = top20_sku.parent.unique()
top20_pre = list(pre.index[:20])


def share_top(v, frac):
    v = np.sort(np.asarray(v))[::-1]
    k = int(np.ceil(len(v) * frac))
    return float(v[:k].sum() / v.sum() * 100)


many = par[par.n_var >= 24]
fake = [g for g in pre.index if g not in par.index]
res = {"n_parents": NP, "n_sku": int(len(sku)), "variants_per_parent": {"median": float(par.n_var.median()), "max": int(par.n_var.max()), "n_single": int((par.n_var == 1).sum())},
       "total_qty": int(sales.qty.sum()),
       "top20_parents_with_a_sku_in_sku_top20": int(len(set(top20_par) & set(parents_in_sku_top20))),
       "distinct_parents_in_sku_top20": int(len(parents_in_sku_top20)),
       "sku_top20_n_from_parents_with_4_or_fewer_variants": int((top20_sku.n_var <= 4).sum()),
       "spearman_parent_rank_vs_best_sku_rank": round(float(par["rank"].corr(par.best_sku_rank, method="spearman")), 3),
       "top20_parents_best_sku_rank": {"median": float(par.best_sku_rank[:20].median()), "max": int(par.best_sku_rank[:20].max())},
       "top20_parents_n_without_sku_in_top100": int((par.best_sku_rank[:20] > 100).sum()),
       "share_top10pct": {"parent": round(share_top(par.qty, 0.1), 1), "sku": round(share_top(sku.qty, 0.1), 1)},
       "share_top20pct": {"parent": round(share_top(par.qty, 0.2), 1), "sku": round(share_top(sku.qty, 0.2), 1)},
       "sku_zero_sales": int((sku.qty == 0).sum()),
       "prefix6": {"n_groups": int(len(pre)), "fake_groups": fake,
                   "fake_group_ranks": {g: int(list(pre.index).index(g) + 1) for g in fake},
                   "top20_overlap_with_master": int(len(set(top20_par) & set(top20_pre))),
                   "true_ranks_of_merged_parents": sorted(int(r) for r in par.loc[[c for c in codes if len(c) == 7], "rank"])}}
# 色・サイズの多い商品の例
ex = par.head(20).sort_values(["best_sku_rank"], ascending=False).iloc[0]
res["example_many_variants"] = {"parent": ex.name, "n_var": int(ex.n_var), "parent_rank": int(ex["rank"]), "best_sku_rank": int(ex.best_sku_rank)}

# ---- 4. SQL（DuckDB、1スレッド） ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE sales AS SELECT * FROM read_csv_auto('{DATA / 'sales.csv'}')")
con.execute(f"CREATE TABLE sku_master AS SELECT * FROM read_csv_auto('{DATA / 'sku_master.csv'}', all_varchar=true)")
sq = con.execute((SQL / "02_rank_duckdb.sql").read_text()).df()
sq.to_csv(RES / "sql_rank.csv", index=False)
m1 = sq[sq.method == "master"].set_index("parent").qty
m2 = sq[sq.method == "prefix6"].set_index("parent").qty
res["sql_match_python"] = bool((m1.reindex(par.index).values == par.qty.values).all() and (m2.reindex(pre.index).values == pre.values).all())
json.dump(res, open(RES / "a592_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 5. 図 ----
fig, ax = plt.subplots(figsize=(7, 5.5))
sc = ax.scatter(par["rank"], par.best_sku_rank, c=par.n_var, cmap="viridis_r", s=22, alpha=0.85)
ax.set_xlabel("親品番（色・サイズをまとめた）での順位"); ax.set_ylabel("その商品でいちばん売れた SKU の順位")
ax.set_yscale("log"); ax.set_yticks([1, 10, 100, 1000], ["1", "10", "100", "1000"]); ax.invert_yaxis()
ax.axvline(20.5, color=GRAY, lw=0.8, ls="--"); ax.axhline(20.5, color=GRAY, lw=0.8, ls="--")
cb = fig.colorbar(sc, ax=ax); cb.set_label("色・サイズの数（SKU数）")
ax.set_title("まとめて上位でも、1つずつでは上位に出てこない商品")
save(fig, "a592_rank_scatter.png", SRC)

fig, ax = plt.subplots(figsize=(7, 4.6))
for v, lab, c in [(par.qty, f"親品番（{NP}品目）", BLUE), (sku.qty, f"SKU（{len(sku)}品目）", ORANGE)]:
    s = np.sort(v.values)[::-1]
    ax.plot(np.arange(1, len(s) + 1) / len(s) * 100, np.cumsum(s) / s.sum() * 100, color=c, lw=2, label=lab)
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8, ls="--")
ax.set_xlabel("売れている順に並べた品目の割合（%）"); ax.set_ylabel("売上数量の累積の割合（%）")
ax.set_title("数える単位で、「上位○%で売上の何%」が変わる")
ax.legend(frameon=False)
save(fig, "a592_concentration.png", SRC)

fig, axes = plt.subplots(1, 2, figsize=(10, 5.2), sharex=True)
for ax, ser, title in [(axes[0], par.qty.head(20), "商品マスタで親品番をひく（正しい）"), (axes[1], pre.head(20), "SKU コードの先頭6文字で切る")]:
    cols = [ORANGE if g in fake else ("#f4b393" if len(g) == 7 else BLUE) for g in ser.index]
    ax.barh(range(20), ser.values / 1000, color=cols)
    ax.set_yticks(range(20), ser.index, fontsize=8); ax.invert_yaxis()
    ax.set_title(title, fontsize=11); ax.set_xlabel("数量（千個）")
fig.suptitle("親品番が7文字の商品（左の薄い橙）を先頭6文字で切ると、10商品ずつ1つにまとまる（右の橙）", fontsize=12)
save(fig, "a592_prefix_top20.png", SRC)
