"""684 桁区切りのカンマが入った数字を CSV に書き出すと、読み込みで何列がずれるのか

架空の売上表 2,000行（列：date・store・item・amount・qty）。金額 amount は 1,000円未満から 100万円を超えるものまである。
金額を「1,234」のような桁区切りつきの文字で書き出すとき、3通りの CSV を作る：
  引用符なし：2024-04-01,店03,品目12,1,234,5      … カンマが区切りと区別できない
  引用符あり：2024-04-01,店03,品目12,"1,234",5
  数字のまま：2024-04-01,店03,品目12,1234,5
読み込み方：
  引用符なし → (a) 列の数が合わない行を飛ばす（pandas の on_bad_lines="skip"）、(b) 区切りで分けて先頭から5列を取る（csv モジュール）
  引用符あり → (c) 文字のまま読む、(d) thousands="," を付けて読む、DuckDB では REPLACE で「,」を除いて数にする
  数字のまま → (e) そのまま読む（pandas と DuckDB）
本当の値と、ずれた行・読めた金額の合計を比べる。引用符ありと数字のままは DuckDB（1スレッド、02_read_duckdb.sql）でも読み、一致を確かめる。
"""
import csv
import io
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, DATA, save, SQL as SRC_DIR, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の売上表（作成者が乱数で作成、seed 684）"
rng = np.random.default_rng(684)
N = 2000
qty = rng.integers(1, 21, N)
price = np.round(rng.lognormal(np.log(600), 1.0, N), -1).astype(int).clip(50, 60000)
big = rng.random(N) < .02
qty = np.where(big, qty * 50, qty)
amount = qty * price
T = pd.DataFrame({"date": (pd.Timestamp("2024-04-01") + pd.to_timedelta(rng.integers(0, 90, N), "D")).strftime("%Y-%m-%d"),
                  "store": [f"店{s:02d}" for s in rng.integers(1, 21, N)],
                  "item": [f"品目{i:02d}" for i in rng.integers(1, 51, N)],
                  "amount": amount, "qty": qty})
true_total, true_qty = int(T.amount.sum()), int(T.qty.sum())
fmt = T.amount.map(lambda v: f"{v:,}")
DATA.mkdir(exist_ok=True)
head = "date,store,item,amount,qty\n"
lines_u = [f"{d},{s},{i},{a},{q}" for d, s, i, a, q in zip(T.date, T.store, T.item, fmt, T.qty)]
lines_q = [f'{d},{s},{i},"{a}",{q}' for d, s, i, a, q in zip(T.date, T.store, T.item, fmt, T.qty)]
lines_p = [f"{d},{s},{i},{a},{q}" for d, s, i, a, q in zip(T.date, T.store, T.item, T.amount, T.qty)]
for name, ls in [("sales_unquoted.csv", lines_u), ("sales_quoted.csv", lines_q), ("sales_plain.csv", lines_p)]:
    (DATA / name).write_text(head + "\n".join(ls) + "\n", encoding="utf-8")

# 引用符なし
recs = list(csv.reader(io.StringIO((DATA / "sales_unquoted.csv").read_text(encoding="utf-8"))))[1:]
nf = np.array([len(r) for r in recs])
n_commas = fmt.str.count(",").values
assert (nf == 5 + n_commas).all()
bad = nf != 5
a_skip = pd.read_csv(DATA / "sales_unquoted.csv", on_bad_lines="skip", engine="python")
pos = pd.DataFrame([r[:5] for r in recs], columns=["date", "store", "item", "amount", "qty"])
pos_amount = pos.amount.astype(int); pos_qty = pos.qty.astype(int)
# 引用符あり
q_text = pd.read_csv(DATA / "sales_quoted.csv")
q_num = pd.read_csv(DATA / "sales_quoted.csv", thousands=",")
assert q_num.amount.sum() == true_total and q_text.amount.dtype == object
# 数字のまま
p_num = pd.read_csv(DATA / "sales_plain.csv")
assert p_num.amount.sum() == true_total

# DuckDB
con = duckdb.connect(); con.execute("SET threads=1")
qs = [q.strip() for q in (SRC_DIR / "02_read_duckdb.sql").read_text(encoding="utf-8").split(";") if q.strip()]
qs = ["\n".join(l for l in q.splitlines() if not l.strip().startswith("--")) for q in qs]
d_q = con.execute(qs[0].replace("{path}", (DATA / "sales_quoted.csv").as_posix())).fetchone()[0]
d_p = con.execute(qs[1].replace("{path}", (DATA / "sales_plain.csv").as_posix())).fetchone()[0]
assert d_q == true_total and d_p == true_total

band = pd.cut(T.amount, [0, 999, 999_999, 10 ** 9], labels=["1,000円未満", "1,000円〜99万円台", "100万円以上"])
B = pd.DataFrame({"band": band, "fields": nf}).groupby("band", observed=False).agg(rows=("fields", "size"), fields=("fields", "first"))
B.to_csv(RES / "by_band.csv")
summary = pd.DataFrame([
    ("本当の値", N, true_total, true_qty),
    ("引用符なし：列数の合わない行を飛ばす", len(a_skip), int(a_skip.amount.sum()), int(a_skip.qty.sum())),
    ("引用符なし：先頭から5列を取る", len(pos), int(pos_amount.sum()), int(pos_qty.sum())),
    ("引用符あり：thousands=\",\" で読む", len(q_num), int(q_num.amount.sum()), int(q_num.qty.sum())),
    ("数字のまま", len(p_num), int(p_num.amount.sum()), int(p_num.qty.sum()))], columns=["way", "rows", "amount_sum", "qty_sum"])
