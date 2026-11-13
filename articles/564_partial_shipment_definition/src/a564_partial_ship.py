"""564 注文を何回かに分けて出荷すると、「出荷済みの注文」の数え方でどれだけ違うのか

架空の通販の注文（2025年1〜12月、20,000件）と出荷。在庫が足りない品目は、あるぶんを先に出し、残りを後から出す（分納）。
「出荷済み」の定義を3つ比べる：
  S1 1回でも出荷した注文
  S2 全量を出荷し終えた注文
  S3 数量の比（出荷した数量 ÷ 注文した数量、注文ごとの割合を足し上げる）
月末時点の出荷率と、注文から出荷までの日数（最初の出荷まで・出荷し終えるまで）を比べる。注文の品目数で分けても見る。
Python と SQL（DuckDB、1スレッド）で月末の出荷率が一致することを確かめる。数字は置いた仮定で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の通販の注文と出荷（作成者が乱数で作成、seed 564）"
rng = np.random.default_rng(564)
N = 20000
start = pd.Timestamp("2025-01-01")
odays = np.sort(rng.integers(0, 365, N))
# 年末に向けて少し増える形は置かない（一様）。品目数は1〜6
nlines = rng.choice([1, 2, 3, 4, 5, 6], N, p=[0.45, 0.25, 0.14, 0.08, 0.05, 0.03])
orders, lines, ships = [], [], []
lid = 0
for i in range(N):
    oid = 500000 + i
    od = start + pd.Timedelta(days=int(odays[i]))
    orders.append((oid, od.date(), int(nlines[i])))
    base = int(rng.choice([1, 1, 1, 2, 2, 3]))   # ふだんの出荷までの日数
    for _ in range(nlines[i]):
        lid += 1
        q = int(rng.choice([1, 1, 1, 2, 2, 3, 5, 10]))
        lines.append((lid, oid, q))
        if rng.random() < 0.12:                  # 在庫が足りない品目
            first = int(np.floor(q * rng.uniform(0, 0.8)))   # 先に出せる数（0もある）
            back = int(rng.choice([5, 7, 10, 14, 21, 30, 45]) + rng.integers(0, 5))
            if first > 0:
                ships.append((lid, oid, (od + pd.Timedelta(days=base)).date(), first))
            if rng.random() < 0.97:              # 3%は年をまたいでも出ない（取り消し前）
                ships.append((lid, oid, (od + pd.Timedelta(days=base + back)).date(), q - first))
        else:
            ships.append((lid, oid, (od + pd.Timedelta(days=base)).date(), q))
O = pd.DataFrame(orders, columns=["order_id", "order_date", "n_lines"])
L = pd.DataFrame(lines, columns=["line_id", "order_id", "qty"])
Sh = pd.DataFrame(ships, columns=["line_id", "order_id", "ship_date", "ship_qty"])
O[["order_id", "order_date"]].to_csv(DATA / "orders.csv", index=False)
L.to_csv(DATA / "order_lines.csv", index=False)
Sh.to_csv(DATA / "shipments.csv", index=False)

O["order_date"] = pd.to_datetime(O.order_date)
Sh["ship_date"] = pd.to_datetime(Sh.ship_date)
oq = L.groupby("order_id").qty.sum()


def snapshot(asof):
    """asof の日の終わり時点。その日までに受けた注文について、3つの定義の出荷率"""
    o = O[O.order_date <= asof].set_index("order_id")
    s = Sh[Sh.ship_date <= asof].groupby("order_id").ship_qty.sum()
    shipped = s.reindex(o.index).fillna(0)
    ratio = shipped / oq.reindex(o.index)
    return {"orders": len(o), "S1": float((shipped > 0).mean()), "S2": float((ratio >= 1).mean()), "S3": float(ratio.mean())}


month_ends = pd.date_range("2025-01-31", "2025-12-31", freq="ME")
# 月末時点、その月に受けた注文だけで出す（ふだんの月次報告の形）
rec = []
for me in month_ends:
    ms = me.replace(day=1)
    o = O[(O.order_date >= ms) & (O.order_date <= me)].set_index("order_id")
    s = Sh[Sh.ship_date <= me].groupby("order_id").ship_qty.sum()
    shipped = s.reindex(o.index).fillna(0)
    ratio = shipped / oq.reindex(o.index)
    rec.append({"month": me.strftime("%Y-%m"), "orders": len(o), "S1": round(100 * float((shipped > 0).mean()), 2),
                "S2": round(100 * float((ratio >= 1).mean()), 2), "S3": round(100 * float(ratio.mean()), 2)})
M = pd.DataFrame(rec)
M.to_csv(RES / "month_end_rate.csv", index=False)

# 注文ごとの出荷までの日数
fs = Sh.groupby("order_id").ship_date.min()
cum = Sh.sort_values("ship_date").groupby(["order_id", "ship_date"]).ship_qty.sum().groupby(level=0).cumsum().reset_index()
cum = cum.merge(oq.rename("oq"), left_on="order_id", right_index=True)
full = cum[cum.ship_qty >= cum.oq].groupby("order_id").ship_date.min()
D = O.set_index("order_id")
D["first_days"] = (fs.reindex(D.index) - D.order_date).dt.days
D["full_days"] = (full.reindex(D.index) - D.order_date).dt.days
D["partial"] = Sh.groupby("order_id").ship_date.nunique().reindex(D.index).fillna(0) > 1
D.reset_index()[["order_id", "n_lines", "first_days", "full_days", "partial"]].to_csv(RES / "order_days.csv", index=False)


def st(x):
    x = x.dropna()
    return {"n": int(len(x)), "mean": round(float(x.mean()), 2), "median": float(x.median()), "p90": float(x.quantile(0.9))}


by_lines = []
for k in range(1, 7):
    q = D[D.n_lines == k]
    by_lines.append({"n_lines": k, "orders": len(q), "partial_pct": round(100 * float(q.partial.mean()), 1),
                     "first_mean": round(float(q.first_days.mean()), 2), "full_mean": round(float(q.full_days.mean()), 2),
                     "never_full_pct": round(100 * float(q.full_days.isna().mean()), 2)})
BL = pd.DataFrame(by_lines)
BL.to_csv(RES / "by_n_lines.csv", index=False)

# SQL（DuckDB）で月末の出荷率
con = duckdb.connect()
con.execute("SET threads=1")
for t in ["orders", "order_lines", "shipments"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{DATA / (t + '.csv')}')")
sql = (SQL / "02_ship_rate_duckdb.sql").read_text()
for r in M.itertuples():
    me = pd.Timestamp(r.month + "-01") + pd.offsets.MonthEnd(0)
    v = con.execute(sql.replace(":month_start", (me.replace(day=1)).strftime("%Y-%m-%d")).replace(":asof", me.strftime("%Y-%m-%d"))).fetchone()
    assert int(v[0]) == r.orders and abs(100 * v[1] - r.S1) < 0.006 and abs(100 * v[2] - r.S2) < 0.006 and abs(100 * v[3] - r.S3) < 0.006, (r, v)

summary = {"orders": N, "lines": len(L), "shipments": len(Sh), "orders_partial_pct": round(100 * float(D.partial.mean()), 2),
           "orders_never_full_pct": round(100 * float(D.full_days.isna().mean()), 2),
           "month_end": {"S1_mean": round(float(M.S1.mean()), 2), "S2_mean": round(float(M.S2.mean()), 2), "S3_mean": round(float(M.S3.mean()), 2),
                         "S1_minus_S2_range": [round(float((M.S1 - M.S2).min()), 2), round(float((M.S1 - M.S2).max()), 2)]},
           "days_first": st(D.first_days), "days_full": st(D.full_days),
           "days_partial_only": {"first": st(D[D.partial].first_days), "full": st(D[D.partial].full_days)},
           "by_n_lines": by_lines, "year_end_snapshot_all_orders": {k: (round(100 * v, 2) if k != "orders" else v) for k, v in snapshot(pd.Timestamp("2025-12-31")).items()},
           "sql_python_match": True}
json.dump(summary, open(RES / "a564_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

COL = {"S1": BLUE, "S2": ORANGE, "S3": GREEN}
LAB = {"S1": "S1 1回でも出荷", "S2": "S2 全量出荷", "S3": "S3 数量の比"}
# 図1：月末の出荷率
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = np.arange(len(M))
for k in ["S1", "S3", "S2"]:
    ax.plot(x, M[k], marker="o", color=COL[k], label=LAB[k])
ax.set_xticks(x, [m[5:] + "月" for m in M.month])
ax.set_ylabel("その月に受けた注文の出荷率（%）")
ax.set_title("月末時点の出荷率（その月に受けた注文）", loc="left")
ax.legend(frameon=False, fontsize=9)
save(fig, "a564_month_end.png", SRC)

# 図2：出荷までの日数（分納のあった注文）
fig, ax = plt.subplots(figsize=(8, 4))
P = D[D.partial]
bins = np.arange(0, 61, 2)
ax.hist(P.first_days.clip(upper=60), bins=bins, color=BLUE, alpha=0.75, label=f"最初の出荷まで（平均 {P.first_days.mean():.1f}日）")
ax.hist(P.full_days.dropna().clip(upper=60), bins=bins, color=ORANGE, alpha=0.6, label=f"出荷し終えるまで（平均 {P.full_days.mean():.1f}日）")
ax.set_xlabel("注文から出荷までの日数（60日以上は60にまとめた）")
ax.set_ylabel("注文の数")
ax.set_title(f"分納のあった注文 {len(P):,}件の、出荷までの日数", loc="left")
ax.legend(frameon=False, fontsize=9)
save(fig, "a564_days.png", SRC)

# 図3：品目数別
fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.9))
axs[0].bar(BL.n_lines, BL.partial_pct, color=BLUE)
for a, b in zip(BL.n_lines, BL.partial_pct):
    axs[0].text(a, b, f"{b:.0f}%", ha="center", va="bottom", fontsize=9)
axs[0].set_xlabel("注文の品目数"); axs[0].set_ylabel("分納になった注文の割合（%）")
axs[0].set_title("品目が多いほど分納になる", loc="left", fontsize=11)
axs[1].plot(BL.n_lines, BL.first_mean, marker="o", color=BLUE, label="最初の出荷まで")
axs[1].plot(BL.n_lines, BL.full_mean, marker="o", color=ORANGE, label="出荷し終えるまで")
axs[1].set_xlabel("注文の品目数"); axs[1].set_ylabel("平均日数")
axs[1].set_title("出荷までの平均日数", loc="left", fontsize=11)
axs[1].legend(frameon=False, fontsize=9)
save(fig, "a564_by_lines.png", SRC)
