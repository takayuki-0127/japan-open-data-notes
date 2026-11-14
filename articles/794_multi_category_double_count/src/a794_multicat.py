"""794 1つの商品が2つのカテゴリに入る表でカテゴリ別に売上を足すと、全体の何倍になるのか

架空の商品300品と、商品とカテゴリの対応表（1品が1〜3カテゴリに入る。うち1つが主なカテゴリ）。
売上明細20,000件をカテゴリ別に、
  そのまま結合して合計／主なカテゴリだけ／カテゴリの数で按分
の3通りで足し、カテゴリ別の合計が全体の売上の何倍になるか、カテゴリの順位がどう変わるかを見る。
DuckDB（1スレッド）と pandas の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の商品と売上（作成者が乱数で作成、seed 794）"
rng = np.random.default_rng(794)
CATS = ["飲料", "菓子", "日用品", "冷凍", "季節もの", "ギフト", "限定品", "まとめ買い"]
MAIN = CATS[:4]; TAG = CATS[4:]          # 主なカテゴリになりうるのは前の4つ、後ろの4つは「横断」のカテゴリ
NP = 300
pc = []
for p in range(1, NP + 1):
    main = rng.choice(MAIN); pc.append((p, main, True))
    k = rng.choice([0, 1, 2], p=[.45, .4, .15])
    for t in rng.choice(TAG, k, replace=False): pc.append((p, t, False))
PC = pd.DataFrame(pc, columns=["product_id", "category", "is_primary"])
pop = rng.gamma(.8, 1, NP)
nk = PC.groupby("product_id").size()
pop = pop * np.where(nk.reindex(range(1, NP + 1)).to_numpy() > 1, 1.6, 1.0)    # 横断のカテゴリにも入る商品はよく売れる
S = pd.DataFrame({"line_id": np.arange(1, 20001), "product_id": rng.choice(np.arange(1, NP + 1), 20000, p=pop / pop.sum())})
S["amount"] = rng.integers(2, 40, len(S)) * 100
DATA.mkdir(exist_ok=True); PC.to_csv(DATA / "product_category.csv", index=False); S.to_csv(DATA / "sales.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", S); con.register("product_category", PC)
q = "\n".join(l for l in (SQL / "02_category_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
M = S.merge(PC, on="product_id").merge(nk.rename("n_cat"), left_on="product_id", right_index=True)
P = M.groupby("category").agg(sales_join=("amount", "sum"), sales_primary=("amount", lambda x: x[M.loc[x.index, "is_primary"]].sum()),
                               sales_alloc=("amount", lambda x: (x / M.loc[x.index, "n_cat"]).sum())).reindex(Q.category)
for c in ["sales_join", "sales_primary", "sales_alloc"]: assert np.allclose(P[c].to_numpy(), Q[c].to_numpy().astype(float)), c
total = int(S.amount.sum())
Q["share_join"] = Q.sales_join / total
for c in ["sales_join", "sales_primary", "sales_alloc"]: Q[f"rank_{c[6:]}"] = Q[c].rank(ascending=False, method="min").astype(int)
Q["cat_order"] = Q.category.map({c: i for i, c in enumerate(CATS)}); Q = Q.sort_values("cat_order").drop(columns="cat_order")
Q.to_csv(RES / "by_category.csv", index=False)
multi = int((nk > 1).sum())
out = {"products": NP, "lines": len(S), "total_sales": total, "multi_cat_products": multi, "multi_cat_share": multi / NP,
       "mean_categories": float(nk.mean()),
       "sum_join": float(Q.sales_join.sum()), "ratio_join": float(Q.sales_join.sum() / total),
       "sum_primary": float(Q.sales_primary.sum()), "sum_alloc": float(Q.sales_alloc.sum()),
       "sales_share_multi": float(S.product_id.isin(nk[nk > 1].index).mean()),
       "by_category": Q.set_index("category")[["sales_join", "sales_primary", "sales_alloc", "rank_join", "rank_primary", "rank_alloc"]].to_dict(orient="index"),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a794_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：カテゴリ別の合計を足すと全体の何倍か
fig, ax = plt.subplots(figsize=(8.5, 4.4))
lab = ["全体の売上", "そのまま結合して\nカテゴリ別に足す", "主なカテゴリだけ", "カテゴリの数で按分"]
vals = [total, Q.sales_join.sum(), Q.sales_primary.sum(), Q.sales_alloc.sum()]
ax.bar(range(4), np.array(vals) / 1e6, color=["#0b0b0b", ORANGE, BLUE, GREEN])
for i, v in enumerate(vals): ax.text(i, v / 1e6 + .3, f"{v/1e6:.1f}百万円\n（{v/total:.2f}倍）", ha="center", fontsize=10)
ax.set_xticks(range(4)); ax.set_xticklabels(lab); ax.set_ylabel("売上（百万円）"); ax.set_ylim(0, max(vals) / 1e6 * 1.25)
ax.set_title(f"そのまま足すと、カテゴリ別の合計は全体の{out['ratio_join']:.2f}倍になる")
save(fig, "a794_totals.png", SRC)

# 図2：カテゴリ別の売上（3通り）
fig, ax = plt.subplots(figsize=(9.5, 4.6)); x = np.arange(len(Q)); w = .27
for j, (c, col, l) in enumerate([("sales_join", ORANGE, "そのまま結合"), ("sales_primary", BLUE, "主なカテゴリだけ"), ("sales_alloc", GREEN, "按分")]):
    ax.bar(x + (j - 1) * w, Q[c] / 1e6, w, color=col, label=l)
ax.set_xticks(x); ax.set_xticklabels(Q.category); ax.set_ylabel("売上（百万円）"); ax.legend(frameon=False)
ax.axvline(3.5, color=GRAY, lw=.8, ls=":"); ax.text(3.6, ax.get_ylim()[1] * .92, "横断のカテゴリ →", fontsize=9, color=GRAY)
ax.set_title("横断のカテゴリは、主なカテゴリだけで数えると0。そのまま結合すると大きく見える")
save(fig, "a794_by_category.png", SRC)

# 図3：順位の入れ替わり（そのまま結合 vs 按分）
fig, ax = plt.subplots(figsize=(7, 5))
for _, r in Q.iterrows():
    col = ORANGE if r.category in TAG else BLUE
    ax.plot([0, 1], [r.rank_join, r.rank_alloc], "o-", color=col)
    ax.text(-.04, r.rank_join, f"{r.category}", ha="right", va="center", fontsize=10)
    ax.text(1.04, r.rank_alloc, f"{r.category}", ha="left", va="center", fontsize=10)
ax.set_xlim(-.5, 1.5); ax.invert_yaxis(); ax.set_xticks([0, 1]); ax.set_xticklabels(["そのまま結合", "按分"]); ax.set_ylabel("順位")
ax.set_title("足し方で、カテゴリの順位も入れ替わる（オレンジは横断のカテゴリ）")
save(fig, "a794_rank.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "by_category"}, ensure_ascii=False, indent=1)); print(Q.round(0).to_string())
