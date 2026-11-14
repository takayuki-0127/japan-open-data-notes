"""755 時刻つきの日時のまま GROUP BY すると、日ごとの集計は何行に分かれてしまうのか

架空の1か月（2025-10）の注文。店舗の注文は日付だけ（時刻は 00:00:00）、EC の注文は秒まで入る。
同じ ordered_at 列に両方が入っている表を、日別に集計する。
  A 日時のまま GROUP BY、B 日付のカレンダー表と「=」で結合、C 日付に直して GROUP BY、
  D 文字の先頭10桁で GROUP BY、E 期間（d 以上 d+1 未満）で結合
A の行数と、B で落ちる注文を数える。DuckDB（1スレッド）と pandas で一致を確かめる。seed 755。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の注文（作成者が乱数で作成、seed 755）"
rng = np.random.default_rng(755)
days = pd.date_range("2025-10-01", "2025-10-31", freq="D")
rows = []
oid = 0
for d in days:
    wk = 1.3 if d.dayofweek >= 5 else 1.0
    n_store = rng.poisson(240 * wk); n_ec = rng.poisson(160 * (1.15 if d.dayofweek >= 5 else 1.0))
    for _ in range(n_store):
        oid += 1; rows.append((oid, "店舗", d, int(rng.lognormal(8.0, 0.6))))
    # EC：夜に多い時刻。秒まで
    hw = np.array([2, 1, 1, 1, 1, 1, 2, 3, 4, 5, 6, 6, 7, 6, 6, 6, 6, 6, 7, 8, 9, 9, 7, 4], float)
    hrs = rng.choice(24, n_ec, p=hw / hw.sum())
    for h in hrs:
        sec = int(h * 3600 + rng.integers(0, 3600))
        oid += 1; rows.append((oid, "EC", d + pd.Timedelta(seconds=sec), int(rng.lognormal(8.3, 0.6))))
O = pd.DataFrame(rows, columns=["order_id", "channel", "ordered_at", "amount"])
O.assign(ordered_at=O.ordered_at.dt.strftime("%Y-%m-%d %H:%M:%S")).to_csv(DATA / "orders.csv", index=False)
cal = pd.DataFrame({"d": days})

con = duckdb.connect(); con.execute("SET threads=1"); con.register("orders", O); con.register("calendar", cal)
q = [x for x in (SQL / "02_datetime_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
A, B, C, Dd, E = [con.execute(x).df() for x in q]
# pandas
pA = O.groupby("ordered_at").order_id.size()
pC = O.groupby(O.ordered_at.dt.normalize()).order_id.size()
pB = O[O.ordered_at.isin(days)].groupby("ordered_at").order_id.size().reindex(days, fill_value=0)
assert len(A) == len(pA) and (A.orders.values == pA.values).all()
assert (C.orders.values == pC.values).all() and (Dd.orders.values == pC.values).all() and (E.orders.values == pC.values).all()
assert (B.orders.values == pB.values).all()
n = len(O); n_ec = int((O.channel == "EC").sum())
ec_midnight = int(((O.channel == "EC") & (O.ordered_at.dt.hour == 0) & (O.ordered_at.dt.minute == 0) & (O.ordered_at.dt.second == 0)).sum())
lost_B = n - int(B.orders.sum())
out = {"days": len(days), "orders": n, "orders_ec": n_ec, "orders_store": n - n_ec, "ec_share_pct": round(n_ec / n * 100, 1),
       "rows_A_group_by_datetime": int(len(A)), "rows_C_group_by_date": int(len(C)),
       "A_rows_per_day": round(len(A) / len(days), 1),
       "A_rows_with_1_order_pct": round(float((A.orders == 1).mean() * 100), 1),
       "A_max_orders_in_a_row": int(A.orders.max()),
       "B_orders_counted": int(B.orders.sum()), "B_lost_orders": lost_B, "B_lost_pct": round(lost_B / n * 100, 1),
       "B_lost_amount_pct": round((1 - B.amount.sum() / O.amount.sum()) * 100, 1),
       "ec_orders_exactly_midnight": ec_midnight,
       "C_D_E_same": True,
       "A_first_rows_per_day_orders_mean": None}
# A を「日別」と思って、日付ごとの先頭の行だけ見た場合（よくある読み違い）
Af = A.assign(d=pd.to_datetime(A.ordered_at).dt.normalize()).groupby("d").orders.first()
out["A_first_rows_per_day_orders_mean"] = round(float(Af.mean()), 1)
out["C_orders_per_day_mean"] = round(float(C.orders.mean()), 1)
json.dump(out, open(RES / "a755_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"d": days.strftime("%Y-%m-%d"), "C_true": C.orders.values, "B_join_eq": B.orders.values,
              "A_rows": A.assign(d=pd.to_datetime(A.ordered_at).dt.normalize()).groupby("d").size().reindex(days).values}).to_csv(RES / "daily_counts.csv", index=False)

# 図1：A の行数（日ごと）
ArowsPerDay = A.assign(d=pd.to_datetime(A.ordered_at).dt.normalize()).groupby("d").size()
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(days, ArowsPerDay.reindex(days).values, color=ORANGE, width=0.8)
ax.axhline(1, color=GREEN, lw=1.5, ls="--"); ax.text(days[0], 8, "本来は1日1行", color=GREEN, fontsize=9)
ax.set_ylabel("「日別」の表の行数"); ax.set_title(f"日時のまま GROUP BY すると、31日が{len(A):,}行に分かれる")
save(fig, "a755_rows_per_day.png", SRC)
# 図2：日別の件数 C と B
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.plot(days, C.orders, color=BLUE, lw=2, marker="o", ms=3, label="C 日付に直して集計（正しい）")
ax.plot(days, B.orders, color=ORANGE, lw=2, marker="o", ms=3, ls="--", label="B カレンダーと「=」で結合")
ax.set_ylim(0, C.orders.max() * 1.25)
ax.set_ylabel("1日の注文数"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title(f"「=」で結ぶと、時刻のある EC の注文（{out['ec_share_pct']}%）がまるごと落ちる")
save(fig, "a755_join_eq.png", SRC)
# 図3：5つの方法の合計
fig, ax = plt.subplots(figsize=(7.8, 3.6))
labs = ["A 日時のまま", "B「=」で結合", "C 日付に直す", "D 先頭10桁", "E 期間で結合"]
vals = [A.orders.sum(), B.orders.sum(), C.orders.sum(), Dd.orders.sum(), E.orders.sum()]
rowsn = [len(A), len(B), len(C), len(Dd), len(E)]
ax.bar(labs, vals, color=[GRAY, ORANGE, BLUE, BLUE, BLUE])
for i, (v, r) in enumerate(zip(vals, rowsn)):
    ax.text(i, v + 150, f"{v:,}件\n{r:,}行", ha="center", fontsize=9)
ax.set_ylim(0, max(vals) * 1.25); ax.set_ylabel("注文数の合計")
ax.set_title("A は合計は合うが行が多すぎ、B は行は合うが合計が足りない")
save(fig, "a755_methods.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
