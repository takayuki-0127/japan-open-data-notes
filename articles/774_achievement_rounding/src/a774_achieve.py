"""774 達成率を四捨五入してから「100%以上」を数えると、何店が「達成」に入ってしまうのか

架空の200店×12か月。目標（円）は店ごとに決め、実績は目標×(1＋ばらつき)（達成率の平均100%、標準偏差6ポイント）。
達成店を「実績≧目標」で数える場合と、達成率を整数の%・小数1桁の%に四捨五入してから「100%以上」で数える場合を比べる。
DuckDB（1スレッド）の結果と Python の結果の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の店の目標と実績（作成者が乱数で作成、seed 774）"
rng = np.random.default_rng(774)
S, M = 200, 12
base = rng.integers(300, 1500, S) * 10_000
rows = []
for m in range(1, M + 1):
    t = (base * rng.uniform(.95, 1.05, S)).round(-3).astype(np.int64)
    a = np.round(t * (1 + rng.normal(0, .06, S))).astype(np.int64)
    rows.append(pd.DataFrame({"month": f"2025-{m:02d}", "store_id": np.arange(1, S + 1), "target": t, "actual": a}))
D = pd.concat(rows, ignore_index=True)
DATA.mkdir(exist_ok=True); D.to_csv(DATA / "results.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("results", D)
q = "\n".join(l for l in (SQL / "02_achieve_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
r = D.actual * 100.0 / D.target
rnd = lambda x, d: np.floor(x * 10 ** d + .5) / 10 ** d
D["exact"] = D.actual >= D.target; D["r0"] = rnd(r, 0) >= 100; D["r1"] = rnd(r, 1) >= 100; D["rate"] = r
P = D.groupby("month")[["exact", "r0", "r1"]].sum().reset_index()
assert (P.exact.to_numpy() == Q.achieved_exact.to_numpy()).all() and (P.r0.to_numpy() == Q.achieved_round0.to_numpy()).all() and (P.r1.to_numpy() == Q.achieved_round1.to_numpy()).all()
P.to_csv(RES / "by_month.csv", index=False)
extra0 = P.r0 - P.exact; extra1 = P.r1 - P.exact
border = D[(D.rate >= 99.5) & (D.rate < 100)]
out = {"stores": S, "months": M, "store_months": len(D),
       "exact_mean": float(P.exact.mean()), "r0_mean": float(P.r0.mean()), "r1_mean": float(P.r1.mean()),
       "extra_r0_mean": float(extra0.mean()), "extra_r0_min": int(extra0.min()), "extra_r0_max": int(extra0.max()),
       "extra_r1_mean": float(extra1.mean()), "extra_r1_max": int(extra1.max()),
       "extra_r0_total": int(extra0.sum()), "extra_r1_total": int(extra1.sum()),
       "exact_rate_share": float(D.exact.mean()), "r0_rate_share": float(D.r0.mean()),
       "border_count": len(border), "border_min_rate": float(border.rate.min()),
       "border_shortfall_max_yen": int((border.target - border.actual).max()),
       "border_shortfall_mean_yen": float((border.target - border.actual).mean()),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a774_main.json", "w"), ensure_ascii=False, indent=1)

lab = [m[5:] + "月" for m in P.month]; x = np.arange(M)
# 図1：月ごとの達成店の数
fig, ax = plt.subplots(figsize=(10, 4.6)); w = .27
ax.bar(x - w, P.exact, w, color=BLUE, label="実績≧目標（丸める前）")
ax.bar(x, P.r1, w, color=GREEN, label="小数1桁に丸めてから")
ax.bar(x + w, P.r0, w, color=ORANGE, label="整数の%に丸めてから")
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("達成店の数（200店のうち）"); ax.set_ylim(0, 140)
ax.legend(frameon=False, ncol=3, loc="upper left"); ax.set_title(f"整数の%に丸めると、毎月平均{extra0.mean():.1f}店が「達成」に増える")
save(fig, "a774_by_month.png", SRC)
# 図2：境目の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
z = D[(D.rate >= 97) & (D.rate < 103)]
bins = np.arange(97, 103.01, .25)
ax.hist(z.rate, bins=bins, color=GRAY)
ax.axvspan(99.5, 100, color=ORANGE, alpha=.3, label="99.5%以上100%未満：丸めると「100%」")
ax.axvline(100, color="black", lw=1)
ax.set_xlabel("達成率（%、丸める前）"); ax.set_ylabel("店×月の数"); ax.legend(frameon=False, loc="upper left")
ax.set_title(f"12か月で{len(border)}件が、目標に届かないのに「100%」と表示される")
save(fig, "a774_border.png", SRC)
# 図3：足りなかった金額
fig, ax = plt.subplots(figsize=(9, 4.6))
sh = (border.target - border.actual) / 1e4
ax.hist(sh, bins=20, color=ORANGE)
ax.set_xlabel("目標に足りなかった金額（万円）"); ax.set_ylabel("店×月の数")
ax.set_title(f"「100%」と表示された{len(border)}件は、平均{out['border_shortfall_mean_yen'] / 1e4:.1f}万円、最大{out['border_shortfall_max_yen'] / 1e4:.1f}万円届いていない")
save(fig, "a774_shortfall.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
