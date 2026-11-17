"""図を4枚つくる（results/ と data/ を読むだけ）。"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
SRC = "出典：総務省「家計調査」二人以上の世帯 第3-12表・長期時系列 表2（2015年1月〜2026年9月）をもとに作成者が加工して作成"
main = json.loads((RES / "main.json").read_text())
d = pd.read_csv(ROOT / "data" / "monthly_groups.csv")

# 図1：年金の世帯の公的年金給付と消費支出（2022年1月〜）
w = d[(d.group == "m65_nowork") & d.item.isin(["公的年金給付", "消費支出"])].pivot_table(
    index=["year", "month"], columns="item", values="value").reset_index()
w = w[w.year >= 2022].reset_index(drop=True)
x = np.arange(len(w))
fig, ax = plt.subplots(figsize=(9, 4.6))
fig.subplots_adjust(left=0.09, right=0.97, top=0.86, bottom=0.2)
ax.bar(x, w["公的年金給付"] / 1e4, width=0.7, color=C[0], label="公的年金給付（受け取り）")
ax.plot(x, w["消費支出"] / 1e4, color=C[1], lw=2, marker="o", ms=3.5, label="消費支出")
ticks = [i for i in x if w.month[i] in (1, 7)]
ax.set_xticks(ticks, [f"{w.year[i]}年{w.month[i]}月" for i in ticks], fontsize=9)
ax.set_ylabel("1世帯あたり、月（万円）")
style(ax)
ax.legend(frameon=False, loc="upper left", ncol=2, bbox_to_anchor=(0, 1.02))
h = main["H1"]
fig.suptitle(f"年金は偶数月に約{h['pension_even_mean_yen']/1e4:.0f}万円入るが、消費支出はほぼ毎月同じ高さ",
             x=0.01, ha="left", fontsize=12.5, color=INK)
save(fig, FIG / "fig1_pension_vs_spending.png", SRC, "世帯主が65歳以上の無職世帯（二人以上の世帯）。2022年1月〜2026年9月を表示。")

# 図2：暦の月ごとの差（年金の世帯 − 対照、年の平均からのずれ）
cal = pd.read_csv(RES / "calmonth_logdiff_consumption.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.6))
fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.22)
col = [C[0] if m % 2 == 0 else "#b9b8b3" for m in cal.month]
se = cal["std"] / np.sqrt(cal["count"])
ax.bar(cal.month, cal["mean"], width=0.65, color=col)
ax.errorbar(cal.month, cal["mean"], yerr=1.96 * se, fmt="none", ecolor=INK2, lw=1, capsize=3)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(1, 13), [f"{m}月" for m in range(1, 13)])
ax.set_ylabel("消費支出の差（%）")
style(ax)
r = main["H2"]["reg"]
fig.suptitle(f"偶数月だけが高い形は見えない（偶数月の上乗せ {r['pct']:+.1f}%、95%区間 {r['lo']:+.1f}〜{r['hi']:+.1f}%）",
             x=0.01, ha="left", fontsize=12.5, color=INK)
ax.text(0.01, 0.99, "青＝偶数月（年金の受け取り月）　灰＝奇数月\n線は95%区間（12年分の振れ）", transform=ax.transAxes,
        ha="left", va="top", fontsize=8.8, color=INK2)
save(fig, FIG / "fig2_calmonth_gap.png", SRC,
     "差＝log（65歳以上の無職世帯）−log（65歳未満の勤労者世帯）。両方に共通の季節は消えるが、世帯ごとに違う季節（春の低さ・年末の高さ）は残る。")

# 図3：頑健性
rob = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(figsize=(8.6, 4.8))
fig.subplots_adjust(left=0.36, right=0.97, top=0.86, bottom=0.18)
y = np.arange(len(rob))[::-1]
ax.axvline(0, color=INK2, lw=0.8)
ax.axvspan(1, 3, color=GRID, alpha=0.5, lw=0)
ax.hlines(y, rob.lo, rob.hi, color=C[0], lw=2)
ax.plot(rob.pct, y, "o", color=C[0], ms=7, mec="#fcfcfb", mew=1.5)
for yi, (p, hi) in zip(y, zip(rob.pct, rob.hi)):
    ax.text(max(hi, p) + 0.15, yi, f"{p:+.1f}%", va="center", fontsize=8.8, color=INK2)
ax.set_yticks(y, rob.check, fontsize=9)
ax.set_xlabel("偶数月の消費支出の上乗せ（%）。点＝推定、線＝95%区間")
ax.text(2, y[0] + 0.55, "事前に決めた「上乗せあり」\nの基準（+1%以上）", ha="center", fontsize=8, color=INK2)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_axisbelow(True)
fig.suptitle("比べ方を変えると、上乗せは −1%〜+1%前後で揺れる", x=0.01, ha="left", fontsize=12.5, color=INK)
save(fig, FIG / "fig3_robustness.png", SRC, "年の固定効果つきの回帰。標準誤差は Newey-West（ラグ3）。")

# 図4：費目別
it = pd.read_csv(RES / "item_effects.csv")
order = ["食料（外食を除く）", "光熱・水道", "外食", "被服及び履物", "教養娯楽", "交際費", "住居", "家具・家事用品", "交通・通信",
         "その他の消費支出"]
it = it.set_index("item").loc[order].reset_index()
colmap = {"毎月ほぼ決まった": C[2], "後回しにできる": C[1], "その他": "#8f8e89"}
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.24, right=0.97, top=0.84, bottom=0.17)
y = np.arange(len(it))[::-1]
ax.axvline(0, color=INK2, lw=0.8)
for yi, row in zip(y, it.itertuples()):
    ax.hlines(yi, max(row.lo, -10), min(row.hi, 10), color=colmap[row.group], lw=2)
    ax.plot(row.pct, yi, "o", color=colmap[row.group], ms=7, mec="#fcfcfb", mew=1.5)
    ax.text(12.8, yi, f"{row.pct:+.1f}%", va="center", ha="right", fontsize=8.8, color=INK2)
ax.set_yticks(y, it.item, fontsize=9.5)
ax.set_xlim(-10, 13)
ax.set_xticks([-10, -5, 0, 5, 10])
ax.set_xlabel("偶数月の上乗せ（%）。線は95%区間（±10%で切った）")
for k, (lab, c) in enumerate(colmap.items()):
    ax.plot([], [], "o", color=c, label=lab)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=8.8)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_axisbelow(True)
h3 = main["H3"]
fig.suptitle(f"後回しにできる支出も、決まった支出も、上乗せは平均で同じくらい（{h3['disc_mean_pct']:+.1f}% と {h3['basic_mean_pct']:+.1f}%）",
             x=0.01, ha="left", fontsize=12, color=INK)
save(fig, FIG / "fig4_items.png", SRC, "対照は65歳未満の勤労者世帯。色は事前の計画での費目の分け方。住居の区間は ±10% をこえる。")
print("figures ok")
