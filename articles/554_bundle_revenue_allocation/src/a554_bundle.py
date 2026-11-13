"""554 セット商品の売上を構成品に分けるとき、金額の割り振り方で商品別の売上はどれだけ変わるのか

架空の店（単品30品目、セット商品10種。セットは2〜4品の組み合わせで、単品価格の合計より10〜25%安い）の
2025年の売上を作り、セットの売上を構成品に割り振る3通りで、商品別の売上・粗利・順位を比べる。
  A 単品価格の比で按分
  B 原価の比で按分
  C 構成品で均等に按分（数量を考えない）
Python と SQL（DuckDB、1スレッド）で A の商品別売上が一致することを確かめる。
数字は、置いた価格・原価・セットの組み合わせで決まる。会計基準の解説や助言ではない。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の店の単品・セット商品の売上（作成者が乱数で作成、seed 554）"
rng = np.random.default_rng(554)
NI, NS = 30, 10
cat = rng.choice(["食品", "飲料", "雑貨"], NI, p=[0.4, 0.3, 0.3])
price = np.array([int(round(rng.choice([300, 500, 800, 1200, 2000, 3500]) * rng.uniform(0.8, 1.2), -1)) for _ in range(NI)])
cost_rate = np.where(cat == "食品", rng.uniform(0.45, 0.7, NI), np.where(cat == "飲料", rng.uniform(0.25, 0.45, NI), rng.uniform(0.3, 0.6, NI)))
cost = np.round(price * cost_rate).astype(int)
items = pd.DataFrame({"item_id": [f"I{i+1:02d}" for i in range(NI)], "category": cat, "list_price": price, "unit_cost": cost})

comps, sets = [], []
for s in range(NS):
    k = int(rng.integers(2, 5))
    its = rng.choice(NI, k, replace=False)
    units = rng.choice([1, 1, 1, 2, 3], k)
    lv = int((price[its] * units).sum())
    disc = rng.uniform(0.10, 0.25)
    sp = int(round(lv * (1 - disc), -1))
    sets.append((f"S{s+1:02d}", sp, lv, round(disc * 100, 1)))
    for i, u in zip(its, units):
        comps.append((f"S{s+1:02d}", f"I{i+1:02d}", int(u)))
sets = pd.DataFrame(sets, columns=["set_id", "set_price", "list_value", "discount_pct"])
comps = pd.DataFrame(comps, columns=["set_id", "item_id", "units"])

# 売上：単品は品目ごと、セットはセットごとに、年間の販売数を置く
single_qty = rng.poisson(rng.gamma(1.5, 900, NI))
set_qty = rng.poisson(rng.gamma(1.8, 700, NS))
single = pd.DataFrame({"item_id": items.item_id, "qty": single_qty})
single["amount"] = single.qty * items.list_price
set_sales = pd.DataFrame({"sale_id": np.arange(1, NS + 1), "set_id": sets.set_id, "qty": set_qty})
set_sales["amount"] = set_sales.qty * sets.set_price
items.to_csv(DATA / "items.csv", index=False); sets.to_csv(DATA / "sets.csv", index=False)
comps.to_csv(DATA / "set_components.csv", index=False); single.to_csv(DATA / "single_sales.csv", index=False)
set_sales.to_csv(DATA / "set_sales.csv", index=False)

# --- 割り振り
c = comps.merge(items, on="item_id").merge(set_sales[["set_id", "qty", "amount"]], on="set_id")
c["w_A"] = c.list_price * c.units
c["w_B"] = c.unit_cost * c.units
c["w_C"] = 1.0
for m in ["A", "B", "C"]:
    c[f"alloc_{m}"] = c.amount * c[f"w_{m}"] / c.groupby("set_id")[f"w_{m}"].transform("sum")
c["cost_total"] = c.unit_cost * c.units * c.qty

res = items.set_index("item_id")[["category", "list_price", "unit_cost"]].copy()
res["single_sales"] = single.set_index("item_id").amount
res["single_cost"] = single.set_index("item_id").qty * items.set_index("item_id").unit_cost
res["set_cost"] = c.groupby("item_id").cost_total.sum().reindex(res.index).fillna(0)
for m in ["A", "B", "C"]:
    res[f"sales_{m}"] = res.single_sales + c.groupby("item_id")[f"alloc_{m}"].sum().reindex(res.index).fillna(0)
    res[f"gp_{m}"] = res[f"sales_{m}"] - res.single_cost - res.set_cost
    res[f"gpr_{m}"] = res[f"gp_{m}"] / res[f"sales_{m}"] * 100
    res[f"rank_{m}"] = res[f"sales_{m}"].rank(ascending=False, method="min").astype(int)
in_set = sorted(comps.item_id.unique())
res["in_set"] = res.index.isin(in_set)
res.round(2).to_csv(RES / "by_item.csv")

# SQL（DuckDB）で A を確かめる
con = duckdb.connect(); con.execute("SET threads=1")
con.register("set_sales", set_sales); con.register("set_components", comps); con.register("items", items)
sq = con.execute((SQL / "02_allocation_duckdb.sql").read_text(encoding="utf-8")).df().set_index("item_id").allocated_sales
py = c.groupby("item_id").alloc_A.sum()
assert np.allclose(sq.reindex(py.index).values, py.values)

S = res[res.in_set]
def pair(a, b):
    d = (S[f"sales_{b}"] / S[f"sales_{a}"] - 1) * 100
    return d
dBA, dCA = pair("A", "B"), pair("A", "C")
gpr_range = (S[["gpr_A", "gpr_B", "gpr_C"]].max(axis=1) - S[["gpr_A", "gpr_B", "gpr_C"]].min(axis=1))
rank_changed_B = int((res.rank_A != res.rank_B).sum()); rank_changed_C = int((res.rank_A != res.rank_C).sum())
top10 = lambda m: set(res[f"sales_{m}"].nlargest(10).index)
set_share = float(set_sales.amount.sum() / (set_sales.amount.sum() + single.amount.sum()) * 100)
out = {"items": NI, "sets": NS, "items_in_sets": len(in_set), "set_sales_share_pct": round(set_share, 1),
       "total_sales": int(res.sales_A.sum()), "set_sales": int(set_sales.amount.sum()),
       "discount_pct_range": [float(sets.discount_pct.min()), float(sets.discount_pct.max())],
       "B_vs_A_pct": {"min": round(float(dBA.min()), 1), "max": round(float(dBA.max()), 1), "median_abs": round(float(dBA.abs().median()), 1)},
       "C_vs_A_pct": {"min": round(float(dCA.min()), 1), "max": round(float(dCA.max()), 1), "median_abs": round(float(dCA.abs().median()), 1)},
       "gpr_range_pt": {"median": round(float(gpr_range.median()), 1), "max": round(float(gpr_range.max()), 1), "max_item": str(gpr_range.idxmax())},
       "rank_changed_B": rank_changed_B, "rank_changed_C": rank_changed_C,
       "top10_diff_B": len(top10("A") ^ top10("B")) // 2, "top10_diff_C": len(top10("A") ^ top10("C")) // 2,
       "total_gp_same": bool(np.isclose(res.gp_A.sum(), res.gp_B.sum()) and np.isclose(res.gp_A.sum(), res.gp_C.sum()))}
ex = gpr_range.idxmax()
out["max_item_detail"] = {k: round(float(res.loc[ex, k]), 1) for k in ["sales_A", "sales_B", "sales_C", "gpr_A", "gpr_B", "gpr_C"]}
json.dump(out, open(RES / "a554_main.json", "w"), ensure_ascii=False, indent=1)

# --- 図1：商品別売上の差（B・C の A との差）
o = S.sort_values("sales_A", ascending=False)
fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = np.arange(len(o)); w = 0.4
ax.bar(x - w / 2, (o.sales_B / o.sales_A - 1) * 100, w, color=ORANGE, label="原価の比で按分（A との差）")
ax.bar(x + w / 2, (o.sales_C / o.sales_A - 1) * 100, w, color=GREEN, label="均等に按分（A との差）")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(x); ax.set_xticklabels(o.index, rotation=90, fontsize=8)
ax.set_ylabel("単品価格の比で按分した売上との差（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"セットに入っている{len(o)}品目の年間売上：割り振り方による差（売上の多い順）")
save(fig, "a554_sales_diff.png", SRC, y=-0.08)

# --- 図2：粗利率の幅
o2 = S.assign(r=gpr_range).sort_values("r", ascending=False).head(12)
fig, ax = plt.subplots(figsize=(9, 4.4))
for i, (k, r) in enumerate(o2.iterrows()):
    vals = [r.gpr_A, r.gpr_B, r.gpr_C]
    ax.plot([min(vals), max(vals)], [i, i], color=LIGHT, lw=4, zorder=1)
    ax.scatter(r.gpr_A, i, color=BLUE, zorder=3, label="単品価格の比" if i == 0 else None)
    ax.scatter(r.gpr_B, i, color=ORANGE, zorder=3, marker="s", label="原価の比" if i == 0 else None)
    ax.scatter(r.gpr_C, i, color=GREEN, zorder=3, marker="^", label="均等" if i == 0 else None)
ax.set_yticks(range(len(o2))); ax.set_yticklabels([f"{k}（{r.category}）" for k, r in o2.iterrows()]); ax.invert_yaxis()
ax.set_xlabel("年間の粗利率（%）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("粗利率が割り振り方で大きく変わる12品目")
save(fig, "a554_gpr_range.png", SRC)

# --- 図3：順位の入れ替わり（A→C）
fig, ax = plt.subplots(figsize=(6.5, 5.5))
for k, r in res.iterrows():
    col = ORANGE if r.rank_A != r.rank_C else LIGHT
    ax.plot([0, 1], [r.rank_A, r.rank_C], color=col, lw=1.6 if col == ORANGE else 1)
    ax.text(-0.03, r.rank_A, k, ha="right", va="center", fontsize=7)
    ax.text(1.03, r.rank_C, k, ha="left", va="center", fontsize=7)
ax.set_xlim(-0.3, 1.3); ax.invert_yaxis(); ax.set_xticks([0, 1]); ax.set_xticklabels(["単品価格の比", "均等"])
ax.set_yticks([1, 10, 20, 30]); ax.set_ylabel("売上の順位")
ax.set_title(f"商品別売上の順位：{rank_changed_C}品目が入れ替わる（橙）")
save(fig, "a554_rank.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
