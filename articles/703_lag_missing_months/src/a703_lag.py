"""703 売上のない月が行ごと抜けた表で LAG を使って前月比を出すと、何行が2か月前と比べてしまうのか

架空の60店×24か月（2024-01〜2025-12）。小さい店ほど売上0の月があり、その月は行がない。
  A そのまま LAG：前の「行」と比べる
  B 店×月のカレンダーと結合し、抜けた月を0で埋めてから LAG
前の行が前月でない行の数と、前月比のずれを数える。DuckDB（1スレッド）と pandas で一致を確かめる。seed 703。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店別・月別の売上（作成者が乱数で作成、seed 703）"
rng = np.random.default_rng(703)
NS = 60
months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
size = np.exp(rng.normal(0, 1.0, NS))
p0 = np.clip(0.35 / (1 + size * 1.5), 0.0, 0.4)  # 小さい店ほど売上0の月が多い
rows = []
for s in range(NS):
    lvl = 300 * size[s]; trend = rng.normal(0.01, 0.01)
    for t, m in enumerate(months):
        if rng.random() < p0[s]:
            continue  # 売上0の月は行がない
        season = 1 + 0.15 * np.sin(2 * np.pi * (m.month - 3) / 12)
        v = lvl * (1 + trend) ** t * season * rng.lognormal(0, 0.12)
        rows.append((s + 1, m, int(round(v * 1000))))
M = pd.DataFrame(rows, columns=["store_id", "ym", "sales"])
M.assign(ym=M.ym.dt.strftime("%Y-%m-%d")).to_csv(DATA / "monthly.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("monthly", M)
q = [x for x in (SQL / "02_lag_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
A = con.execute(q[0]).df(); B = con.execute(q[1]).df(); C = int(con.execute(q[2]).fetchone()[0])
# pandas
P = M.sort_values(["store_id", "ym"]).reset_index(drop=True)
P["prev_ym"] = P.groupby("store_id").ym.shift(); P["prev_sales"] = P.groupby("store_id").sales.shift()
assert np.allclose(P.prev_sales.fillna(-1), A.prev_sales.fillna(-1))
P["gap"] = (P.ym.dt.year - P.prev_ym.dt.year) * 12 + (P.ym.dt.month - P.prev_ym.dt.month)
wrong = P[P.gap > 1]
assert len(wrong) == C
full = pd.MultiIndex.from_product([sorted(M.store_id.unique()), months], names=["store_id", "ym"])
F = M.set_index(["store_id", "ym"]).reindex(full, fill_value=0).reset_index()
F["prev_sales"] = F.groupby("store_id").sales.shift()
assert np.allclose(F.prev_sales.fillna(-1), B.prev_sales.fillna(-1)) and len(F) == len(B)
# 前月比（%）。A は前の行と、B は本当の前月（0なら計算できない）
P["mom_A"] = (P.sales / P.prev_sales - 1) * 100
F["mom_B"] = np.where(F.prev_sales > 0, (F.sales / F.prev_sales - 1) * 100, np.nan)
cmp = P.merge(F[["store_id", "ym", "mom_B", "prev_sales"]].rename(columns={"prev_sales": "true_prev"}), on=["store_id", "ym"])
w = cmp[cmp.gap > 1]
stores_affected = int(w.store_id.nunique())
rows_with_prev = int(P.prev_sales.notna().sum())
# 2か月前と比べた前月比の値（本当は前月が0で計算できない行）
out = {"stores": NS, "months": len(months), "rows": len(M), "missing_month_rows": NS * len(months) - len(M),
       "missing_pct": round((1 - len(M) / (NS * len(months))) * 100, 1),
       "rows_with_lag": rows_with_prev, "rows_not_prev_month": C, "rows_not_prev_month_pct": round(C / rows_with_prev * 100, 1),
       "gap_counts": {str(int(k)): int(v) for k, v in wrong.gap.value_counts().sort_index().items()},
       "stores_affected": stores_affected,
       "mom_A_on_wrong_rows_median_abs": round(float(w.mom_A.abs().median()), 1),
       "mom_A_on_wrong_rows_share_within_10pct": round(float((w.mom_A.abs() <= 10).mean() * 100), 1),
       "true_mom_on_wrong_rows": "前月が0のため計算できない（行がなかった月の翌月）",
       "rows_after_zero_month_in_B": int((F.prev_sales == 0).sum()),
       "after_zero_month_rows_in_A_by_gap": None}
# 店の大きさ（四分位）ごとの割合
P["size_q"] = pd.qcut(P.store_id.map(dict(zip(range(1, NS + 1), size))), 4, labels=["小", "中小", "中大", "大"])
byq = P[P.prev_sales.notna()].groupby("size_q", observed=True).gap.apply(lambda g: (g > 1).mean() * 100).round(1)
out["wrong_pct_by_store_size"] = byq.to_dict()
out.pop("after_zero_month_rows_in_A_by_gap")
json.dump(out, open(RES / "a703_main.json", "w"), ensure_ascii=False, indent=1)
w[["store_id", "ym", "prev_ym", "gap", "sales", "prev_sales", "mom_A"]].assign(ym=w.ym.dt.strftime("%Y-%m"), prev_ym=w.prev_ym.dt.strftime("%Y-%m")).round(1).to_csv(RES / "wrong_rows.csv", index=False)

# 図1：例の店
ex = int(w.store_id.value_counts().index[0])
e = F[F.store_id == ex]
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.bar(e.ym, e.sales / 1000, width=20, color=[LIGHT if v > 0 else "white" for v in e.sales], edgecolor=[BLUE if v > 0 else ORANGE for v in e.sales])
for _, r in w[w.store_id == ex].iterrows():
    ax.annotate("", xy=(r.ym, r.sales / 1000), xytext=(r.prev_ym, r.prev_sales / 1000), arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.4))
ax.set_ylabel("売上（千円）"); ax.set_title(f"店{ex}：売上0の月（行がない）をとばして、LAG は2か月以上前と比べる（オレンジの矢印）")
save(fig, "a703_example.png", SRC)
# 図2：店の大きさごとの割合
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.bar(byq.index.astype(str), byq.values, color=ORANGE)
for i, v in enumerate(byq.values):
    ax.text(i, v + 0.3, f"{v:.1f}%", ha="center", fontsize=10)
ax.set_xlabel("店の大きさ（4つに等分）"); ax.set_ylabel("前の行が前月でない割合（%）")
ax.set_title("小さい店ほど、LAG の前月比が前月と比べていない")
save(fig, "a703_by_size.png", SRC)
# 図3：前月でない行の前月比の分布
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.hist(w.mom_A.clip(-60, 60), bins=np.arange(-60, 62, 4), color=ORANGE)
ax.set_xlabel("LAG で出した「前月比」（%、±60%でまとめた）"); ax.set_ylabel("行数")
ax.set_title(f"本当は前月が0で計算できない{C}行が、ふつうの前月比に見える")
save(fig, "a703_wrong_mom.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
