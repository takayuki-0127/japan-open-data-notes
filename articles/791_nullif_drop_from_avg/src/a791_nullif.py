"""791 0で割るのを NULLIF で避けると、その店は平均から黙って消え、全体の率はどれだけ変わるのか

架空の60店×30日の来店数と申込み数。来店の少ない店ほど、来店0の日が多い。2店は月の間ずっと改装で来店0。
申込み率（申込み÷来店）を、
  NULLIF のまま平均：来店0の日（と、ずっと来店0の店）は NULL になり、AVG から黙って外れる
  0として平均：来店0の日を率0として数える
  合計から率：申込みの合計÷来店の合計
で出し、店の平均・全体の率・消えた日と店を数える。DuckDB（1スレッド）と pandas の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の店の来店数と申込み数（作成者が乱数で作成、seed 791）"
rng = np.random.default_rng(791)
NS, ND = 60, 30
mu = np.exp(rng.uniform(np.log(0.6), np.log(40), NS))       # 1日の来店の平均（0.6〜40人）
p = np.clip(rng.normal(.12, .03, NS), .03, .25)              # 店ごとの本当の申込み率
closed = {7, 41}                                              # 月の間ずっと改装中（来店0）
rows = []
for s in range(NS):
    for d in range(ND):
        v = 0 if s in closed else int(rng.poisson(mu[s]))
        rows.append((f"T{s+1:02d}", f"2025-09-{d+1:02d}", v, int(rng.binomial(v, p[s]))))
D = pd.DataFrame(rows, columns=["store_id", "day", "visits", "applications"])
DATA.mkdir(exist_ok=True); D.to_csv(DATA / "daily.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("daily", D)
q = "\n".join(l for l in (SQL / "02_rate_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
D["r"] = np.where(D.visits > 0, D.applications / D.visits.where(D.visits > 0), np.nan)
P = D.groupby("store_id").agg(days=("r", "size"), days_used=("r", "count"), avg_daily_nullif=("r", "mean"),
                              avg_daily_zero=("r", lambda s: s.fillna(0).mean()),
                              a=("applications", "sum"), v=("visits", "sum")).reset_index()
P["rate_total"] = P.a / P.v.where(P.v > 0)
for c in ["days_used", "avg_daily_nullif", "avg_daily_zero", "rate_total"]:
    assert np.allclose(Q[c].astype(float).fillna(-1), P[c].astype(float).fillna(-1)), c
Q["mean_visits"] = mu; Q["true_p"] = p
Q.to_csv(RES / "by_store.csv", index=False)

# 全体の数字
all_nullif = float(con.execute("SELECT AVG(applications*1.0/NULLIF(visits,0)) FROM daily").fetchone()[0])
all_zero = float(con.execute("SELECT AVG(COALESCE(applications*1.0/NULLIF(visits,0),0)) FROM daily").fetchone()[0])
all_total = float(D.applications.sum() / D.visits.sum())
store_mean_nullif = float(Q.avg_daily_nullif.mean())         # AVG は NULL の店を飛ばす
store_mean_zero = float(Q.avg_daily_zero.mean())
dropped_days = int((D.visits == 0).sum()); dropped_stores = int(Q.avg_daily_nullif.isna().sum())
small = Q.mean_visits < 2
out = {"stores": NS, "days": ND, "rows": len(D), "zero_visit_days": dropped_days, "zero_visit_share": dropped_days / len(D),
       "stores_all_null": dropped_stores, "stores_in_avg_nullif": int(Q.avg_daily_nullif.notna().sum()),
       "overall_avg_nullif": all_nullif, "overall_avg_zero": all_zero, "overall_total": all_total,
       "true_mean_p": float(p.mean()), "true_weighted_p": float((p * mu * np.array([0 if i in closed else 1 for i in range(NS)])).sum() / (mu * np.array([0 if i in closed else 1 for i in range(NS)])).sum()),
       "store_mean_nullif": store_mean_nullif, "store_mean_zero": store_mean_zero,
       "small_stores": int(small.sum()), "small_days_used_share": float(Q[small].days_used.sum() / Q[small].days.sum()),
       "small_avg_nullif_mean": float(Q[small].avg_daily_nullif.mean()), "small_avg_zero_mean": float(Q[small].avg_daily_zero.mean()),
       "small_rate_total_mean": float(Q[small].rate_total.mean()),
       "max_store_avg_nullif": float(Q.avg_daily_nullif.max()),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a791_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：全体の率（3通り）
fig, ax = plt.subplots(figsize=(8.5, 4.4))
lab = ["日ごとの率の平均\n（NULLIF のまま）", "日ごとの率の平均\n（来店0の日を0）", "合計から率\n（申込み計÷来店計）"]
vals = [all_nullif, all_zero, all_total]
ax.bar(range(3), vals, color=[ORANGE, GRAY, BLUE])
for i, v in enumerate(vals): ax.text(i, v + .003, f"{v:.1%}", ha="center", fontsize=11)
ax.set_xticks(range(3)); ax.set_xticklabels(lab); ax.set_ylabel("申込み率"); ax.set_ylim(0, max(vals) * 1.2)
ax.set_title(f"同じデータでも、全体の率は出し方で{min(vals):.1%}〜{max(vals):.1%}になる（60店×30日）")
save(fig, "a791_overall.png", SRC)

# 図2：店の来店の多さと、使われた日の割合
fig, ax = plt.subplots(figsize=(8.5, 4.6))
q2 = Q[~Q.store_id.isin([f"T{s+1:02d}" for s in closed])]
ax.scatter(q2.mean_visits, q2.days_used / q2.days, color=ORANGE, s=25)
ax.set_xscale("log"); ax.set_xlabel("1日の来店の平均（人、対数）"); ax.set_ylabel("NULLIF の平均に使われた日の割合")
ax.set_ylim(0, 1.05); ax.set_title(f"来店の少ない店ほど、平均から黙って外れる日が多い（来店0の日は全体の{out['zero_visit_share']:.0%}）")
ax.text(.03, .05, f"ずっと来店0の{dropped_stores}店は、平均から店ごと消えた", transform=ax.transAxes, fontsize=10, color=GRAY)
save(fig, "a791_days_used.png", SRC)

# 図3：店ごとの3つの率と本当の率
fig, ax = plt.subplots(figsize=(8.5, 4.6))
o = q2.sort_values("mean_visits")
ax.plot(range(len(o)), o.true_p, color="#0b0b0b", lw=1.5, label="本当の率")
ax.scatter(range(len(o)), o.avg_daily_nullif, color=ORANGE, s=16, label="日ごとの率の平均（NULLIF のまま）")
ax.scatter(range(len(o)), o.avg_daily_zero, color=GRAY, s=16, label="日ごとの率の平均（0として）")
ax.scatter(range(len(o)), o.rate_total, color=BLUE, s=16, label="合計から率")
ax.set_xlabel("店（左ほど来店が少ない）"); ax.set_ylabel("申込み率"); ax.legend(frameon=False, fontsize=9)
ax.set_title("来店の少ない店では、日ごとの率の平均が大きく振れる。0として数えると下に引っぱられる")
save(fig, "a791_by_store.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
