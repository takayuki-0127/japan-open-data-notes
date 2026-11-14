"""751 PIVOT の列を固定で書いておくと、あとから増えた区分の売上は何%消えるのか

架空の区分別の月次売上（2024-01〜2025-12）。表を作った時点の6区分で PIVOT の列を固定したあと、
2024-07 に「定期便」、2025-04 に「ギフト」、2025-10 に「まとめ買い」が増える。
  A 列を固定した PIVOT、B CASE WHEN で「その他」「合計」も出す、C 縦持ちのまま合計
固定の列だけを足した合計が、本当の合計からどれだけ欠けるかを数える。DuckDB（1スレッド）と pandas で一致を確かめる。seed 751。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の区分別の月次売上（作成者が乱数で作成、seed 751）"
rng = np.random.default_rng(751)
months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
FIXED = ["食品", "飲料", "日用品", "衣料", "家電", "雑貨"]
base = dict(zip(FIXED, [420, 260, 180, 150, 120, 90]))  # 万円
NEW = {"定期便": ("2024-07-01", 25, 0.09), "ギフト": ("2025-04-01", 40, 0.05), "まとめ買い": ("2025-10-01", 60, 0.04)}
rows = []
for t, m in enumerate(months):
    season = 1 + 0.12 * np.sin(2 * np.pi * (m.month - 4) / 12) + (0.25 if m.month == 12 else 0)
    for c in FIXED:
        v = base[c] * (1 + 0.004) ** t * season * rng.lognormal(0, 0.05)
        rows.append((m, c, int(round(v * 10000))))
    for c, (start, lvl, g) in NEW.items():
        s = pd.Timestamp(start)
        if m >= s:
            k = (m.year - s.year) * 12 + (m.month - s.month)
            v = lvl * (1 + g) ** k * season * rng.lognormal(0, 0.06)
            rows.append((m, c, int(round(v * 10000))))
S = pd.DataFrame(rows, columns=["ym", "category", "amount"])
S.assign(ym=S.ym.dt.strftime("%Y-%m-%d")).to_csv(DATA / "sales.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", S)
q = [x for x in (SQL / "02_pivot_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
A = con.execute(q[0]).df(); B = con.execute(q[1]).df(); C = con.execute(q[2]).df(); D = con.execute(q[3]).df()
# pandas で同じものを作る
P = S.pivot_table(index="ym", columns="category", values="amount", aggfunc="sum").reset_index()
assert np.allclose(A[FIXED].fillna(0).values, P[FIXED].fillna(0).values)
tot = S.groupby("ym").amount.sum().values
assert np.allclose(C.total.values, tot) and np.allclose(B["合計"].values, tot)
fixed_sum = A[FIXED].sum(axis=1).values
assert np.allclose(B[FIXED].sum(axis=1).values + B["その他"].values, tot)
lost = tot - fixed_sum
lost_pct = lost / tot * 100
y24 = months.year == 2024; y25 = months.year == 2025
out = {"months": len(months), "fixed_categories": FIXED, "new_categories": {k: v[0][:7] for k, v in NEW.items()},
       "total_2y_oku": round(tot.sum() / 1e8, 2),
       "lost_2y_pct": round(lost.sum() / tot.sum() * 100, 1),
       "lost_2024_pct": round(lost[y24].sum() / tot[y24].sum() * 100, 1),
       "lost_2025_pct": round(lost[y25].sum() / tot[y25].sum() * 100, 1),
       "lost_last_month_pct": round(float(lost_pct[-1]), 1),
       "lost_first_new_month_pct": round(float(lost_pct[6]), 1),
       "yoy_2025_true_pct": round((tot[y25].sum() / tot[y24].sum() - 1) * 100, 1),
       "yoy_2025_fixed_pct": round((fixed_sum[y25].sum() / fixed_sum[y24].sum() - 1) * 100, 1),
       "dec_yoy_true_pct": round((tot[-1] / tot[11] - 1) * 100, 1),
       "dec_yoy_fixed_pct": round((fixed_sum[-1] / fixed_sum[11] - 1) * 100, 1),
       "missing_categories_found": D.category.tolist()}
json.dump(out, open(RES / "a751_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"ym": months.strftime("%Y-%m"), "total": tot, "fixed_cols_sum": fixed_sum, "lost": lost,
              "lost_pct": lost_pct.round(2)}).to_csv(RES / "monthly_lost.csv", index=False)

# 図1：月ごとの合計と固定列の合計
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(months, tot / 1e6, color=BLUE, lw=2, label="本当の合計（縦持ちで合計）")
ax.plot(months, fixed_sum / 1e6, color=ORANGE, lw=2, ls="--", label="固定した6列の合計")
ax.fill_between(months, fixed_sum / 1e6, tot / 1e6, color=ORANGE, alpha=0.15)
for c, (st, _, _) in NEW.items():
    ax.axvline(pd.Timestamp(st), color=GRAY, lw=0.8, ls=":"); ax.text(pd.Timestamp(st) + pd.Timedelta(days=6), (tot / 1e6).min(), c + "が増える", fontsize=8.5, color=GRAY, ha="left", va="bottom")
ax.set_ylabel("月の売上（百万円）"); ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.set_title("固定した PIVOT の列を足しても、新しい区分のぶんだけ合計に届かない")
save(fig, "a751_totals.png", SRC)
# 図2：消えた割合
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(months, lost_pct, width=20, color=ORANGE)
ax.set_ylabel("表から消えた売上（%）")
ax.set_title(f"消えた割合は月を追って増え、2025年12月には{lost_pct[-1]:.1f}%")
save(fig, "a751_lost_pct.png", SRC)
# 図3：前年比のずれ
fig, ax = plt.subplots(figsize=(7.5, 3.6))
lab = ["2025年の前年比", "12月の前年同月比"]
tv = [out["yoy_2025_true_pct"], out["dec_yoy_true_pct"]]; fv = [out["yoy_2025_fixed_pct"], out["dec_yoy_fixed_pct"]]
x = np.arange(2)
ax.bar(x - 0.18, tv, 0.36, color=BLUE, label="本当の合計")
ax.bar(x + 0.18, fv, 0.36, color=ORANGE, label="固定した6列の合計")
for i in range(2):
    ax.text(i - 0.18, tv[i] + 0.3, f"{tv[i]:+.1f}%", ha="center", fontsize=10)
    ax.text(i + 0.18, fv[i] + 0.3, f"{fv[i]:+.1f}%", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("伸び（%）"); ax.legend(frameon=False)
ax.set_title("伸びも、新しい区分のぶんだけ小さく見える")
save(fig, "a751_yoy.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
