"""305 図3枚"""
import json
import matplotlib.pyplot as plt, pandas as pd
from matplotlib.patches import FancyBboxPatch
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

df = pd.read_csv(RES / "measures.csv")
fmt = lambda i, v: f"{v*100:.1f}%" if i == "M07" else ("（空）" if float(v) == 0 else f"{float(v)/1e4:,.0f}万円")

# 図1：12本の表
fig, ax = plt.subplots(figsize=(11.5, 6.2)); ax.axis("off")
ax.set_title("12本のメジャーを、決まりどおりの読みと2つの単純な読みで計算した\n（評価する場所：スライサー 年=2025・地域=関東、行=日用品）", loc="left")
cols = ["", "メジャー（DAX、実行はしていない）", "決まりどおり", "足すだけの読み", "入れ替える読み"]
xs = [0.0, 0.04, 0.60, 0.74, 0.88]
y = 0.93
for x, c in zip(xs, cols): ax.text(x, y, c, fontsize=9.5, weight="bold", transform=ax.transAxes)
for r in df.itertuples():
    y -= 0.071
    ax.text(xs[0], y, r.id, fontsize=8.5, color=GRAY, transform=ax.transAxes)
    ax.text(xs[1], y, r.dax.replace("　※スライサーが店（S02）のとき", " ※店で絞り込み"), fontsize=8.2, family=["DejaVu Sans Mono", "Noto Sans CJK JP"], transform=ax.transAxes)
    ax.text(xs[2], y, fmt(r.id, r.correct), fontsize=9, transform=ax.transAxes)
    ax.text(xs[3], y, ("✗ " if r.naive_wrong else "") + fmt(r.id, r.naive), fontsize=9, color=ORANGE if r.naive_wrong else GRAY, transform=ax.transAxes)
    ax.text(xs[4], y, ("✗ " if r.naive_b_wrong else "") + fmt(r.id, r.naive_b), fontsize=9, color=ORANGE if r.naive_b_wrong else GRAY, transform=ax.transAxes)
ax.text(0, 0.02, f"✗ は決まりどおりの値と違うもの。足すだけの読みは12本中{int(df.naive_wrong.sum())}本、入れ替える読みは{int(df.naive_b_wrong.sum())}本で違った",
        fontsize=9, color=INK, transform=ax.transAxes)
save(fig, "a305_table.png", y=-0.01)

# 図2：入れ替えの4本
pick = ["M01", "M02", "M04", "M05", "M06"]
lab = ["M01\nそのまま\n（日用品）", "M02\ncategory = \"食品\"", "M04\nregion = \"関西\"", "M05\nyear = 2024", "M06\nALL ( category )"]
d = df.set_index("id").loc[pick]
fig, ax = plt.subplots(figsize=(9, 4.6))
x = range(len(pick))
ax.bar([i - 0.2 for i in x], d["correct"].astype(float) / 1e4, 0.4, color=BLUE, label="決まりどおり（同じ列の絞り込みを入れ替える・外す）")
ax.bar([i + 0.2 for i in x], d["naive"].astype(float) / 1e4, 0.4, color=ORANGE, label="足すだけの読み（WHERE に AND で足す）")
for i, (a, b) in enumerate(zip(d["correct"].astype(float) / 1e4, d["naive"].astype(float) / 1e4)):
    ax.text(i - 0.2, a, f"{a:,.0f}", ha="center", va="bottom", fontsize=8.5)
    ax.text(i + 0.2, b, f"{b:,.0f}" if b else "空", ha="center", va="bottom", fontsize=8.5, color=ORANGE)
ax.set_xticks(list(x)); ax.set_xticklabels(lab, fontsize=9); ax.set_ylabel("売上（万円）")
ax.set_title("CALCULATE の条件は、同じ列の絞り込みを入れ替える。足すだけと読むと空になる", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "a305_replace.png")

# 図3：絞り込みがどう変わるか
fig, ax = plt.subplots(figsize=(11, 5)); ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 5)
ax.set_title("絞り込み（フィルター文脈）は、列ごとの箱で考える", loc="left")
def box(x, y, t, c, w=1.9): 
    ax.add_patch(FancyBboxPatch((x, y), w, 0.55, boxstyle="round,pad=0.03", fc=c, ec="none"))
    ax.text(x + w / 2, y + 0.27, t, ha="center", va="center", fontsize=9)
rowsd = [
 ("いまのセル", ["年 = 2025", "地域 = 関東", "カテゴリ = 日用品"], [LIGHT] * 3, "→ 日用品の売上"),
 ('category = "食品"', ["年 = 2025", "地域 = 関東", "カテゴリ = 食品"], [LIGHT, LIGHT, "#f6c3ad"], "→ 同じ列の箱を入れ替える（M02）"),
 ('KEEPFILTERS ( category = "食品" )', ["年 = 2025", "地域 = 関東", "日用品 かつ 食品"], [LIGHT, LIGHT, "#f6c3ad"], "→ 箱の中で重ねる。空になる（M03）"),
 ("ALL ( category )", ["年 = 2025", "地域 = 関東", "（箱を外す）"], [LIGHT, LIGHT, "#e8e7e3"], "→ 全カテゴリの売上（M06）"),
 ('region = "関西"　※店で絞り込み', ["年 = 2025", "店 = S02", "地域 = 関西", "カテゴリ = 日用品"], [LIGHT, LIGHT, "#f6c3ad", LIGHT], "→ 違う列は箱が増えるだけ。空（M10）"),
]
for k, (name, bs, cs, res) in enumerate(rowsd):
    y = 4.1 - k * 0.92
    ax.text(0.0, y + 0.27, name, fontsize=9, va="center", family=["DejaVu Sans Mono", "Noto Sans CJK JP"])
    w = 1.9 if len(bs) == 3 else 1.42
    for j, (b, c) in enumerate(zip(bs, cs)): box(3.2 + j * (w + 0.1), y, b, c, w)
    ax.text(9.25, y + 0.27, res, fontsize=8.8, va="center")
save(fig, "a305_context.png", y=0.0)
print("ok")
