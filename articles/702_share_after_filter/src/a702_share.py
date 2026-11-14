"""702 構成比を WHERE で絞り込んだあとに出すと、全体に対する割合とどれだけ違って見えるのか

架空の60品目（6カテゴリ）の売上明細（4万行）。構成比の分母を
  A 絞った中の合計（WHERE のあとに SUM() OVER ()）
  B 全体の合計（全体で割ってから絞る）
で比べる。絞り方は「カテゴリ」「上位10品目」「1行1万円以上の明細」の3通り。
DuckDB（1スレッド）と pandas で一致を確かめる。seed 702。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の品目別の売上明細（作成者が乱数で作成、seed 702）"
rng = np.random.default_rng(702)
CATS = ["食品", "飲料", "日用品", "文具", "衣料", "家電"]
cat_w = np.array([0.30, 0.15, 0.20, 0.08, 0.15, 0.12])
items = []
for c, wc in zip(CATS, cat_w):
    pw = rng.dirichlet(np.ones(10) * 0.8)
    for k in range(10):
        items.append((f"{c}{k + 1:02d}", c, wc * pw[k]))
IT = pd.DataFrame(items, columns=["item", "category", "w"])
N = 40000
idx = rng.choice(len(IT), size=N, p=IT.w / IT.w.sum())
unit = {"食品": 600, "飲料": 300, "日用品": 900, "文具": 500, "衣料": 3500, "家電": 9000}
S = pd.DataFrame({"line_id": np.arange(1, N + 1), "item": IT.item.values[idx], "category": IT.category.values[idx]})
S["amount"] = (np.array([unit[c] for c in S.category]) * rng.lognormal(0, 0.7, N) // 10 * 10).astype(int) + 10
S.to_csv(DATA / "sales.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", S)
q = [x for x in (SQL / "02_share_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
qa, qb, qc = [con.execute(x).df().set_index("item") for x in q]
tot = S.amount.sum()
g = S.groupby(["item", "category"]).amount.sum().reset_index().set_index("item")
g["share_total"] = g.amount / tot
food = g[g.category == "食品"].copy(); food["share_in_filter"] = food.amount / food.amount.sum()
assert np.allclose(food.sort_index().share_in_filter, qa.sort_index().share_in_filter)
assert np.allclose(food.sort_index().share_total, qb.sort_index().share_total)
top = g.sort_values("amount", ascending=False).head(10).copy(); top["share_in_top10"] = top.amount / top.amount.sum()
assert np.allclose(top.sort_index().share_in_top10, qc.sort_index().share_in_top10)
# 1行1万円以上の明細に絞る（行の絞り込みで品目の顔ぶれと合計が変わる）
big = S[S.amount >= 10000]
gb = big.groupby("item").amount.sum(); gb_share = gb / gb.sum()
cat_total_share = S.groupby("category").amount.sum() / tot
cat_big_share = big.groupby("category").amount.sum() / big.amount.sum()
res = []
for name, sh_f, sh_t in [("カテゴリ「食品」で絞る", food.share_in_filter, food.share_total),
                         ("上位10品目に絞る", top.share_in_top10, top.share_total)]:
    res.append({"filter": name, "items": len(sh_f), "denominator_share_of_total_pct": round(float(sh_t.sum() * 100), 1),
                "inflation_factor": round(float((sh_f / sh_t).mean()), 2),
                "max_item_share_filter_pct": round(float(sh_f.max() * 100), 1), "max_item_share_total_pct": round(float(sh_t.loc[sh_f.idxmax()] * 100), 1),
                "max_item": sh_f.idxmax()})
pd.DataFrame(res).to_csv(RES / "summary.csv", index=False)
out = {"lines": N, "items": len(IT), "total_amount": int(tot), "filters": res,
       "big_lines_rows": int(len(big)), "big_lines_amount_share_pct": round(float(big.amount.sum() / tot * 100), 1),
       "category_share_total_pct": (cat_total_share * 100).round(1).to_dict(),
       "category_share_big_lines_pct": (cat_big_share.reindex(CATS).fillna(0) * 100).round(1).to_dict()}
json.dump(out, open(RES / "a702_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：食品の10品目
f = food.sort_values("amount", ascending=False)
fig, ax = plt.subplots(figsize=(8.5, 3.8)); x = np.arange(len(f))
ax.bar(x - 0.2, f.share_in_filter * 100, 0.4, color=ORANGE, label="絞った中の合計で割る（食品の中の割合）")
ax.bar(x + 0.2, f.share_total * 100, 0.4, color=BLUE, label="全体の合計で割る")
ax.set_xticks(x); ax.set_xticklabels(f.index, fontsize=9); ax.set_ylabel("構成比（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"食品で絞ってから割ると、どの品目も{res[0]['inflation_factor']:.1f}倍に見える（食品は全体の{res[0]['denominator_share_of_total_pct']:.0f}%）")
save(fig, "a702_food.png", SRC)
# 図2：上位10品目
t = top.sort_values("amount", ascending=False)
fig, ax = plt.subplots(figsize=(8.5, 3.8)); x = np.arange(len(t))
ax.bar(x - 0.2, t.share_in_top10 * 100, 0.4, color=ORANGE, label="上位10品目の中の割合（合計100%）")
ax.bar(x + 0.2, t.share_total * 100, 0.4, color=BLUE, label="全体に対する割合")
ax.set_xticks(x); ax.set_xticklabels(t.index, fontsize=9); ax.set_ylabel("構成比（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"上位10品目だけで割ると、10品目で100%。本当は全体の{res[1]['denominator_share_of_total_pct']:.0f}%")
save(fig, "a702_top10.png", SRC)
# 図3：行を絞るとカテゴリの構成比そのものが変わる
fig, ax = plt.subplots(figsize=(8.5, 3.6)); x = np.arange(len(CATS))
ax.bar(x - 0.2, cat_total_share.reindex(CATS) * 100, 0.4, color=BLUE, label="全部の明細")
ax.bar(x + 0.2, cat_big_share.reindex(CATS).fillna(0) * 100, 0.4, color=ORANGE, label="1行1万円以上の明細だけ")
ax.set_xticks(x); ax.set_xticklabels(CATS); ax.set_ylabel("カテゴリの構成比（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("明細を金額で絞ってから構成比を出すと、高い品物のカテゴリが大きく見える")
save(fig, "a702_big_lines.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
