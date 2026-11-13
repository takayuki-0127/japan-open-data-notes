"""632 マスタは今日、明細は昨日の時点の表をつなぐと、何件が片方にしかないのか

架空の通販の顧客と注文の30日分。はじめの顧客は5万人。毎日 約300人が登録し（登録した人の6割は1時間以内に初めて注文する）、
約40人が退会してマスタから消える（退会の前の数日に注文していることがある）。地域を変える人も毎日 約30人いる。
毎日の夜（24時）に、その日の注文をマスタとつないで地域別の売上を出す。マスタを取り出す時刻を注文から
−24時間・−6時間・0・+6時間・+24時間ずらし、内部結合で落ちた注文と、地域が違ってつながった注文を数える。
1日分は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた登録・退会・地域変更の多さで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の通販の顧客と注文（作成者が乱数で作成、seed 632）"
rng = np.random.default_rng(632)
DAYS, N0 = 30, 50_000
REG = ["北", "東", "中", "西", "南"]
H = 3600.0
# 顧客：作成時刻・退会時刻・地域の履歴
cust = pd.DataFrame({"customer_id": np.arange(1, N0 + 1), "created": -1e9, "deleted": np.inf})
reg_hist = [pd.DataFrame({"customer_id": cust.customer_id, "from": -1e9, "region": rng.choice(REG, N0)})]
nid = N0
new_rows = []
for d in range(DAYS):
    k = rng.poisson(300); t = d * 24 * H + rng.uniform(0, 24 * H, k)
    ids = np.arange(nid + 1, nid + k + 1); nid += k
    new_rows.append(pd.DataFrame({"customer_id": ids, "created": t, "deleted": np.inf}))
    reg_hist.append(pd.DataFrame({"customer_id": ids, "from": t, "region": rng.choice(REG, k)}))
cust = pd.concat([cust] + new_rows, ignore_index=True)
for d in range(DAYS):
    alive = cust[(cust.created < d * 24 * H) & np.isinf(cust.deleted)]
    dl = rng.choice(alive.customer_id.to_numpy(), rng.poisson(40), replace=False)
    cust.loc[cust.customer_id.isin(dl), "deleted"] = d * 24 * H + rng.uniform(0, 24 * H, len(dl))
    mv = rng.choice(alive.customer_id.to_numpy(), rng.poisson(30), replace=False)
    reg_hist.append(pd.DataFrame({"customer_id": mv, "from": d * 24 * H + rng.uniform(0, 24 * H, len(mv)), "region": rng.choice(REG, len(mv))}))
RH = pd.concat(reg_hist, ignore_index=True).sort_values(["customer_id", "from"]).reset_index(drop=True)
# 注文
orders = []
oid = 0
for d in range(DAYS):
    t0, t1 = d * 24 * H, (d + 1) * 24 * H
    alive = cust[(cust.created < t1) & (cust.deleted > t0)]
    # ふだんの注文：1日約3,000件、その時刻に生きている顧客から
    m = rng.poisson(3000); t = rng.uniform(t0, t1, m)
    who = rng.choice(alive.customer_id.to_numpy(), m)
    cr = cust.set_index("customer_id").loc[who]
    ok = (cr.created.to_numpy() < t) & (cr.deleted.to_numpy() > t)
    orders.append(pd.DataFrame({"customer_id": who[ok], "ordered_at": t[ok]}))
    # 登録してすぐの注文
    nw = cust[(cust.created >= t0) & (cust.created < t1)]
    first = nw[rng.random(len(nw)) < 0.6]
    orders.append(pd.DataFrame({"customer_id": first.customer_id.to_numpy(), "ordered_at": np.minimum(first.created.to_numpy() + rng.uniform(60, H, len(first)), t1 - 1)}))
    # 退会の直前の注文
    dd = cust[(cust.deleted >= t0) & (cust.deleted < t1)]
    last = dd[rng.random(len(dd)) < 0.3]
    orders.append(pd.DataFrame({"customer_id": last.customer_id.to_numpy(), "ordered_at": np.maximum(last.deleted.to_numpy() - rng.uniform(60, 6 * H, len(last)), t0)}))
O = pd.concat(orders, ignore_index=True)
O["amount"] = np.round(rng.gamma(2, 2500, len(O)), -1).astype(int)
O["day"] = (O.ordered_at // (24 * H)).astype(int)
O["order_id"] = np.arange(1, len(O) + 1)


def master_at(ts):
    m = cust[(cust.created <= ts) & (cust.deleted > ts)][["customer_id"]]
    r = RH[RH["from"] <= ts].groupby("customer_id").region.last()
    return m.assign(region=m.customer_id.map(r))


def region_at_order(o):
    r = pd.merge_asof(o.sort_values("ordered_at"), RH.rename(columns={"from": "ordered_at"}).sort_values("ordered_at"),
                      on="ordered_at", by="customer_id", direction="backward")
    return r.set_index("order_id").region


LAGS = [-24, -6, 0, 6, 24]
rows = []
for d in range(1, DAYS - 1):
    od = O[O.day == d]
    true_reg = region_at_order(od)
    for lag in LAGS:
        ts = (d + 1) * 24 * H + lag * H
        m = master_at(ts)
        j = od.merge(m, on="customer_id", how="left")
        miss = j.region.isna()
        created_after = od.customer_id.map(cust.set_index("customer_id").created) > ts
        rows.append({"day": d, "lag_h": lag, "orders": len(od), "amount": int(od.amount.sum()),
                     "missing": int(miss.sum()), "missing_amt": int(j.amount[miss.to_numpy()].sum()),
                     "missing_new": int((miss.to_numpy() & created_after.to_numpy()).sum()), "missing_deleted": int((miss.to_numpy() & ~created_after.to_numpy()).sum()),
                     "region_differs": int(((j.region.to_numpy() != true_reg.reindex(j.order_id).to_numpy()) & ~miss.to_numpy()).sum())})
R = pd.DataFrame(rows)
R.to_csv(RES / "by_day_lag.csv", index=False)
S = R.groupby("lag_h").agg(orders=("orders", "mean"), missing=("missing", "mean"), missing_new=("missing_new", "mean"),
                           missing_deleted=("missing_deleted", "mean"), region_differs=("region_differs", "mean"),
                           missing_amt=("missing_amt", "sum"), amount=("amount", "sum")).reset_index()
S["missing_pct"] = 100 * S.missing / S.orders; S["missing_amt_pct"] = 100 * S.missing_amt / S.amount
S.round(3).to_csv(RES / "summary.csv", index=False)

# SQL：15日目、マスタが6時間前
d, lag = 15, -6
od = O[O.day == d][["order_id", "customer_id", "ordered_at", "amount"]]
m = master_at((d + 1) * 24 * H + lag * H)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("orders_snap", od); con.register("customers_snap", m)
qs = [q.strip() for q in (SQL / "02_snapshot_join_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
r1 = con.execute(qs[0][qs[0].index("SELECT"):]).fetchone(); r2 = con.execute(qs[1][qs[1].index("SELECT"):]).fetchone()
rr = R[(R.day == d) & (R.lag_h == lag)].iloc[0]
assert r2[0] == rr.orders and r2[2] == rr.missing and r1[0] == rr.orders - rr.missing and int(r1[1]) == rr.amount - rr.missing_amt
pd.DataFrame([{"day": d, "lag_h": lag, "inner_n": r1[0], "inner_amt": int(r1[1]), "left_n": r2[0], "left_amt": int(r2[1]), "unknown": r2[2]}]).to_csv(RES / "sql_example.csv", index=False)

out = {"days_measured": int(R.day.nunique()), "customers_start": N0, "orders_total": int(len(O)), "summary": S.round(3).to_dict(orient="records")}
json.dump(out, open(RES / "a632_main.json", "w"), ensure_ascii=False, indent=1)

xl = [f"{l:+d}時間" if l else "同じ時刻" for l in LAGS]
# 図1
fig, ax = plt.subplots(figsize=(8.5, 4.2))
xs = np.arange(len(LAGS))
ax.bar(xs, S.missing_new, color=BLUE, label="マスタを取った後に登録した顧客")
ax.bar(xs, S.missing_deleted, bottom=S.missing_new, color=ORANGE, label="マスタを取る前に退会した顧客")
for x, v, p in zip(xs, S.missing, S.missing_pct):
    ax.text(x, v + 2, f"{v:.0f}件\n（{p:.2f}%）", ha="center", fontsize=8.5)
ax.set_xticks(xs); ax.set_xticklabels(xl); ax.set_xlabel("マスタを取り出した時刻（注文の締めとの差）")
ax.set_ylabel("内部結合で落ちる注文（1日あたり）"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, S.missing.max() * 1.35)
ax.set_title("注文は24時の締め、マスタは別の時刻のとき、つながらない注文")
save(fig, "a632_missing.png", SRC)

# 図2：日ごと（−24時間）
fig, ax = plt.subplots(figsize=(8.5, 4))
for lag, c in [(-24, ORANGE), (-6, BLUE), (0, GRAY), (24, GREEN)]:
    s = R[R.lag_h == lag]
    ax.plot(s.day + 1, s.missing, marker="o", ms=3, color=c, label=xl[LAGS.index(lag)])
ax.set_xlabel("日"); ax.set_ylabel("落ちる注文（件）"); ax.legend(frameon=False, fontsize=9, ncol=4)
ax.set_title("日ごとの落ちる注文の数")
save(fig, "a632_by_day.png", SRC)

# 図3：地域の違い
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.bar(xs, S.region_differs, color=LIGHT)
for x, v in zip(xs, S.region_differs):
    ax.text(x, v + 0.3, f"{v:.1f}件", ha="center", fontsize=9)
ax.set_xticks(xs); ax.set_xticklabels(xl); ax.set_ylabel("注文時と違う地域でつながった注文（1日あたり）")
ax.set_title("つながった注文のうち、注文したときとは違う地域で数えたもの")
save(fig, "a632_region.png", SRC)
print(S.round(2).to_string()); print(len(O))