summary.to_csv(RES / "summary.csv", index=False)

ex_i = int(np.where(n_commas == 1)[0][0]); ex_j = int(np.where(n_commas == 2)[0][0])
out = {"rows": N, "true_total": true_total, "true_qty": true_qty,
       "rows_by_commas": {str(k): int((n_commas == k).sum()) for k in range(3)},
       "unquoted_bad_rows": int(bad.sum()), "unquoted_bad_pct": round(100 * bad.mean(), 1),
       "unquoted_amount_share_in_bad_rows_pct": round(100 * T.amount[bad].sum() / true_total, 2),
       "skip": {"rows": len(a_skip), "amount_sum": int(a_skip.amount.sum()),
                "amount_vs_true_pct": round(100 * (a_skip.amount.sum() / true_total - 1), 2)},
       "by_position": {"amount_sum": int(pos_amount.sum()), "amount_vs_true_pct": round(100 * (pos_amount.sum() / true_total - 1), 2),
                       "qty_sum": int(pos_qty.sum()), "qty_vs_true_pct": round(100 * (pos_qty.sum() / true_qty - 1), 2),
                       "rows_amount_wrong": int((pos_amount != T.amount).sum()), "rows_qty_wrong": int((pos_qty != T.qty).sum())},
       "quoted_text_dtype": str(q_text.amount.dtype), "quoted_thousands_ok": True, "duckdb_quoted_sum": int(d_q), "duckdb_plain_sum": int(d_p),
       "example_1comma": {"line": lines_u[ex_i], "fields": recs[ex_i]},
       "example_2commas": {"line": lines_u[ex_j], "fields": recs[ex_j]}}
json.dump(out, open(RES / "a684_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：列の数
fig, ax = plt.subplots(figsize=(9, 4.4))
y = np.arange(3)[::-1]
ax.barh(y, B.rows.values, color=[BLUE, ORANGE, ORANGE])
for yy, r, f in zip(y, B.rows.values, B.fields.values):
    ax.text(r + 15, yy, f"{r:,}行 → {f}列（本来は5列）", va="center", fontsize=10)
ax.set_yticks(y); ax.set_yticklabels(B.index); ax.set_xlim(0, B.rows.max() * 1.55)
ax.set_xlabel("行の数（2,000行のうち）")
ax.set_title(f"引用符なしで書き出すと、1,000円以上の行（{int(bad.sum()):,}行・{100 * bad.mean():.1f}%）の列の数が狂う")
save(fig, "a684_fields.png", SRC)

# 図2：1行がどう分かれるか
fig, ax = plt.subplots(figsize=(9, 4.3)); ax.axis("off")
cols = ["date", "store", "item", "amount", "qty"]
def draw_row(y0, fields, title):
    ax.text(0, y0 + .1, title, fontsize=11, va="bottom")
    for k, f in enumerate(fields):
        x0 = .01 + k * .14
        lab = cols[k] if k < 5 else "（6列目以降）"
        color = BLUE if k < 3 else ORANGE
        ax.add_patch(plt.Rectangle((x0, y0 - .1), .13, .1, color=color, alpha=.18, transform=ax.transAxes))
        ax.text(x0 + .065, y0 - .05, f, ha="center", va="center", fontsize=10.5, transform=ax.transAxes)
        ax.text(x0 + .065, y0 - .14, lab, ha="center", va="center", fontsize=8.5, color=GRAY, transform=ax.transAxes)
r1 = out["example_1comma"]; r2 = out["example_2commas"]
draw_row(.78, r1["fields"], f"書き出した行：{r1['line']}")
draw_row(.38, r2["fields"], f"書き出した行：{r2['line']}")
ax.text(0, .02, "先頭から5列を取ると、amount にはカンマの前の数字、qty には金額の下3桁が入る", fontsize=9.5, color=GRAY)
ax.set_title("引用符なしの行は、金額のカンマで分かれて、後ろの列がずれる", fontsize=12)
save(fig, "a684_shift.png", SRC)

# 図3：読めた金額の合計
fig, ax = plt.subplots(figsize=(9, 4.4))
lab = ["本当の値", "引用符なし：\n合わない行を飛ばす", "引用符なし：\n先頭から5列", "引用符あり：\nthousands=\",\"", "数字のまま"]
vals = summary.amount_sum.values / 1e4
bars = ax.bar(range(5), vals, color=[GRAY, ORANGE, ORANGE, BLUE, BLUE], width=.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + vals.max() * .02, f"{v:,.0f}万円\n（{100 * (v * 1e4 / true_total - 1):+.1f}%）",
            ha="center", fontsize=9)
ax.set_xticks(range(5)); ax.set_xticklabels(lab, fontsize=9.5); ax.set_ylabel("読めた金額の合計（万円）")
ax.set_ylim(0, vals.max() * 1.25)
ax.set_title("引用符なしの CSV は、どう読んでも金額の合計がほとんど残らない")
save(fig, "a684_totals.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
