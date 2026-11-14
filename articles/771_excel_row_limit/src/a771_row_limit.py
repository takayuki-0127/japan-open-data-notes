"""771 104万行を超える CSV を Excel で開くと、どれだけの行と売上が消えるのか

架空の売上明細120万行（2025年1〜12月、月ごとに件数が増える）。Excel のシートは1,048,576行までで、
見出しに1行使うので、明細は1,048,575行までしか入らない（この切り方を Python で再現。Excel では未検証）。
日付順に並んだファイルと、ばらばらの順のファイルの2通りで、消える行・売上を月ごとに数える。
SQL（DuckDB、1スレッド）で全件を集計した結果と、pandas の結果の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の売上明細（作成者が乱数で作成、seed 771）"
rng = np.random.default_rng(771)
N, LIMIT = 1_200_000, 1_048_576 - 1          # 見出しに1行使う
w = np.linspace(1, 1.6, 12); w /= w.sum()        # 後の月ほど件数が多い
month = np.sort(rng.choice(12, N, p=w)) + 1
day = rng.integers(1, 29, N)
dates = pd.to_datetime({"year": 2025, "month": month, "day": day})
amount = np.round(rng.lognormal(7.6, .8, N)).astype(int)
D = pd.DataFrame({"sale_date": dates, "amount": amount}).sort_values("sale_date", kind="stable").reset_index(drop=True)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("details", D)
q = "\n".join(l for l in (SQL / "02_monthly_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
full = D.groupby(D.sale_date.dt.strftime("%Y-%m")).amount.agg(["size", "sum"])
assert (Q.n_rows.to_numpy() == full["size"].to_numpy()).all() and (Q.amount.to_numpy() == full["sum"].to_numpy()).all()

def kept(df): return df.iloc[:LIMIT]
sorted_k = kept(D)
shuf = D.sample(frac=1, random_state=771).reset_index(drop=True); shuf_k = kept(shuf)
M = pd.DataFrame({"month": full.index, "rows_full": full["size"].values, "amount_full": full["sum"].values})
for name, k in [("sorted", sorted_k), ("shuffled", shuf_k)]:
    g = k.groupby(k.sale_date.dt.strftime("%Y-%m")).amount.agg(["size", "sum"]).reindex(M.month, fill_value=0)
    M[f"rows_{name}"] = g["size"].values; M[f"amount_{name}"] = g["sum"].values
M.to_csv(RES / "by_month.csv", index=False)
lost_rows = N - LIMIT
out = {"rows": N, "excel_data_rows": LIMIT, "lost_rows": lost_rows, "lost_share": lost_rows / N,
       "amount_total": int(D.amount.sum()),
       "lost_amount_sorted": int(D.amount.sum() - sorted_k.amount.sum()), "lost_amount_shuffled": int(D.amount.sum() - shuf_k.amount.sum()),
       "lost_amount_share_sorted": float(1 - sorted_k.amount.sum() / D.amount.sum()),
       "lost_amount_share_shuffled": float(1 - shuf_k.amount.sum() / D.amount.sum()),
       "dec_rows_full": int(M.rows_full.iloc[-1]), "dec_rows_sorted": int(M.rows_sorted.iloc[-1]),
       "nov_rows_full": int(M.rows_full.iloc[-2]), "nov_rows_sorted": int(M.rows_sorted.iloc[-2]),
       "dec_kept_share_sorted": float(M.rows_sorted.iloc[-1] / M.rows_full.iloc[-1]),
       "nov_kept_share_sorted": float(M.rows_sorted.iloc[-2] / M.rows_full.iloc[-2]),
       "shuffled_kept_share_min": float((M.rows_shuffled / M.rows_full).min()), "shuffled_kept_share_max": float((M.rows_shuffled / M.rows_full).max()),
       "last_date_kept_sorted": str(sorted_k.sale_date.iloc[-1].date()),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a771_main.json", "w"), ensure_ascii=False, indent=1)

lab = [m[5:] + "月" for m in M.month]; x = np.arange(12)
# 図1：日付順のファイル
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(x, M.amount_full / 1e6, color=GRAY, label="全120万行")
ax.bar(x, M.amount_sorted / 1e6, color=BLUE, label="Excel に入る1,048,575行")
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("売上（百万円）"); ax.legend(frameon=False, loc="upper left")
ax.set_title(f"日付順のファイルでは、{out['last_date_kept_sorted'][5:7]}月の途中から後ろがまるごと消える")
save(fig, "a771_sorted.png", SRC)
# 図2：ばらばらの順
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(x, M.rows_sorted / M.rows_full * 100, "o-", color=BLUE, label="日付順に並んだファイル")
ax.plot(x, M.rows_shuffled / M.rows_full * 100, "s-", color=ORANGE, label="ばらばらの順のファイル")
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("Excel に残った行の割合（%）"); ax.set_ylim(0, 105)
ax.legend(frameon=False, loc="lower left"); ax.set_title("ばらばらの順だと、どの月も同じように約13%ずつ消える")
save(fig, "a771_order.png", SRC)
# 図3：消えた合計
fig, ax = plt.subplots(figsize=(9, 4.6))
vals = [lost_rows / N * 100, out["lost_amount_share_sorted"] * 100, out["lost_amount_share_shuffled"] * 100]
b = ax.bar(["消えた行", "消えた売上\n（日付順）", "消えた売上\n（ばらばら）"], vals, color=[GRAY, BLUE, ORANGE])
for bb, v in zip(b, vals): ax.text(bb.get_x() + bb.get_width() / 2, v + .3, f"{v:.1f}%", ha="center")
ax.set_ylabel("全体に対する割合（%）"); ax.set_title(f"{lost_rows:,}行（{lost_rows / N:.1%}）が Excel に入らない")
save(fig, "a771_lost.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
