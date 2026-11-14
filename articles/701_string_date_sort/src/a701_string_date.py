"""701 「2024/1/5」のように0を埋めない日付を文字列のまま並べ替えると、何行が順番を間違えるのか

架空の注文（2024-01-01〜2025-12-31、6,000件）。日付は0を埋めない文字列「2024/1/5」で持つ。
  文字列のまま並べる／日付に直して並べる。位置のずれ、最初と最後の日、「最新N件」の取り違えを数える。
DuckDB（1スレッド）と pandas で一致を確かめる。seed 701。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の注文（作成者が乱数で作成、seed 701）"
rng = np.random.default_rng(701)
N = 6000
days = pd.date_range("2024-01-01", "2025-12-31")
w = np.linspace(1.0, 1.6, len(days))  # 後ろほど少し多い
d = pd.Series(rng.choice(days, size=N, p=w / w.sum())).sort_values().reset_index(drop=True)
od = pd.DataFrame({"order_id": np.arange(1, N + 1)})
od["order_date"] = d.values
od = od.sample(frac=1, random_state=701).reset_index(drop=True)
od["order_id"] = np.arange(1, N + 1)
od["order_date_txt"] = od.order_date.dt.year.astype(str) + "/" + od.order_date.dt.month.astype(str) + "/" + od.order_date.dt.day.astype(str)
od["amount"] = (rng.lognormal(8, 0.6, N) // 10 * 10).astype(int)
od[["order_id", "order_date_txt", "amount"]].to_csv(DATA / "orders.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("orders", od[["order_id", "order_date_txt", "amount"]])
q = [x for x in (SQL / "02_sort_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
pos = con.execute(q[0]).df().set_index("order_id").sort_index()
mm = con.execute(q[1]).df().iloc[0]
# pandas
od = od.sort_values("order_id").set_index("order_id")
od["pos_text"] = 0
o_t = od.reset_index().sort_values(["order_date_txt", "order_id"]); od.loc[o_t.order_id, "pos_text"] = np.arange(1, N + 1)
o_d = od.reset_index().sort_values(["order_date", "order_id"]); od["pos_date"] = 0; od.loc[o_d.order_id, "pos_date"] = np.arange(1, N + 1)
assert (od.pos_text.values == pos.pos_text.values).all() and (od.pos_date.values == pos.pos_date.values).all()
assert mm.min_text == od.order_date_txt.min() and mm.max_text == od.order_date_txt.max()
# 日付として正しい位置からずれた行（同じ日の中の順番は order_id で決めているので、ずれ＝日付の順番の誤り）
# 日付の順で並べたときの「本当の日付」と、文字列で並べたときの同じ位置の日付が違う行
seq_text_dates = od.sort_values("pos_text").order_date.values
seq_true_dates = od.sort_values("pos_date").order_date.values
wrong_pos = int((seq_text_dates != seq_true_dates).sum())
# 前の行より日付が戻っている箇所（文字列の順で読んだとき）
back = int((np.diff(seq_text_dates.astype("datetime64[D]").astype(int)) < 0).sum())
# 1桁の月・日を含む行
one_digit = float(((od.order_date.dt.month < 10) | (od.order_date.dt.day < 10)).mean() * 100)
# 「最新 N 件」：文字列で降順の上 N 件と、日付で降順の上 N 件の重なり
Ns = [10, 50, 100, 200, 500, 1000]
latest = {}
for n in Ns:
    a = set(od.sort_values("pos_text", ascending=False).index[:n]); b = set(od.sort_values("pos_date", ascending=False).index[:n])
    latest[n] = round(len(a & b) / n * 100, 1)
top100_text = od.sort_values("pos_text", ascending=False).head(100)
month_tab = top100_text.order_date.dt.to_period("M").astype(str).value_counts().sort_index()
# 期間で絞る：文字列で BETWEEN '2025/1/1' AND '2025/3/31'
f_text = od[(od.order_date_txt >= "2025/1/1") & (od.order_date_txt <= "2025/3/31")]
f_true = od[(od.order_date >= "2025-01-01") & (od.order_date <= "2025-03-31")]
out = {"orders": N, "period": "2024/1/1〜2025/12/31", "rows_with_one_digit_month_or_day_pct": round(one_digit, 1),
       "rows_in_wrong_date_position": wrong_pos, "rows_in_wrong_date_position_pct": round(wrong_pos / N * 100, 1),
       "date_goes_back_count": back,
       "min_text": mm.min_text, "max_text": mm.max_text, "min_date": mm.min_date, "max_date": mm.max_date,
       "latest_n_overlap_pct": {str(k): v for k, v in latest.items()},
       "latest100_text_months": month_tab.to_dict(),
       "between_text_rows": int(len(f_text)), "between_true_rows": int(len(f_true)),
       "between_text_true_overlap": int(len(set(f_text.index) & set(f_true.index))),
       "between_text_months": f_text.order_date.dt.to_period("M").astype(str).value_counts().sort_index().to_dict()}
json.dump(out, open(RES / "a701_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"n": Ns, "overlap_pct": [latest[n] for n in Ns]}).to_csv(RES / "latest_overlap.csv", index=False)

# 図1：文字列の順番での位置と、本当の日付
fig, ax = plt.subplots(figsize=(8, 4))
s = od.sort_values("pos_text")
ax.scatter(s.pos_text, s.order_date, s=2, color=ORANGE, label="文字列のまま並べた順")
s2 = od.sort_values("pos_date")
ax.plot(s2.pos_date, s2.order_date, color=BLUE, lw=1.5, label="日付に直して並べた順")
ax.set_xlabel("並べたあとの行の位置"); ax.set_ylabel("その行の本当の日付")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("文字列のまま並べると「1月→10月→11月→12月→2月…」の順に飛ぶ")
save(fig, "a701_order.png", SRC)
# 図2：最新 N 件の重なり
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(Ns, [latest[n] for n in Ns], "o-", color=ORANGE)
for n in Ns:
    ax.annotate(f"{latest[n]:.0f}%", (n, latest[n]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=9)
ax.set_xscale("log"); ax.set_xticks(Ns); ax.set_xticklabels(Ns); ax.set_ylim(-5, 105)
ax.set_xlabel("「最新 N 件」の N"); ax.set_ylabel("本当の最新 N 件と重なる割合（%）")
ax.set_title("文字列で降順にした「最新 N 件」は、本当の最新とほとんど重ならない")
save(fig, "a701_latest.png", SRC)
# 図3：文字列の BETWEEN '2025/1/1' AND '2025/3/31' で取れた行の月
fig, ax = plt.subplots(figsize=(8, 3.6))
mt = f_text.order_date.dt.to_period("M").astype(str).value_counts().sort_index()
mtr = f_true.order_date.dt.to_period("M").astype(str).value_counts().reindex(mt.index).fillna(0)
x = np.arange(len(mt))
ax.bar(x - 0.2, mtr.values, 0.4, color=BLUE, label="日付で 2025/1/1〜3/31")
ax.bar(x + 0.2, mt.values, 0.4, color=ORANGE, label="文字列で '2025/1/1'〜'2025/3/31'")
ax.set_xticks(x); ax.set_xticklabels(mt.index); ax.set_ylabel("件数"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"文字列で1〜3月を絞ると {len(f_text):,}件（本当は{len(f_true):,}件）。10〜12月が混ざり、3月の一部が落ちる")
save(fig, "a701_between.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
