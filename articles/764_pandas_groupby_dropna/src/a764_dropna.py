"""764 pandas の groupby が欠けたキーの行を黙って落とすと、合計はどれだけ減るのか

架空の売上明細（2024-01〜2025-12、50店）。店コードは基本1%の行で欠けていて、システムを入れ替えた2025-04 だけ
20%の行で欠けている。カテゴリも2%の行で欠けている。pandas で
  A groupby の既定（dropna=True）、B groupby(dropna=False)、C 先に「未設定」で埋める
で店別・店×カテゴリ別・月×店別の合計を出し、全体の合計と比べる。value_counts と pivot_table も同じように数える。
SQL（DuckDB、1スレッド）の GROUP BY は欠けたキーを1つのまとまりとして残すことも確かめる。seed 764。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の売上明細（作成者が乱数で作成、seed 764）"
rng = np.random.default_rng(764)
months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
stores = [f"S{i:03d}" for i in range(1, 51)]
cats = ["食品", "飲料", "日用品", "衣料", "雑貨"]
rows = []
for m in months:
    n = 2500
    st = rng.choice(stores, n); ct = rng.choice(cats, n, p=[0.35, 0.2, 0.2, 0.15, 0.1])
    amt = (rng.lognormal(8.5, 0.8, n) // 10 * 10).astype(int)
    p_miss = 0.20 if m == pd.Timestamp("2025-04-01") else 0.01
    st = np.where(rng.random(n) < p_miss, None, st)
    ct = np.where(rng.random(n) < 0.02, None, ct)
    rows.append(pd.DataFrame({"ym": m.strftime("%Y-%m"), "store": st, "category": ct, "amount": amt}))
D = pd.concat(rows, ignore_index=True)
D.to_csv(DATA / "sales_lines.csv", index=False)
D = pd.read_csv(DATA / "sales_lines.csv")   # CSV から読むと空欄は NaN になる
total = int(D.amount.sum())
A1 = D.groupby("store").amount.sum(); B1 = D.groupby("store", dropna=False).amount.sum()
C1 = D.assign(store=D.store.fillna("未設定")).groupby("store").amount.sum()
A2 = D.groupby(["store", "category"]).amount.sum(); B2 = D.groupby(["store", "category"], dropna=False).amount.sum()
A3 = D.groupby(["ym", "store"]).amount.sum().groupby("ym").sum()
PV = D.pivot_table(index="store", columns="category", values="amount", aggfunc="sum")
VC = D.store.value_counts()
assert int(B1.sum()) == total and int(C1.sum()) == total and int(B2.sum()) == total
con = duckdb.connect(); con.execute("SET threads=1"); con.register("lines", D)
q = [x for x in (SQL / "02_groupby_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
dS = con.execute(q[0]).df(); dN = con.execute(q[1]).df()
assert int(dS.amount.sum()) == total and int(dN.n_null_store.iloc[0]) == int(D.store.isna().sum())
lost = lambda s: round((1 - s.sum() / total) * 100, 2)
mon_true = D.groupby("ym").amount.sum()
mon_lost_pct = (1 - A3 / mon_true) * 100
out = {"rows": len(D), "months": len(months), "stores": len(stores), "total_oku": round(total / 1e8, 2),
       "store_missing_rows": int(D.store.isna().sum()), "store_missing_pct": round(D.store.isna().mean() * 100, 2),
       "category_missing_rows": int(D.category.isna().sum()),
       "either_missing_rows": int((D.store.isna() | D.category.isna()).sum()),
       "lost_pct_groupby_store": lost(A1), "lost_pct_groupby_store_category": lost(A2),
       "lost_pct_pivot_table": round((1 - PV.sum().sum() / total) * 100, 2),
       "lost_rows_value_counts": int(len(D) - VC.sum()),
       "lost_pct_dropna_false": lost(B1), "lost_pct_fillna": lost(C1),
       "month_2025_04_lost_pct": round(float(mon_lost_pct["2025-04"]), 1),
       "other_months_lost_pct_median": round(float(mon_lost_pct.drop("2025-04").median()), 1),
       "yoy_2025_04_true_pct": round((mon_true["2025-04"] / mon_true["2024-04"] - 1) * 100, 1),
       "yoy_2025_04_groupby_pct": round((A3["2025-04"] / A3["2024-04"] - 1) * 100, 1),
       "duckdb_keeps_null_group": True, "pandas_version": pd.__version__}
json.dump(out, open(RES / "a764_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"ym": mon_true.index, "true": mon_true.values, "groupby_month_store": A3.reindex(mon_true.index).values,
              "lost_pct": mon_lost_pct.reindex(mon_true.index).round(2).values}).to_csv(RES / "monthly.csv", index=False)

# 図1：月ごとに消えた割合（月×店で集計してから足した場合）
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(pd.to_datetime(mon_true.index), mon_lost_pct.reindex(mon_true.index), width=20, color=[ORANGE if m == "2025-04" else LIGHT for m in mon_true.index])
ax.set_ylabel("groupby で消えた売上（%）")
ax.set_title(f"システムを入れ替えた月だけ、店別に集計すると{out['month_2025_04_lost_pct']}%が消える")
save(fig, "a764_monthly.png", SRC)
# 図2：集計のしかたごとの消えた割合
fig, ax = plt.subplots(figsize=(8, 3.8))
labs = ["groupby(店)", "groupby(店, カテゴリ)", "pivot_table", "groupby(店,\ndropna=False)", "「未設定」で\n埋めてから"]
vals = [out["lost_pct_groupby_store"], out["lost_pct_groupby_store_category"], out["lost_pct_pivot_table"], out["lost_pct_dropna_false"], out["lost_pct_fillna"]]
ax.bar(labs, vals, color=[ORANGE, ORANGE, ORANGE, GREEN, GREEN])
for i, v in enumerate(vals):
    ax.text(i, v + 0.05, f"{v:.2f}%", ha="center", fontsize=10)
ax.set_ylabel("2年分の売上のうち消えた割合（%）"); ax.tick_params(axis="x", labelsize=9)
ax.set_title("キーが2つになると、どちらかが欠けた行も消える")
save(fig, "a764_methods.png", SRC)
# 図3：前年同月比
fig, ax = plt.subplots(figsize=(7, 3.6))
v = [out["yoy_2025_04_true_pct"], out["yoy_2025_04_groupby_pct"]]
ax.bar(["本当の合計", "店別に集計してから足した合計"], v, color=[BLUE, ORANGE])
for i, val in enumerate(v):
    ax.text(i, val + (0.5 if val >= 0 else -1.5), f"{val:+.1f}%", ha="center", fontsize=11)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_ylabel("2025年4月の前年同月比（%）")
ax.set_title("欠けたキーの行が消えると、前年比も下がって見える")
save(fig, "a764_yoy.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
