"""765 「NA」という区分名を pandas で読むと、何行が欠けた値になってしまうのか

架空の海外向けの受注明細（2025年、1年分）。地域コードは NA（北米）・EU（欧州）・AS（アジア）・OC（オセアニア）・
SA（南米）・AF（アフリカ）。本当に地域が分からない行は空欄にしてある。ほかに、
担当者が自由に書く「メモ」の列に「N/A」「null」「None」などの文字が入っている。
  A pandas.read_csv の既定、B dtype=str を指定、C keep_default_na=False と na_values=[""]
で読み、欠けた値になった行と地域別の合計・構成比のずれを数える。DuckDB（1スレッド）の read_csv とも比べる。seed 765。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の海外向けの受注明細（作成者が乱数で作成、seed 765）"
rng = np.random.default_rng(765)
REG = ["NA", "EU", "AS", "OC", "SA", "AF"]
LAB = {"NA": "北米", "EU": "欧州", "AS": "アジア", "OC": "オセアニア", "SA": "南米", "AF": "アフリカ"}
n = 12000
reg = rng.choice(REG, n, p=[0.32, 0.27, 0.28, 0.06, 0.04, 0.03])
reg = np.where(rng.random(n) < 0.01, "", reg)          # 本当に分からない行は空欄
memo_choices = ["", "", "", "", "N/A", "null", "None", "急ぎ", "再送", "NA"]
memo = rng.choice(memo_choices, n)
amt = (rng.lognormal(11, 0.9, n) // 100 * 100).astype(int)
dates = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
O = pd.DataFrame({"order_id": [f"O{i:06d}" for i in range(1, n + 1)], "order_date": dates.strftime("%Y-%m-%d"), "region": reg, "memo": memo, "amount": amt})
O = O.sort_values(["order_date", "order_id"]).reset_index(drop=True)
O.to_csv(DATA / "orders.csv", index=False)
path = DATA / "orders.csv"
A = pd.read_csv(path)
B = pd.read_csv(path, dtype=str)
C = pd.read_csv(path, keep_default_na=False, na_values=[""])
con = duckdb.connect(); con.execute("SET threads=1")
q = [x for x in (SQL / "02_na_duckdb.sql").read_text(encoding="utf-8").replace("{CSV}", str(path)).split(";") if "SELECT" in x]
Dk = con.execute(q[0]).df(); Dn = con.execute(q[1]).df()
true_reg = O.region.replace("", np.nan)
assert int(C.region.isna().sum()) == int((O.region == "").sum())
assert int(Dn.n_null_region.iloc[0]) == int((O.region == "").sum())
truth = O[O.region != ""].groupby("region").amount.sum()
gA = A.groupby("region").amount.sum(); gC = C.groupby("region").amount.sum()
shareT = truth / truth.sum() * 100; shareA = gA / gA.sum() * 100
memo_na_true = int((O.memo == "").sum())
out = {"rows": n, "region_blank_rows": int((O.region == "").sum()),
       "A_region_nan_rows": int(A.region.isna().sum()), "A_region_nan_pct": round(A.region.isna().mean() * 100, 1),
       "B_region_nan_rows": int(B.region.isna().sum()), "C_region_nan_rows": int(C.region.isna().sum()),
       "A_memo_nan_rows": int(A.memo.isna().sum()), "C_memo_nan_rows": int(C.memo.isna().sum()), "memo_blank_rows_true": memo_na_true,
       "memo_words_turned_nan_A": sorted(set(O.memo[A.memo.isna() & (O.memo != "")])),
       "NA_sales_pct_true": round(float(shareT["NA"]), 1),
       "A_NA_in_groupby": "NA" in gA.index,
       "A_total_vs_true_pct": round((gA.sum() / truth.sum() - 1) * 100, 1),
       "share_true": {LAB[k]: round(float(v), 1) for k, v in shareT.items()},
       "share_A": {LAB[k]: round(float(v), 1) for k, v in shareA.items()},
       "duckdb_region_null_rows": int(Dn.n_null_region.iloc[0]), "duckdb_NA_rows": int(Dk[Dk.region == "NA"].n.iloc[0]),
       "pandas_version": pd.__version__}
assert int(B.region.isna().sum()) == out["A_region_nan_rows"]
json.dump(out, open(RES / "a765_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"region": [LAB[k] for k in shareT.index], "sales_true": truth.values,
              "sales_A": gA.reindex(truth.index).fillna(0).astype(int).values,
              "share_true_pct": shareT.round(2).values, "share_A_pct": shareA.reindex(truth.index).round(2).values}).to_csv(RES / "by_region.csv", index=False)

# 図1：読み方ごとに欠けた値になった行
fig, ax = plt.subplots(figsize=(8, 3.8))
labs = ["A 既定", "B dtype=str", "C keep_default_na=False\n＋ na_values=[\"\"]", "DuckDB\nread_csv"]
v = [out["A_region_nan_rows"], out["B_region_nan_rows"], out["C_region_nan_rows"], out["duckdb_region_null_rows"]]
ax.bar(labs, v, color=[ORANGE, ORANGE, GREEN, GREEN])
for i, val in enumerate(v):
    ax.text(i, val + 60, f"{val:,}行", ha="center")
ax.axhline(out["region_blank_rows"], color=GRAY, ls="--", lw=1); ax.text(2.5, 900, f"本当に空欄の行は{out['region_blank_rows']}行（点線）", color=GRAY, fontsize=9, ha="center")
ax.set_ylim(0, max(v) * 1.12)
ax.set_ylabel("地域が欠けた値になった行"); ax.tick_params(axis="x", labelsize=9)
ax.set_title("既定の読み方では、北米（NA）の行がまるごと欠けた値になる")
save(fig, "a765_nan_rows.png", SRC)
# 図2：地域の構成比
fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(len(truth)); k = list(truth.index)
ax.bar(x - 0.18, shareT.values, 0.36, color=BLUE, label="本当の構成比")
ax.bar(x + 0.18, shareA.reindex(k).fillna(0).values, 0.36, color=ORANGE, label="既定で読んで groupby した構成比")
for i, kk in enumerate(k):
    ax.text(i - 0.18, shareT[kk] + 0.5, f"{shareT[kk]:.1f}", ha="center", fontsize=8.5)
    a = shareA.get(kk, 0.0); ax.text(i + 0.18, a + 0.5, f"{a:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([LAB[kk] for kk in k]); ax.set_ylabel("売上の構成比（%）"); ax.legend(frameon=False)
ax.set_title("北米が消え、ほかの地域の構成比が大きく見える")
save(fig, "a765_share.png", SRC)
# 図3：メモの列
fig, ax = plt.subplots(figsize=(8, 3.4))
words = ["NA", "N/A", "null", "None", "急ぎ", "再送"]
cnt = [int((O.memo == w).sum()) for w in words]; nanA = [int((A.memo.isna() & (O.memo == w)).sum()) for w in words]
ax.bar(words, cnt, color=LIGHT, label="書かれていた行")
ax.bar(words, nanA, color=ORANGE, label="既定で読むと欠けた値になった行")
ax.set_ylabel("行数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("自由に書くメモでも、「N/A」「null」「None」「NA」は欠けた値に変わる")
save(fig, "a765_memo.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
