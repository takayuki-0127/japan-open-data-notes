"""図を4枚つくる（results/ を読むだけ）。"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
SRC = "出典：総務省「家計調査」二人以上の世帯のうち勤労者世帯 第3-11表・第2-4表（2000〜2025年）をもとに作成者が加工して作成"
main = json.loads((RES / "main.json").read_text())
yr = pd.read_csv(RES / "gap_by_year.csv")
ITEMS = [("調理食品", C[0]), ("一般外食", C[1]), ("生鮮食品", C[2])]

# 図1：年ごとの差
fig, ax = plt.subplots(figsize=(8.8, 4.8))
fig.subplots_adjust(left=0.1, right=0.86, top=0.82, bottom=0.2)
ax.axhline(0, color=INK2, lw=0.8)
for it, c in ITEMS:
    ax.plot(yr.year, yr[f"gap_{it}"], color=c, lw=2, marker="o", ms=3.5)
    ax.text(2025.4, yr[f"gap_{it}"].iloc[-1] + {"調理食品": 2.2, "一般外食": -0.6, "生鮮食品": 0}[it], it, color=INK, va="center", fontsize=9.5)
ax.set_xlim(1999.5, 2025.5)
ax.set_ylabel("共働き − 夫のみ有業（%）")
style(ax)
m = main["main"]
fig.suptitle(f"共働きの調理食品は26年すべてで多いが、差は {m['調理食品']['first5_mean']:.0f}% から {m['調理食品']['last5_mean']:.0f}% に縮んだ",
             x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.885, "夫婦と未婚の子供2人の世帯。1世帯あたりの月の支出の差（対数の差×100）", va="top", fontsize=9, color=INK2)
save(fig, FIG / "fig1_gap_by_year.png", SRC, "差は2000〜2004年と2021〜2025年の平均。生鮮食品＝生鮮魚介・生鮮肉・生鮮野菜・生鮮果物の合計。")

# 図2：収入をそろえる前と後
labs = ["調理食品", "一般外食", "生鮮食品", "食料"]
raw = [m[i]["mean"] for i in labs]
adj = [m[i]["adj_mean"] for i in labs]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.2)
x = np.arange(len(labs))
w = 0.36
ax.bar(x - w / 2 - 0.01, raw, width=w, color="#b9b8b3", label="そのままの差")
ax.bar(x + w / 2 + 0.01, adj, width=w, color=C[0], label="収入の差の分を引いた差")
for xi, (r, a) in enumerate(zip(raw, adj)):
    ax.text(xi - w / 2 - 0.01, r + (0.5 if r >= 0 else -0.5), f"{r:+.1f}", ha="center", va="bottom" if r >= 0 else "top", fontsize=9, color=INK2)
    ax.text(xi + w / 2 + 0.01, a + (0.5 if a >= 0 else -0.5), f"{a:+.1f}", ha="center", va="bottom" if a >= 0 else "top", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, labs)
ax.set_ylabel("共働き − 夫のみ有業（%、26年の平均）")
ax.set_ylim(-10, 18)
style(ax)
ax.legend(frameon=False, loc="upper right")
fig.suptitle("収入の差の分を引くと、外食の差はほぼ消え、調理食品の差は残る", x=0.01, ha="left", fontsize=12.5, color=INK)
save(fig, FIG / "fig2_income_adjusted.png", SRC,
     f"引いた分＝品目の支出の伸び方（年間収入五分位から出した弾力性）×消費支出の差（平均 +{main['H3']['budget_gap_mean']:.1f}%）。夫婦と子供2人の世帯。")

# 図3：妻の勤め先収入の区分（問い直し）
rq = pd.read_csv(RES / "requestion_wife_income.csv")
its = ["調理食品", "一般外食", "生鮮食品"]
grp = ["妻の勤め先収入 月1〜79,999円", "妻の勤め先収入 月8万円以上"]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.2)
x = np.arange(len(its))
for k, (g, c) in enumerate(zip(grp, ["#b9b8b3", C[0]])):
    v = [float(rq[(rq.group == g) & (rq["item"] == it)].per_person_gap.iloc[0]) for it in its]
    xs = x + (k - 0.5) * (w + 0.02)
    ax.bar(xs, v, width=w, color=c, label=g.replace("妻の勤め先収入 ", "共働き：妻の勤め先収入 "))
    for xi, vi in zip(xs, v):
        ax.text(xi, vi + (0.6 if vi >= 0 else -0.6), f"{vi:+.1f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, its)
ax.set_ylabel("夫のみ有業（計）との差（%、1人あたり、26年の平均）")
ax.set_ylim(-14, 36)
style(ax)
ax.legend(frameon=False, loc="upper left")
fig.suptitle("差が出るのは、妻の勤め先収入が月8万円以上の共働き", x=0.01, ha="left", fontsize=12.5, color=INK)
save(fig, FIG / "fig3_wife_income.png", SRC, "共働きは有業者が夫婦のみの核家族。世帯の人数が違うので1人あたりにして比べた（収入の差の分は引いていない）。")

# 図4：頑健性
rob = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.6))
fig.subplots_adjust(left=0.4, right=0.97, top=0.82, bottom=0.2)
y = np.arange(len(rob))[::-1]
ax.axvline(0, color=INK2, lw=0.8)
ax.hlines(y, rob.cooked_adj, rob.cooked, color=GRID, lw=3)
ax.plot(rob.cooked, y, "o", color="#9a9994", ms=8, mec="#fcfcfb", mew=1.5, label="そのままの差")
ax.plot(rob.cooked_adj, y, "o", color=C[0], ms=8, mec="#fcfcfb", mew=1.5, label="収入の差の分を引いた差")
for yi, v in zip(y, rob.cooked_adj):
    ax.text(v - 0.5, yi, f"{v:+.1f}", ha="right", va="center", fontsize=8.8, color=INK)
ax.set_yticks(y, rob.check, fontsize=9)
ax.set_xlabel("調理食品の差（共働き − 夫のみ有業、%、年の平均）")
ax.set_xlim(-2, 20)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9)
fig.suptitle("調理食品の差は、比べ方を変えてもプラスに残る（夫婦のみの世帯では小さい）", x=0.01, ha="left", fontsize=12, color=INK)
save(fig, FIG / "fig4_robustness.png", SRC, "本線は夫婦と子供2人の世帯、弾力性は勤労者世帯の年間収入五分位（2018〜2025年）から。")
print("figures ok")
