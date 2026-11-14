"""773 列の順番が違う2つの表を UNION ALL でつなぐと、何行の値が別の列に入るのか

架空の2店の売上表。A 店は (sale_date, store, item, qty, amount)、B 店は (sale_date, store, item, amount, qty) の順で持つ。
SELECT * で UNION ALL すると列の位置で合わさるので、B 店の行は数量と金額が入れ替わる（型が同じ整数なのでエラーにならない）。
列名を書いてつなぐ・UNION ALL BY NAME と比べ、店ごとの数量・金額・平均単価のずれを見る。DuckDB は1スレッド。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の2店の売上表（作成者が乱数で作成、seed 773）"
rng = np.random.default_rng(773)
ITEMS = {"ノート": 180, "ペン": 120, "ファイル": 260, "はさみ": 480, "電卓": 1980}


def make(store, n):
    it = rng.choice(list(ITEMS), n, p=[.3, .3, .2, .12, .08])
    q = rng.integers(1, 6, n); price = np.array([ITEMS[i] for i in it])
    d = pd.to_datetime("2025-04-01") + pd.to_timedelta(rng.integers(0, 30, n), unit="D")
    return pd.DataFrame({"sale_date": d.strftime("%Y-%m-%d"), "store": store, "item": it, "qty": q, "amount": q * price})


A = make("A", 3000).sort_values(["sale_date", "item"], kind="stable").reset_index(drop=True)
Bf = make("B", 2400).sort_values(["sale_date", "item"], kind="stable").reset_index(drop=True)
B = Bf[["sale_date", "store", "item", "amount", "qty"]]          # 列の順番が違う
DATA.mkdir(exist_ok=True); A.to_csv(DATA / "store_a.csv", index=False); B.to_csv(DATA / "store_b.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("store_a", A); con.register("store_b", B)
sql = "\n".join(l for l in (SQL / "02_union_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
stmts = [s.strip() for s in sql.split(";") if s.strip()]
for s in stmts[:-1]: con.execute(s)
Q = con.execute(stmts[-1]).df()
pos = con.execute("SELECT * FROM by_position").df()
truth = pd.concat([A, Bf])
for how in ["by_listed", "by_name"]:
    s = Q[Q.how == how].set_index("store")
    for st in "AB":
        assert int(s.loc[st, "qty"]) == int(truth[truth.store == st].qty.sum()) and int(s.loc[st, "amount"]) == int(truth[truth.store == st].amount.sum())
swapped = int((pos.store == "B").sum())
pb = Q[Q.how == "by_position"].set_index("store"); tb = Q[Q.how == "by_listed"].set_index("store")
Q.to_csv(RES / "by_store.csv", index=False)
item_pos = pos[pos.store == "B"].groupby("item").apply(lambda d: d.amount.sum() / d.qty.sum(), include_groups=False)
item_true = Bf.groupby("item").apply(lambda d: d.amount.sum() / d.qty.sum(), include_groups=False)
I = pd.DataFrame({"item": item_true.index, "unit_price_true": item_true.values, "unit_price_position": item_pos.reindex(item_true.index).values})
I.to_csv(RES / "b_unit_price.csv", index=False)
out = {"rows_a": len(A), "rows_b": len(B), "rows_swapped": swapped, "swapped_share": swapped / (len(A) + len(B)),
       "b_qty_true": int(tb.loc["B", "qty"]), "b_qty_position": int(pb.loc["B", "qty"]),
       "b_amount_true": int(tb.loc["B", "amount"]), "b_amount_position": int(pb.loc["B", "amount"]),
       "total_amount_true": int(tb.amount.sum()), "total_amount_position": int(pb.amount.sum()),
       "total_amount_ratio": float(pb.amount.sum() / tb.amount.sum()),
       "b_unit_price_true": float(tb.loc["B", "amount"] / tb.loc["B", "qty"]), "b_unit_price_position": float(pb.loc["B", "amount"] / pb.loc["B", "qty"]),
       "a_amount": int(tb.loc["A", "amount"]),
       "error_raised": False, "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a773_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：店ごとの金額
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(2); w = .38
ax.bar(x - w / 2, tb.amount / 1e3, w, color=BLUE, label="列名を書いてつなぐ（正しい）")
ax.bar(x + w / 2, pb.amount / 1e3, w, color=ORANGE, label="SELECT * でつなぐ")
for xx, a, b in zip(x, tb.amount / 1e3, pb.amount / 1e3):
    ax.text(xx - w / 2, a + 30, f"{a:,.0f}", ha="center", fontsize=9); ax.text(xx + w / 2, b + 30, f"{b:,.0f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(["A 店", "B 店（列の順番が違う）"]); ax.set_ylabel("売上（千円）"); ax.legend(frameon=False)
ax.set_title("B 店の売上が、数量の合計に入れ替わる（A 店は正しいまま）")
save(fig, "a773_store_amount.png", SRC)
# 図2：品目別の単価（B 店）
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(I))
ax.bar(x - w / 2, I.unit_price_true, w, color=BLUE, label="正しい単価")
ax.bar(x + w / 2, I.unit_price_position, w, color=ORANGE, label="SELECT * でつないだ単価")
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels(I["item"]); ax.set_ylabel("平均単価（円、対数の目盛り）")
ax.legend(frameon=False); ax.set_title("B 店の単価は「数量÷金額」になり、1円未満になる")
save(fig, "a773_unit_price.png", SRC)
# 図3：日ごとの2店合計
dp = pos.groupby("sale_date").amount.sum(); dt = truth.groupby("sale_date").amount.sum()
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(dt))
ax.plot(x, dt.values / 1e3, "o-", color=BLUE, ms=3, label="列名を書いてつなぐ（正しい）")
ax.plot(x, dp.reindex(dt.index).values / 1e3, "s-", color=ORANGE, ms=3, label="SELECT * でつなぐ")
ax.set_xticks(x[::5]); ax.set_xticklabels([d[5:] for d in dt.index[::5]]); ax.set_xlabel("日（2025年4月）")
ax.set_ylabel("2店の売上の合計（千円）"); ax.set_ylim(0, None); ax.legend(frameon=False)
ax.set_title(f"日ごとの合計も、毎日{1 - out['total_amount_ratio']:.0%}前後少なく出る（A 店の分だけが残る）")
save(fig, "a773_daily.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
