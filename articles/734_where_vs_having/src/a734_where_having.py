"""734 「1回1万円以上の注文がある顧客」と「合計1万円以上の顧客」を取り違えると、何人がずれるのか

架空の顧客3,000人の1年間の注文（約2万件）。1人の注文回数はポアソン（平均は人による）、1回の金額は対数正規（中央値3,500円）。
  WHERE で絞る：1回1万円以上の注文がある顧客（行を絞ってから顧客を数える）
  HAVING で絞る：注文の合計が1万円以上の顧客（顧客ごとに合計してから絞る）
2つの顧客の数と重なり、「合計1万円以上の顧客の売上」を WHERE で行を絞ってから出したときのずれを数える。
金額の基準を 5,000〜30,000円で変えた場合も出す。DuckDB の SQL と Python が一致することを確かめる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の顧客3,000人の注文（作成者が乱数で作成、seed 734）"
rng = np.random.default_rng(734)
DATA.mkdir(exist_ok=True)
NC = 3000
lam = rng.gamma(1.2, 6.5 / 1.2, NC)
k = rng.poisson(lam)
cid = np.repeat([f"C{i+1:04d}" for i in range(NC)], k)
amt = (rng.lognormal(np.log(3500), 0.75, k.sum()) // 10 * 10).astype(int)
O = pd.DataFrame({"order_id": [f"O{i+1:06d}" for i in range(len(cid))], "customer_id": cid, "amount": amt})
O.to_csv(DATA / "orders.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("o0", O); con.execute("CREATE TABLE orders AS SELECT * FROM o0")
sql = (SQL / "02_where_having_duckdb.sql").read_text(encoding="utf-8")
tot = O.groupby("customer_id").amount.sum()


def calc(th):
    bo = set(O[O.amount >= th].customer_id); bt = set(tot[tot >= th].index)
    sales_bt = int(O[O.customer_id.isin(bt)].amount.sum())
    w = O[O.amount >= th].groupby("customer_id").amount.sum(); sales_w = int(w[w >= th].sum())
    return {"th": th, "n_big_order": len(bo), "n_big_total": len(bt), "n_both": len(bo & bt),
            "only_total": len(bt - bo), "only_order": len(bo - bt), "sales_big_total": sales_bt, "sales_wrong": sales_w}


rows = []
for th in [5000, 10000, 15000, 20000, 30000]:
    r = calc(th); dq = con.execute(sql.replace(":th", str(th))).df().iloc[0]
    for c in ["n_big_order", "n_big_total", "n_both", "sales_big_total", "sales_wrong"]: assert int(dq[c]) == r[c], (th, c)
    rows.append(r)
S = pd.DataFrame(rows); S.to_csv(RES / "by_threshold.csv", index=False)
r10 = S.set_index("th").loc[10000]
buyers = int((tot > 0).sum())
out = {"customers": NC, "buyers": buyers, "orders": len(O), "amount_median": int(np.median(amt)),
       "th10000": {k_: int(v) for k_, v in r10.items()},
       "th10000_extra": {"total_only_pct_of_big_total": round(float(r10.only_total / r10.n_big_total * 100), 1),
                         "sales_wrong_short_pct": round(float((1 - r10.sales_wrong / r10.sales_big_total) * 100), 1)},
       "by_threshold": {str(int(r.th)): {"n_big_order": int(r.n_big_order), "n_big_total": int(r.n_big_total)} for r in S.itertuples()},
       "sql_matches_python": True}
json.dump(out, open(RES / "a734_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：重なり
fig, ax = plt.subplots(figsize=(8, 3.4))
assert r10.only_order == 0                                   # 1回で基準以上なら、合計も必ず基準以上
parts = [("1回1万円以上の注文がある（WHERE でも拾える）", r10.n_both, ORANGE), ("合計は1万円以上だが、1回1万円以上の注文はない", r10.only_total, BLUE)]
left = 0
for nm, v, col in parts:
    ax.barh(0, v, left=left, color=col); ax.text(left + v / 2, 0, f"{int(v):,}人", ha="center", va="center", color="white" if v > 150 else INK, fontsize=10)
    ax.text(left + v / 2, 0.55, nm, ha="center", va="bottom", fontsize=8.5); left += v
ax.set_ylim(-0.6, 1.3); ax.set_yticks([]); ax.set_xlabel("顧客数")
ax.set_title(f"「合計1万円以上」の{int(r10.n_big_total):,}人のうち、{int(r10.only_total):,}人（{out['th10000_extra']['total_only_pct_of_big_total']}%）は WHERE では拾えない", fontsize=11.5)
save(fig, "a734_overlap.png", SRC)

# 図2：売上の出し方
fig, ax = plt.subplots(figsize=(7.5, 3.6))
vals = [r10.sales_big_total, r10.sales_wrong]
ax.bar(["合計1万円以上の顧客の\nすべての注文", "WHERE で1万円以上の注文に\n絞ってから合計（まちがい）"], np.array(vals) / 1e6, color=[GREEN, ORANGE])
for i, v in enumerate(vals): ax.text(i, v / 1e6 + 0.5, f"{v / 1e6:,.1f}百万円", ha="center")
ax.set_ylabel("売上（百万円）"); ax.set_ylim(0, vals[0] / 1e6 * 1.2)
ax.set_title(f"WHERE を先にかけると、売上も顧客も別のものになる（{out['th10000_extra']['sales_wrong_short_pct']}%少ない）")
save(fig, "a734_sales.png", SRC)

# 図3：基準を変えたとき
fig, ax = plt.subplots(figsize=(8, 3.6)); xs = [f"{int(t):,}円" for t in S.th]
ax.plot(xs, S.n_big_total, marker="o", color=BLUE, label="合計が基準以上（HAVING）")
ax.plot(xs, S.n_big_order, marker="o", color=ORANGE, label="1回で基準以上の注文がある（WHERE）")
for i, r in enumerate(S.itertuples()):
    ax.text(i, r.n_big_total + 40, f"{r.n_big_total:,}", ha="center", color=BLUE, fontsize=8.5); ax.text(i, r.n_big_order - 110, f"{r.n_big_order:,}", ha="center", color=ORANGE, fontsize=8.5)
ax.set_xlabel("金額の基準"); ax.set_ylabel("顧客数"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, NC * 1.05)
ax.set_title("基準が高いほど、2つの数え方の人数は大きく違う")
save(fig, "a734_threshold.png", SRC)
print(json.dumps(out, ensure_ascii=False))
