"""721 2つの列を区切りなしでつないでキーにすると、別の組み合わせが同じキーになる行は何件あるのか

架空のチェーンの店コード（1〜120、0で桁をそろえない文字）と商品コード（1〜300、同じく文字）。
各店が商品のうち60品を扱い、店×商品ごとに1か月の売上と目標がある（7,200組）。
目標の表のキーを3通りで作り、売上の表につなぐ：
  区切りなし：店コード＋商品コード（'1'+'23' と '12'+'3' がどちらも '123'）
  区切りあり：店コード＋'-'＋商品コード
  2列のまま：店コードと商品コードの2列で結合
同じキーになった組の数、つないだあとの行数、目標の合計のずれを数える。DuckDB の SQL でも同じ結果を確かめる。
最後に、店の数を 9・99・120・999 と変えたときの、同じキーになる組の割合を出す（各店60品、商品は300品）。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の店別・商品別の売上と目標（作成者が乱数で作成、seed 721）"
rng = np.random.default_rng(721)
DATA.mkdir(exist_ok=True)


def make_pairs(n_store, n_item=300, per=60):
    rows = []
    for s in range(1, n_store + 1):
        for i in np.sort(rng.choice(np.arange(1, n_item + 1), per, replace=False)):
            rows.append((str(s), str(int(i))))
    return pd.DataFrame(rows, columns=["store_cd", "item_cd"])


P = make_pairs(120)
P["amount"] = rng.integers(1, 200, len(P)) * 100
P["target"] = (P.amount * rng.uniform(0.8, 1.2, len(P))).round(-2).astype(int)
sales = P[["store_cd", "item_cd", "amount"]]; targets = P[["store_cd", "item_cd", "target"]]
sales.to_csv(DATA / "sales.csv", index=False); targets.to_csv(DATA / "targets.csv", index=False)

P["key_nosep"] = P.store_cd + P.item_cd; P["key_sep"] = P.store_cd + "-" + P.item_cd
kc = P.key_nosep.value_counts()
coll_keys = kc[kc > 1]
pairs_in_coll = int(coll_keys.sum())
tn = targets.assign(key_nosep=targets.store_cd + targets.item_cd)[["key_nosep", "target"]]
ts = targets.assign(key_sep=targets.store_cd + "-" + targets.item_cd)[["key_sep", "target"]]
sales_k = sales.assign(key_nosep=sales.store_cd + sales.item_cd, key_sep=sales.store_cd + "-" + sales.item_cd)
j1 = sales_k.merge(tn, on="key_nosep"); j2 = sales_k.merge(ts, on="key_sep"); j3 = sales.merge(targets, on=["store_cd", "item_cd"])
py = pd.DataFrame({"method": ["nosep", "sep", "two_columns"], "rows": [len(j1), len(j2), len(j3)],
                   "amount": [j1.amount.sum(), j2.amount.sum(), j3.amount.sum()], "target": [j1.target.sum(), j2.target.sum(), j3.target.sum()]})

con = duckdb.connect(); con.execute("SET threads=1")
con.register("s0", sales); con.register("t0", targets)
con.execute("CREATE TABLE sales AS SELECT * FROM s0"); con.execute("CREATE TABLE targets AS SELECT * FROM t0")
con.execute("CREATE TABLE targets_nosep AS SELECT store_cd || item_cd AS key_nosep, target FROM targets")
con.execute("CREATE TABLE targets_sep AS SELECT store_cd || '-' || item_cd AS key_sep, target FROM targets")
dq = con.execute((SQL / "02_concat_key_duckdb.sql").read_text(encoding="utf-8")).df()
m = py.merge(dq, on="method", suffixes=("_py", "_sql"))
for c in ["rows", "amount", "target"]: assert (m[c + "_py"] == m[c + "_sql"]).all(), c
py.to_csv(RES / "join_summary.csv", index=False)

ex = P[P.key_nosep.isin(coll_keys.index)].sort_values(["key_nosep", "store_cd"]).head(12)
ex[["key_nosep", "store_cd", "item_cd", "amount", "target"]].to_csv(RES / "collision_examples.csv", index=False)

# 店の数を変えたとき
by_n = []
for ns in [9, 99, 120, 999]:
    vals = []
    for r in range(5):
        q = make_pairs(ns); k = (q.store_cd + q.item_cd).value_counts()
        vals.append(k[k > 1].sum() / len(q) * 100)
    by_n.append({"stores": ns, "pairs": ns * 60, "collide_pct": float(np.mean(vals))})
BN = pd.DataFrame(by_n); BN.round(2).to_csv(RES / "by_store_count.csv", index=False)

true_t = int(targets.target.sum())
out = {"stores": 120, "items": 300, "items_per_store": 60, "pairs": len(P),
       "keys_nosep": int(P.key_nosep.nunique()), "colliding_keys": int(len(coll_keys)), "pairs_in_colliding_keys": pairs_in_coll,
       "pairs_in_colliding_keys_pct": round(pairs_in_coll / len(P) * 100, 2), "max_pairs_per_key": int(kc.max()),
       "join_rows": dict(zip(py.method, py.rows.astype(int).tolist())), "extra_rows_nosep": int(len(j1) - len(j3)),
       "target_sum": dict(zip(py.method, py.target.astype(int).tolist())), "target_true": true_t,
       "target_over_pct_nosep": round((int(j1.target.sum()) / true_t - 1) * 100, 2),
       "amount_sum": dict(zip(py.method, py.amount.astype(int).tolist())),
       "by_store_count_collide_pct": {str(r.stores): round(r.collide_pct, 2) for r in BN.itertuples()},
       "sql_matches_python": True}
json.dump(out, open(RES / "a721_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：同じキーになる例
fig, ax = plt.subplots(figsize=(8, 3.6)); ax.axis("off")
show = ex.head(8)
cell = [[r.key_nosep, r.store_cd, r.item_cd, f"{r.store_cd}-{r.item_cd}"] for r in show.itertuples()]
tb = ax.table(cellText=cell, colLabels=["区切りなしのキー", "店コード", "商品コード", "区切りありのキー"], loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.4)
for (r, c), cl in tb.get_celld().items():
    if r == 0: cl.set_facecolor(LIGHT)
    elif c == 0: cl.set_text_props(color=ORANGE)
ax.set_title(f"区切りなしでは別の組が同じキーになる（7,200組のうち {pairs_in_coll}組・{len(coll_keys)}キー）")
save(fig, "a721_examples.png", SRC)

# 図2：つないだあとの行数と目標の合計
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
lab = ["区切りなし", "区切りあり", "2列のまま"]; cols = [ORANGE, BLUE, GREEN]
axes[0].bar(lab, py.rows, color=cols); axes[0].set_ylim(0, py.rows.max() * 1.12)
for i, v in enumerate(py.rows): axes[0].text(i, v + 80, f"{v:,}", ha="center", fontsize=9)
axes[0].set_ylabel("つないだあとの行数"); axes[0].set_title(f"区切りなしは {len(j1) - len(j3)}行ふえる")
axes[1].bar(lab, py.target / 1e6, color=cols); axes[1].set_ylim(0, py.target.max() / 1e6 * 1.12)
for i, v in enumerate(py.target): axes[1].text(i, v / 1e6 + 0.8, f"{v / 1e6:,.2f}", ha="center", fontsize=9)
axes[1].set_ylabel("目標の合計（百万円）"); axes[1].set_title(f"目標の合計は {out['target_over_pct_nosep']}% 多くなる")
fig.suptitle("目標の表を売上につなぐと、区切りなしでは行と合計がふえる", y=1.02)
save(fig, "a721_join.png", SRC)

# 図3：店の数と、同じキーになる組の割合
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar([f"{n}店\n（1〜{len(str(n))}桁）" for n in BN.stores], BN.collide_pct, color=ORANGE)
for i, v in enumerate(BN.collide_pct): ax.text(i, v + 0.3, f"{v:.1f}%", ha="center", fontsize=9)
ax.set_ylabel("同じキーになった組の割合（%）"); ax.set_xlabel("店の数（商品は300品・1店60品、各5回の平均）")
ax.set_title("桁数のまちまちなコードが増えるほど、同じキーになりやすい")
save(fig, "a721_by_store_count.png", SRC)
print(json.dumps(out, ensure_ascii=False))
