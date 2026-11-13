"""601 外部結合（LEFT JOIN）のあと WHERE で右の表の列を絞ると、何件の行が黙って消えるのか

架空の顧客5,000人と2025年の注文を作り、「顧客ごとの下期の注文金額（注文がなければ0）」を3通りの SQL で出す。
  W0 正しい：期間の条件を ON に置く
  W1 誤り：期間の条件を WHERE に置く（右の表が NULL の行が消え、内部結合と同じになる）
  W2 半分直した誤り：WHERE に OR o.order_id IS NULL を足す（期間の外にだけ注文がある顧客が消える）
消えた顧客の数・顧客あたりの平均のずれを数え、期間の長さを1〜12か月で変えて消える割合を見る。
DuckDB（1スレッド）の SQL と pandas の結果が一致することを確かめる。数字は置いた買い方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の顧客と注文（作成者が乱数で作成、seed 601）"
rng = np.random.default_rng(601)
N_CUST = 5000
cust = pd.DataFrame({"customer_id": np.arange(1, N_CUST + 1),
                     "joined_on": pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 1000, N_CUST), unit="D")})
# 年間の注文回数：0回の顧客が多め（負の二項）。買う頻度は顧客ごとに違う
lam = rng.gamma(0.6, 4.0, N_CUST)
n_ord = rng.poisson(lam)
rows = []
oid = 0
for cid, k in zip(cust.customer_id, n_ord):
    if k == 0:
        continue
    d = pd.Timestamp("2025-01-01") + pd.to_timedelta(np.sort(rng.integers(0, 365, k)), unit="D")
    a = np.round(rng.lognormal(8.3, 0.6, k), -1).astype(int)
    for dd, aa in zip(d, a):
        oid += 1
        rows.append((oid, cid, dd, aa))
orders = pd.DataFrame(rows, columns=["order_id", "customer_id", "order_date", "amount"])
cust.assign(joined_on=cust.joined_on.dt.strftime("%Y-%m-%d")).to_csv(DATA / "customers.csv", index=False)
orders.assign(order_date=orders.order_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "orders.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("customers", cust); con.register("orders", orders)
qs = [q.strip() for q in (SQL / "02_left_join_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
res = {k: con.execute(q).df().sort_values("customer_id").reset_index(drop=True) for k, q in zip(["W0", "W1", "W2"], qs)}

# pandas で同じものを作って突き合わせる
lo, hi = pd.Timestamp("2025-07-01"), pd.Timestamp("2026-01-01")
inp = orders[(orders.order_date >= lo) & (orders.order_date < hi)]
w0 = cust[["customer_id"]].merge(inp.groupby("customer_id").amount.agg(["sum", "count"]).reset_index(), how="left").fillna(0)
assert len(res["W0"]) == N_CUST and int(res["W0"].amount.sum()) == int(w0["sum"].sum())
assert len(res["W1"]) == inp.customer_id.nunique()
no_order = set(cust.customer_id) - set(orders.customer_id)
assert len(res["W2"]) == inp.customer_id.nunique() + len(no_order)

tot = int(res["W0"].amount.sum())
summ = {}
for k, df in res.items():
    summ[k] = {"customers": int(len(df)), "missing": int(N_CUST - len(df)), "missing_pct": round(100 * (N_CUST - len(df)) / N_CUST, 2),
               "zero_customers": int((df.amount == 0).sum()), "total": int(df.amount.sum()),
               "avg_per_customer": round(float(df.amount.mean()), 1)}
only_outside = int(len(set(orders.customer_id) - set(inp.customer_id)))
pd.DataFrame(summ).T.to_csv(RES / "summary.csv")

# 期間の長さを変える（期間の最後は12月末にそろえる）
win = []
for m in range(1, 13):
    lo_m = pd.Timestamp(2025, 13 - m, 1)
    q1 = f"""SELECT COUNT(*) FROM (SELECT c.customer_id FROM customers c LEFT JOIN orders o ON o.customer_id=c.customer_id
             WHERE o.order_date >= DATE '{lo_m:%Y-%m-%d}' AND o.order_date < DATE '2026-01-01' GROUP BY c.customer_id)"""
    q2 = f"""SELECT COUNT(*) FROM (SELECT c.customer_id FROM customers c LEFT JOIN orders o ON o.customer_id=c.customer_id
             WHERE (o.order_date >= DATE '{lo_m:%Y-%m-%d}' AND o.order_date < DATE '2026-01-01') OR o.order_id IS NULL GROUP BY c.customer_id)"""
    n1 = con.execute(q1).fetchone()[0]; n2 = con.execute(q2).fetchone()[0]
    sub = res["W0"]
    win.append({"months": m, "W1_missing_pct": round(100 * (N_CUST - n1) / N_CUST, 2), "W2_missing_pct": round(100 * (N_CUST - n2) / N_CUST, 2)})
win = pd.DataFrame(win); win.to_csv(RES / "by_window.csv", index=False)

out = {"customers": N_CUST, "orders": int(len(orders)), "customers_no_order_2025": len(no_order),
       "customers_only_outside_period": only_outside, "period": "2025-07-01〜2025-12-31", "total_W0": tot, "summary": summ,
       "avg_ratio_W1_vs_W0": round(summ["W1"]["avg_per_customer"] / summ["W0"]["avg_per_customer"], 3),
       "avg_ratio_W2_vs_W0": round(summ["W2"]["avg_per_customer"] / summ["W0"]["avg_per_customer"], 3),
       "by_window": win.to_dict(orient="records")}
json.dump(out, open(RES / "a601_main.json", "w"), ensure_ascii=False, indent=1)

lab = {"W0": "条件を ON に置く（正しい）", "W1": "条件を WHERE に置く", "W2": "WHERE に OR … IS NULL を足す"}
col = {"W0": GREEN, "W1": ORANGE, "W2": BLUE}
ks = ["W0", "W1", "W2"]
# 図1：残った顧客の数（内訳）
fig, ax = plt.subplots(figsize=(8.5, 3.6))
for i, k in enumerate(ks[::-1]):
    s = summ[k]; pos = s["customers"] - s["zero_customers"]
    ax.barh(i, pos, color=col[k]); ax.barh(i, s["zero_customers"], left=pos, color=LIGHT)
    ax.text(N_CUST * 1.01, i, f"{s['customers']:,}人（{s['missing']:,}人が消えた）", va="center", fontsize=9)
ax.axvline(N_CUST, color=GRAY, lw=0.8, ls=":")
ax.set_yticks(range(3)); ax.set_yticklabels([lab[k] for k in ks[::-1]]); ax.set_xlim(0, N_CUST * 1.55)
ax.set_xlabel("結果に残った顧客の数（濃い色：下期に注文あり、薄い色：金額0で残った顧客）")
ax.set_title(f"顧客{N_CUST:,}人の「下期の注文金額」：書き方で残る人数が変わる")
save(fig, "a601_customers_kept.png", SRC, y=-0.08)
# 図2：顧客あたり平均
fig, ax = plt.subplots(figsize=(7.5, 3.6))
v = [summ[k]["avg_per_customer"] for k in ks]
ax.bar([lab[k].replace("（正しい）", "\n（正しい）").replace("に置く", "に\n置く").replace("を足す", "を\n足す") for k in ks], v, color=[col[k] for k in ks])
for i, x in enumerate(v):
    ax.text(i, x, f"{x:,.0f}円\n（{x / v[0]:.2f}倍）", ha="center", va="bottom", fontsize=9)
ax.set_ylim(0, max(v) * 1.25); ax.set_ylabel("顧客1人あたりの下期の注文金額（円）")
ax.set_title("顧客1人あたりの平均：消えた顧客の分だけ高く出る")
save(fig, "a601_avg_per_customer.png", SRC, y=-0.1)
# 図3：期間の長さと消える割合
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(win.months, win.W1_missing_pct, marker="o", color=ORANGE, label=lab["W1"])
ax.plot(win.months, win.W2_missing_pct, marker="s", color=BLUE, label=lab["W2"])
ax.set_xticks(range(1, 13)); ax.set_xlabel("集計する期間の長さ（か月、12月末まで）"); ax.set_ylabel("消えた顧客の割合（%）")
ax.set_ylim(0, 100); ax.legend(frameon=False); ax.set_title("期間が短いほど、黙って消える顧客が増える")
save(fig, "a601_by_window.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
