"""714 空白のセルと0のセルが混ざった列を Excel の AVERAGE で平均すると、値はどれだけ変わるのか

架空の30店×60日の「1日の問い合わせ件数」の記録表（列が店、行が日）。本当の件数は店ごとのポアソン分布（0の日もある）。
入力のされ方：8%の日は未入力（空白）、5%の日は文字で入力（"7" のような文字列）。
平均の出し方（Excel の動きは Python で再現。Excel では未検証）：
  AVERAGE：数のセルだけを平均（空白と文字は数えない）
  AVERAGEA：文字を0として数え、空白は数えない
  SUM÷60：空白を0とみなすのと同じ（文字は SUM に入らない）
  文字を数に直してから AVERAGE：入力のある日だけの平均
を、本当の60日の平均と比べる。seed 714。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店の日次の記録（作成者が乱数で作成、seed 714）"
rng = np.random.default_rng(714)
NS, ND = 30, 60
lam = np.exp(rng.uniform(np.log(0.8), np.log(15), NS))
true = rng.poisson(lam, (ND, NS))
u = rng.random((ND, NS))
blank = u < 0.08
text = (u >= 0.08) & (u < 0.13)
cells = np.empty((ND, NS), dtype=object)
for i in range(ND):
    for j in range(NS):
        cells[i, j] = "" if blank[i, j] else (str(true[i, j]) if text[i, j] else int(true[i, j]))
cols = [f"店{j + 1:02d}" for j in range(NS)]
sheet = pd.DataFrame(cells, columns=cols)
# CSV では文字の数を区別できないので、文字のセルは先頭に ' を付けて書き出す（Excel で文字として入力したときの見た目）
sheet.map(lambda v: "'" + v if isinstance(v, str) and v != "" else v).to_csv(DATA / "daily_sheet.csv", index_label="日")


def is_num(v):
    return isinstance(v, (int, np.integer))


num = np.vectorize(is_num)(cells)
vals = np.where(num, cells, 0).astype(float)
textv = np.where(text, true, 0).astype(float)
R = pd.DataFrame(index=cols)
R["true_mean"] = true.mean(0)
R["AVERAGE"] = vals.sum(0) / num.sum(0)
R["AVERAGEA"] = vals.sum(0) / (num.sum(0) + text.sum(0))
R["SUM_div_60"] = vals.sum(0) / ND
R["text_fixed_AVERAGE"] = (vals.sum(0) + textv.sum(0)) / (num.sum(0) + text.sum(0))
R["n_number"] = num.sum(0); R["n_text"] = text.sum(0); R["n_blank"] = blank.sum(0)
assert ((R.n_number + R.n_text + R.n_blank) == ND).all()
M = ["AVERAGE", "AVERAGEA", "SUM_div_60", "text_fixed_AVERAGE"]
for m in M:
    R[m + "_pct"] = (R[m] / R.true_mean - 1) * 100
R.round(3).to_csv(RES / "by_store.csv")
lab = {"AVERAGE": "AVERAGE", "AVERAGEA": "AVERAGEA（文字を0）", "SUM_div_60": "SUM÷60（空白を0）", "text_fixed_AVERAGE": "文字を数に直して AVERAGE"}
out = {"stores": NS, "days": ND, "blank_cells_pct": round(float(blank.mean() * 100), 1), "text_cells_pct": round(float(text.mean() * 100), 1),
       "true_zero_cells_pct": round(float((true == 0).mean() * 100), 1),
       "mean_abs_error_pct": {lab[m]: round(float(R[m + "_pct"].abs().mean()), 2) for m in M},
       "mean_error_pct": {lab[m]: round(float(R[m + "_pct"].mean()), 2) for m in M},
       "max_abs_error_pct": {lab[m]: round(float(R[m + "_pct"].abs().max()), 1) for m in M},
       "counted_cells_mean": {"AVERAGE": round(float(R.n_number.mean()), 1), "AVERAGEA": round(float((R.n_number + R.n_text).mean()), 1), "SUM÷60": ND},
       "stores_off_by_5pct_or_more": {lab[m]: int((R[m + "_pct"].abs() >= 5).sum()) for m in M}}
json.dump(out, open(RES / "a714_main.json", "w"), ensure_ascii=False, indent=1)

colr = {"AVERAGE": BLUE, "AVERAGEA": ORANGE, "SUM_div_60": GRAY, "text_fixed_AVERAGE": GREEN}
# 図1：店ごとのずれ
fig, ax = plt.subplots(figsize=(8.5, 3.8)); o = R.sort_values("true_mean"); x = np.arange(NS)
for m in M:
    ax.scatter(x, o[m + "_pct"], s=18, color=colr[m], label=lab[m])
ax.axhline(0, color="black", lw=0.6); ax.set_xticks(x); ax.set_xticklabels(o.index, rotation=90, fontsize=7)
ax.set_ylabel("本当の平均とのずれ（%）"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title("店を本当の平均の小さい順に並べたずれ：AVERAGEA と SUM÷60 は小さく出る")
save(fig, "a714_by_store.png", SRC)
# 図2：平均のずれと数えたセルの数
fig, ax = plt.subplots(figsize=(8, 3.6))
v = [out["mean_error_pct"][lab[m]] for m in M]
ax.bar([lab[m] for m in M], v, color=[colr[m] for m in M])
for i, a in enumerate(v):
    ax.text(i, a + (0.3 if a >= 0 else -0.9), f"{a:+.1f}%", ha="center")
ax.axhline(0, color="black", lw=0.6); ax.set_ylabel("30店の平均のずれ（%）"); ax.tick_params(axis="x", labelsize=8.5)
ax.set_title("SUM÷60 は約12%（空白も文字も抜ける）、AVERAGEA は約5%小さく出る")
save(fig, "a714_mean_error.png", SRC)
# 図3：表の一部（見た目）
fig, ax = plt.subplots(figsize=(8, 3.6)); ax.axis("off")
part = sheet.iloc[:10, :8].copy()
show = part.map(lambda v: "（空白）" if v == "" else (f'"{v}"' if isinstance(v, str) else str(v)))
tb = ax.table(cellText=show.values, colLabels=part.columns, rowLabels=[f"{i + 1}日" for i in range(10)], loc="center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(8.5)
for (i, j), c in tb.get_celld().items():
    if i > 0 and j >= 0:
        v = part.iloc[i - 1, j]
        if v == "":
            c.set_facecolor("#fde3d6")
        elif isinstance(v, str):
            c.set_facecolor("#dbe8f8")
ax.set_title("記録表の一部：空白（オレンジ）と文字の数（青、\"7\" のように表示）が混ざる", fontsize=11)
save(fig, "a714_sheet.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
