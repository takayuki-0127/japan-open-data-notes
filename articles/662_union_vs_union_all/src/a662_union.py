"""662 UNION と UNION ALL を取り違えると、何件の行が消えたり残ったりするのか

架空の2店（A・B）の売上明細（2025年1〜6月）。店ごとに別の表。B の表には、取り込みのやり直しで3日分が二重に入っている。売った時刻は分まで。
同じ日に同じ品を同じ数だけ買う客は珍しくない（安くてよく売れる品ほど）。4通りでまとめる。
  U1 店とレシートの列を落として UNION
  U2 店の列は残して UNION
  U3 UNION ALL
  U4 UNION ALL のあと、明細のキー（店・レシート番号・行番号）で1行に絞る
本当の明細は U4 と一致するはず。DuckDB（1スレッド）と pandas の一致を確かめる。seed 662。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の2店の売上明細（作成者が乱数で作成、seed 662）"
rng = np.random.default_rng(662)
items = pd.DataFrame({"item": [f"品{i + 1:02d}" for i in range(30)],
                      "price": np.round(np.exp(np.linspace(np.log(100), np.log(3000), 30)) / 10) * 10})
pop = items.price.values ** -1.0; pop /= pop.sum()
days = pd.date_range("2025-01-01", "2025-06-30")
rows = []
for st, nrec in [("A", 90), ("B", 70)]:
    rec_no = 0
    for d in days:
        k = rng.poisson(nrec * (1.15 if d.dayofweek >= 5 else 1.0))
        for _ in range(k):
            rec_no += 1
            t = d + pd.Timedelta(minutes=int(rng.integers(9 * 60, 21 * 60)))
            nl = 1 + rng.poisson(1.2)
            its = rng.choice(30, size=nl, replace=False, p=pop) if nl <= 30 else None
            for ln, it in enumerate(its, 1):
                q = 1 + rng.poisson(0.25) if items.price[it] < 500 else 1
                rows.append((st, f"{st}{rec_no:06d}", ln, t.strftime("%Y-%m-%d %H:%M"), items.item[it], int(q), int(items.price[it] * q)))
T = pd.DataFrame(rows, columns=["store_id", "receipt_no", "line_no", "sold_at", "item", "qty", "amount"])
A = T[T.store_id == "A"].reset_index(drop=True)
dup_days = ["2025-03-10", "2025-03-11", "2025-03-12"]
B = pd.concat([T[T.store_id == "B"], T[(T.store_id == "B") & T.sold_at.str[:10].isin(dup_days)]], ignore_index=True)
A.to_csv(DATA / "sales_a.csv", index=False); B.to_csv(DATA / "sales_b.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales_a", A); con.register("sales_b", B)
qs = [x for x in (SQL / "02_union_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
D = [con.execute(q).fetchone() for q in qs]
# pandas
AB = pd.concat([A, B], ignore_index=True)
P = [AB[["sold_at", "item", "qty", "amount"]].drop_duplicates(),
     AB[["store_id", "sold_at", "item", "qty", "amount"]].drop_duplicates(),
     AB,
     AB.drop_duplicates(["store_id", "receipt_no", "line_no"])]
P = [(len(x), int(x.amount.sum())) for x in P]
assert [tuple(map(int, d)) for d in D] == P, (D, P)
true_n, true_amt = len(T), int(T.amount.sum())
names = ["U1 店とレシートの列を落として UNION", "U2 店の列は残して UNION", "U3 UNION ALL", "U4 UNION ALL＋明細のキーで1行に"]
res = pd.DataFrame({"method": names, "rows": [p[0] for p in P], "amount": [p[1] for p in P]})
res["rows_diff"] = res.rows - true_n; res["amount_diff_pct"] = ((res.amount / true_amt - 1) * 100).round(3)
res.to_csv(RES / "methods.csv", index=False)
# 日ごと
def per_day(df):
    return df.groupby(df.sold_at.str[:10]).amount.sum()
pd_true = per_day(T)
u1 = per_day(P1 := AB[["sold_at", "item", "qty", "amount"]].drop_duplicates())
u3 = per_day(AB)
daily = pd.DataFrame({"true": pd_true, "U1": u1, "U3": u3})
daily["U1_pct"] = (daily.U1 / daily["true"] - 1) * 100; daily["U3_pct"] = (daily.U3 / daily["true"] - 1) * 100
daily.round(3).to_csv(RES / "daily.csv")
# 品ごと：U1 で消えた行の割合
ti = T.groupby("item").size(); ui = P1.groupby("item").size()
by_item = items.set_index("item").assign(true_rows=ti, u1_rows=ui).fillna(0)
by_item["lost_pct"] = (1 - by_item.u1_rows / by_item.true_rows) * 100
by_item.round(3).to_csv(RES / "by_item.csv")
out = {"true_rows": true_n, "true_amount": true_amt, "dup_days": dup_days, "dup_rows": int(len(B) - (T.store_id == "B").sum()),
       "methods": {n: {"rows": r, "amount": a, "rows_diff": int(r - true_n), "amount_diff_pct": round((a / true_amt - 1) * 100, 2)} for n, (r, a) in zip(names, P)},
       "U1_daily_pct_range": [round(float(daily.U1_pct.min()), 1), round(float(daily.U1_pct.max()), 1)],
       "U3_dup_day_pct": {d: round(float(daily.loc[d, "U3_pct"]), 1) for d in dup_days},
       "lost_pct_cheapest3": round(float(by_item.lost_pct.iloc[:3].mean()), 1), "lost_pct_dearest3": round(float(by_item.lost_pct.iloc[-3:].mean()), 1),
       "price_range": [int(items.price.min()), int(items.price.max())]}
json.dump(out, open(RES / "a662_main.json", "w"), ensure_ascii=False, indent=1)

# 図1
fig, ax = plt.subplots(figsize=(8.5, 3.4))
lab = ["U1 列を落として UNION", "U2 店の列を残して UNION", "U3 UNION ALL", "U4 UNION ALL＋キーで1行に"]
v = [out["methods"][n]["rows_diff"] for n in names]
ax.barh(lab[::-1], v[::-1], color=[ORANGE, ORANGE, BLUE, GREEN][::-1])
for i, x in enumerate(v[::-1]):
    ax.text(x, i, f" {x:+,}行 " if x else " ±0行", va="center", ha="left" if x >= 0 else "right", fontsize=9)
ax.axvline(0, color="black", lw=1); ax.set_xlabel(f"本当の明細（{true_n:,}行）との差（行）")
lo = min(v); ax.set_xlim(lo * 1.35, max(max(v), 1) * 1.6)
ax.set_title("UNION は同じ内容の明細を消し、UNION ALL は二重の取り込みを残す")
save(fig, "a662_methods.png", SRC, y=-0.05)
# 図2：日ごと
fig, ax = plt.subplots(figsize=(8.5, 3.6))
x = pd.to_datetime(daily.index)
ax.plot(x, daily.U1_pct, color=ORANGE, lw=1, label="U1 列を落として UNION")
ax.plot(x, daily.U3_pct, color=BLUE, lw=1, label="U3 UNION ALL")
ax.axhline(0, color="black", lw=0.8); ax.set_ylabel("本当の売上との差（%）")
ax.legend(frameon=False, fontsize=9, loc="center left"); ax.set_title("UNION は毎日少しずつ減らし、UNION ALL は二重の日だけ大きく増やす")
save(fig, "a662_daily.png", SRC)
# 図3：品ごと
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.scatter(by_item.price, by_item.lost_pct, color=ORANGE, s=22)
ax.set_xscale("log"); ax.set_xticks([100, 200, 500, 1000, 2000, 3000]); ax.set_xticklabels(["100", "200", "500", "1,000", "2,000", "3,000"]); ax.set_xlabel("品の値段（円、対数）"); ax.set_ylabel("U1 で消えた明細の割合（%）")
ax.set_title("安くてよく売れる品ほど、同じ内容の明細が多く消える")
save(fig, "a662_by_item.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
