"""795 月の数字を週に直すとき4で割るか4.33で割るかで、週あたりの値はどれだけ違うのか

架空の店の日次売上（2024〜2025年の2年、土日が多い曜日の波あり、伸びなし）。
月の売上を週あたりに直す方法を3通り（4で割る・4.33で割る・その月の日数÷7で割る）比べ、
本当の週の売上（月〜日の週の合計の平均。週の木曜日が入る月に数える）とのずれを月ごとに出す。
逆向き（週の目標×4で月の目標にする）のずれも出す。DuckDB（1スレッド）と pandas の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の店の日次売上（作成者が乱数で作成、seed 795）"
rng = np.random.default_rng(795)
days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
dow = np.array([1.0, .9, .9, .95, 1.1, 1.5, 1.4])
sales = np.round(100000 * dow[days.dayofweek] * rng.lognormal(0, .08, len(days)), -2)
D = pd.DataFrame({"sale_date": days.date, "sales": sales.astype(int)})
DATA.mkdir(exist_ok=True); D.to_csv(DATA / "daily_sales.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily_sales", D.assign(sale_date=pd.to_datetime(D.sale_date)))
q = "\n".join(l for l in (SQL / "02_weekly_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
dd = pd.to_datetime(D.sale_date); D["ym"] = dd.dt.strftime("%Y-%m")
P = D.groupby("ym").agg(days=("sales", "size"), month_sales=("sales", "sum")).reset_index()
assert (P.ym.values == Q.ym.values).all() and (P.month_sales.values == Q.month_sales.values).all()
assert np.allclose(Q.per_week_div433, P.month_sales / (52 / 12)) and np.allclose(Q.per_week_days, P.month_sales / (P.days / 7))

# 本当の週の売上：月〜日の週の合計を、その週の木曜日が入る月に数えて平均
wk = D.assign(week_start=(dd - pd.to_timedelta(dd.dt.dayofweek, unit="D")))
W = wk.groupby("week_start").agg(s=("sales", "sum"), n=("sales", "size")).reset_index()
W = W[W.n == 7]; W["ym"] = (W.week_start + pd.Timedelta(days=3)).dt.strftime("%Y-%m")
Wm = W.groupby("ym").agg(actual_week=("s", "mean"), weeks=("s", "size")).reset_index()
Q = Q.merge(Wm, on="ym")
for c in ["per_week_div4", "per_week_div433", "per_week_days"]: Q[f"gap_{c[9:]}"] = Q[c] / Q.actual_week - 1
Q["month"] = Q.ym.str[5:].astype(int)
Q["sat_sun"] = [int(((pd.to_datetime(D[D.ym == y].sale_date).dt.dayofweek) >= 5).sum()) for y in Q.ym]
Q.to_csv(RES / "by_month.csv", index=False)
avg_week = float(W.s.mean())
out = {"months": len(Q), "avg_actual_week": avg_week,
       "mean_gap": {k: float(Q[f"gap_{k}"].mean()) for k in ["div4", "div433", "days"]},
       "max_abs_gap": {k: float(Q[f"gap_{k}"].abs().max()) for k in ["div4", "div433", "days"]},
       "feb_gap": {k: float(Q[Q.month == 2][f"gap_{k}"].mean()) for k in ["div4", "div433", "days"]},
       "m31_gap_div4": float(Q[Q.days == 31].gap_div4.mean()), "m30_gap_div4": float(Q[Q.days == 30].gap_div4.mean()),
       "weekly_target_x4_short": float(1 - 4 / (365.25 / 12 / 7)), "weekly_target_x433_short": float(1 - (52 / 12) / (365.25 / 12 / 7)),
       "sat_sun_range": [int(Q.sat_sun.min()), int(Q.sat_sun.max())],
       "days_gap_by_satsun": Q.groupby("sat_sun").gap_days.mean().round(4).to_dict(),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a795_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：月ごとのずれ（3通り）
fig, ax = plt.subplots(figsize=(10, 4.6)); x = np.arange(len(Q))
for c, col, l in [("gap_div4", ORANGE, "4で割る"), ("gap_div433", GRAY, "4.33で割る"), ("gap_days", BLUE, "日数÷7で割る")]:
    ax.plot(x, Q[c] * 100, "o-", color=col, label=l, ms=4)
ax.axhline(0, color="#0b0b0b", lw=.8); ax.set_xticks(x[::2]); ax.set_xticklabels(Q.ym[::2], rotation=45, fontsize=9)
ax.set_ylabel("本当の週の売上とのずれ（%）"); ax.legend(frameon=False, ncol=3)
ax.set_title("4で割るといつも高く、4.33で割ると2月だけ大きく低く出る（24か月）")
save(fig, "a795_by_month.png", SRC)

# 図2：月の日数ごとの平均のずれ
fig, ax = plt.subplots(figsize=(8.5, 4.4)); g = Q.groupby("days")[["gap_div4", "gap_div433", "gap_days"]].mean(); xi = np.arange(len(g)); w = .27
for j, (c, col, l) in enumerate([("gap_div4", ORANGE, "4で割る"), ("gap_div433", GRAY, "4.33で割る"), ("gap_days", BLUE, "日数÷7で割る")]):
    ax.bar(xi + (j - 1) * w, g[c] * 100, w, color=col, label=l)
    for xx, v in zip(xi, g[c]): ax.text(xx + (j - 1) * w, v * 100 + (.3 if v >= 0 else -.3), f"{v*100:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color="#0b0b0b", lw=.8); ax.set_xticks(xi); ax.set_xticklabels([f"{d}日の月" for d in g.index])
ax.set_ylabel("ずれの平均（%）"); ax.legend(frameon=False); ax.set_title("ずれは月の日数で決まる。日数÷7で割ると、日数の違いは消える")
save(fig, "a795_by_days.png", SRC)

# 図3：日数÷7でも残るずれ（土日の数）
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.scatter(Q.sat_sun, Q.gap_days * 100, color=BLUE, s=30)
for s, v in Q.groupby("sat_sun").gap_days.mean().items(): ax.plot([s - .2, s + .2], [v * 100] * 2, color="#0b0b0b", lw=2)
ax.axhline(0, color=GRAY, lw=.8); ax.set_xticks(sorted(Q.sat_sun.unique())); ax.set_xlabel("その月の土日の日数"); ax.set_ylabel("日数÷7で割ったときのずれ（%）")
ax.set_title("日数÷7で割っても、土日が多い月は高く、少ない月は低く出る（黒線は平均）")
save(fig, "a795_weekend.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
