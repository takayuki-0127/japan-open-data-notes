"""733 見出し行つきの CSV を何本も縦につなぐと、見出し行が何行まざり、数の列はどうなるのか

架空の店の月別の売上 CSV 12本（2025年1〜12月、1本 約500行、見出し行つき）。
7月のファイルだけ、列の順が「sales_date,amount,store_id」になっている（他は sales_date,store_id,amount）。
読み方を3通りで比べる：
  そのままつなぐ：12本をテキストのまま縦につなぎ、先頭の見出しだけで読む（cat でつないだのと同じ）
  見出しを飛ばす：2本目以降の1行目を捨ててつなぐ（列の順は見ない）
  1本ずつ読む：見出しを読んで列の名前でそろえる（DuckDB の read_csv(union_by_name) と pandas）
まざった見出し行の数、数の列の型、月ごとの件数・合計のずれを数える。
"""
import io
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, DATA, SQL, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の店の月別の売上 CSV（作成者が乱数で作成、seed 733）"
rng = np.random.default_rng(733)
DATA.mkdir(exist_ok=True)
files, truth = [], []
for m in range(1, 13):
    n = int(rng.integers(450, 551))
    d = pd.to_datetime(f"2025-{m:02d}-01") + pd.to_timedelta(rng.integers(0, pd.Period(f"2025-{m:02d}").days_in_month, n), unit="D")
    df = pd.DataFrame({"sales_date": d.strftime("%Y-%m-%d"), "store_id": [f"S{int(s):02d}" for s in rng.integers(1, 21, n)],
                       "amount": (rng.lognormal(np.log(4000), 0.6, n) // 10 * 10).astype(int)}).sort_values(["sales_date", "store_id"])
    cols = ["sales_date", "amount", "store_id"] if m == 7 else ["sales_date", "store_id", "amount"]
    p = DATA / f"monthly_{m:02d}.csv"; df[cols].to_csv(p, index=False); files.append(p)
    truth.append({"ym": f"2025-{m:02d}", "rows": n, "amount": int(df.amount.sum())})
T = pd.DataFrame(truth).set_index("ym")

texts = [p.read_text(encoding="utf-8") for p in files]
# 1) そのままつなぐ
naive = pd.read_csv(io.StringIO("".join(texts)), dtype=str)
hdr = naive[naive.sales_date == "sales_date"]
num = pd.to_numeric(naive.amount, errors="coerce")
naive_ym = naive.sales_date.str[:7]
N1 = pd.DataFrame({"rows": naive.groupby(naive_ym).size(), "amount": num.groupby(naive_ym).sum()})
# 2) 見出しを飛ばす（列の順は見ない）
skip = pd.read_csv(io.StringIO(texts[0] + "".join(t.split("\n", 1)[1] for t in texts[1:])), dtype=str)
num2 = pd.to_numeric(skip.amount, errors="coerce")
N2 = pd.DataFrame({"rows": skip.groupby(skip.sales_date.str[:7]).size(), "amount": num2.groupby(skip.sales_date.str[:7]).sum()})
# 3) 1本ずつ読む
each = pd.concat([pd.read_csv(p, dtype={"amount": int, "store_id": str, "sales_date": str}) for p in files], ignore_index=True)
N3 = pd.DataFrame({"rows": each.groupby(each.sales_date.str[:7]).size(), "amount": each.groupby(each.sales_date.str[:7]).amount.sum()})
assert (N3.rows == T.rows).all() and (N3.amount == T.amount).all()

con = duckdb.connect(); con.execute("SET threads=1")
flist = "[" + ", ".join(f"'{p.as_posix()}'" for p in files) + "]"
dq = con.execute((SQL / "02_read_duckdb.sql").read_text(encoding="utf-8").replace(":files", flist)).df().set_index("ym")
assert (dq.rows.astype(int) == T.rows).all() and (dq.amount.astype(int) == T.amount).all()

R = T.join(N1.add_prefix("naive_")).join(N2.add_prefix("skip_"), how="left").fillna(0)
R.to_csv(RES / "by_month.csv")
jul_skip_bad = int(pd.to_numeric(skip[skip.sales_date.str[:7] == "2025-07"].amount, errors="coerce").isna().sum())
out = {"files": 12, "rows_true": int(T.rows.sum()), "amount_true": int(T.amount.sum()),
       "naive": {"rows_read": len(naive), "header_rows_mixed": len(hdr), "amount_dtype": "文字（数でない値がまざる）",
                 "amount_not_numeric": int(num.isna().sum()), "amount_sum_numeric": int(num.sum()),
                 "amount_short_pct": round(float((1 - num.sum() / T.amount.sum()) * 100), 2),
                 "rows_counted_if_count_all": len(naive), "extra_rows": len(naive) - int(T.rows.sum()),
                 "mean_if_text_as_zero": round(float(num.fillna(0).mean()), 1), "mean_true": round(float(each.amount.mean()), 1),
                 "group_labels": sorted(naive_ym.unique().tolist())[-3:]},
       "skip_header": {"rows_read": len(skip), "jul_amount_not_numeric": jul_skip_bad, "amount_sum_numeric": int(num2.sum()),
                       "amount_short_pct": round(float((1 - num2.sum() / T.amount.sum()) * 100), 2)},
       "each_file": {"rows_read": len(each), "amount_sum": int(each.amount.sum())}, "sql_matches_truth": True}
json.dump(out, open(RES / "a733_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：まざった行の例（テキスト）
fig, ax = plt.subplots(figsize=(9, 3.4)); ax.axis("off")
i = hdr.index[0]; show = naive.iloc[i - 2:i + 3]
cell = [[str(k + 2)] + list(r) for k, r in zip(show.index, show.values)]
tb = ax.table(cellText=cell, colLabels=["つないだファイルの行", "sales_date", "store_id", "amount"], loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.5)
for (r, c), cl in tb.get_celld().items():
    if r == 0: cl.set_facecolor(LIGHT)
    elif cell[r - 1][1] == "sales_date": cl.set_facecolor("#fbd9c8")
ax.set_title(f"12本をそのままつなぐと、2本目以降の見出しが {len(hdr)}行、データの行として入る")
save(fig, "a733_mixed_rows.png", SRC)

# 図2：月ごとの合計（7月）
fig, ax = plt.subplots(figsize=(10, 3.8)); x = np.arange(12); wd = 0.27
ax.bar(x - wd, T.amount / 1e6, wd, color=GRAY, label="本当の合計")
ax.bar(x, R.naive_amount / 1e6, wd, color=ORANGE, label="そのままつないで数に直した合計")
ax.bar(x + wd, R.skip_amount / 1e6, wd, color=BLUE, label="見出しを飛ばしてつないだ合計")
ax.set_xticks(x); ax.set_xticklabels([f"{m}月" for m in range(1, 13)]); ax.set_ylabel("月の売上（百万円）"); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper left")
ax.set_ylim(0, T.amount.max() / 1e6 * 1.3)
ax.set_title("列の順が違う7月は、amount の列に店コードが入り、合計が0になる")
save(fig, "a733_monthly.png", SRC)

# 図3：読み方ごとの行数と合計
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6)); lab = ["本当", "そのまま\nつなぐ", "見出しを\n飛ばす", "1本ずつ\n読む"]
rows_ = [out["rows_true"], len(naive), len(skip), len(each)]; amt_ = [out["amount_true"], int(num.sum()), int(num2.sum()), int(each.amount.sum())]
cols = [GRAY, ORANGE, BLUE, GREEN]
axes[0].bar(lab, rows_, color=cols); axes[0].set_ylim(0, max(rows_) * 1.12)
for i_, v in enumerate(rows_): axes[0].text(i_, v + 60, f"{v:,}", ha="center", fontsize=9)
axes[0].set_ylabel("読んだ行数"); axes[0].set_title("行数")
axes[1].bar(lab, np.array(amt_) / 1e6, color=cols); axes[1].set_ylim(0, max(amt_) / 1e6 * 1.12)
for i_, v in enumerate(amt_): axes[1].text(i_, v / 1e6 + 0.3, f"{v / 1e6:.1f}", ha="center", fontsize=9)
axes[1].set_ylabel("年の合計（百万円）"); axes[1].set_title("amount を数に直した合計")
save(fig, "a733_totals.png", SRC)
print(json.dumps(out, ensure_ascii=False))
