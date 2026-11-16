"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省「貿易統計」輸出入額の推移（地域（国）別・主要商品別）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
tot = pd.read_csv(R / "total_share.csv").set_index("year")
t = pd.read_csv(R / "item_shares.csv")
items = pd.read_csv(D / "items.csv").set_index("code")

# 図1 総額に占める中国・ASEAN の割合
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(tot.index, tot.china, color=C[1], lw=2.4, label="中国（輸入総額に占める割合）")
ax.plot(tot.index, tot.china_ex_fuel, color=C[1], lw=1.3, ls="--", label="中国（鉱物性燃料を除く総額に占める割合）")
ax.plot(tot.index, tot.asean, color=C[0], lw=2.2, label="ASEAN")
ax.annotate(f"{m['china_share_peak_year']}年 {m['china_share_peak']:.1f}%", (m["china_share_peak_year"], m["china_share_peak"]), xytext=(2011, 34), fontsize=9, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.text(2025.3, tot.loc[2025, "china"], f"{tot.loc[2025,'china']:.1f}", fontsize=9, color=C[1], va="center")
ax.text(2025.3, tot.loc[2025, "china_ex_fuel"], f"{tot.loc[2025,'china_ex_fuel']:.1f}", fontsize=9, color=C[1], va="center")
ax.text(2025.3, tot.loc[2025, "asean"], f"{tot.loc[2025,'asean']:.1f}", fontsize=9, color=C[0], va="center")
ax.set_xlim(1987.5, 2027.5); ax.set_ylim(0, 36)
ax.set_ylabel("輸入額に占める割合（%）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"中国の割合は{m['china_share_peak_year']}年の{m['china_share_peak']:.1f}%が山で、2025年は{m['china_share_2025']:.1f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, F / "fig1_total_share.png", SRC)

# 図2 2015年→2025年（2015年に30%以上の品目と、大きく上がった品目）
sel = t[(t.cn0 >= 30) | (t.change >= 5)].sort_values("cn0")
fig, ax = plt.subplots(figsize=(8.8, 6.0))
y = np.arange(len(sel))
for i, r in enumerate(sel.itertuples()):
    col = C[0] if r.cn1 < r.cn0 else C[1]
    ax.plot([r.cn0, r.cn1], [i, i], color=col, lw=2)
ax.scatter(sel.cn0, y, color=C[5], s=26, zorder=3, label="2015年")
ax.scatter(sel.cn1, y, color=[C[0] if a < b else C[1] for a, b in zip(sel.cn1, sel.cn0)], s=34, zorder=3, label="2025年（青は下がった、橙は上がった）")
ax.set_yticks(y, sel["item"])
ax.set_xlim(0, 100)
ax.set_xlabel("その品目の輸入額に占める中国の割合（%）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower right", fontsize=8.8)
ax.set_title(f"2015年に30%以上だった{m['n_hi']}品目のうち{m['n_hi_down']}品目で下がったが、通信機・電算機類は6〜7割", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.24, right=0.97, top=0.93, bottom=0.15)
save(fig, F / "fig2_items_2015_2025.png", SRC, "注：2015年に中国の割合が30%以上の品目と、2025年までに5ポイント以上上がった品目。並びは2015年の割合の順。")

# 図3 中国の割合の変化と ASEAN の割合の変化
fig, ax = plt.subplots(figsize=(8.0, 5.8))
big = t[t.w1 >= 5e8]
ax.scatter(big.change, big.asean_change, s=np.sqrt(big.w1) / 1.6e3, color=C[0], alpha=0.6, edgecolor="white")
for r in big.itertuples():
    if abs(r.change) >= 8 or abs(r.asean_change) >= 8:
        ax.annotate(r.item, (r.change, r.asean_change), xytext=(4, 3), textcoords="offset points", fontsize=8.5, color=INK2)
ax.axhline(0, color=INK2, lw=0.8); ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-22, 13)
ax.set_xlabel("中国の割合の変化（2015→2025年、ポイント）")
ax.set_ylabel("ASEAN の割合の変化（ポイント）")
style(ax)
ax.set_title(f"中国の割合が下がった{m['n_down']}品目のうち{m['n_down_asean_up']}品目で ASEAN が上がった", loc="left", fontsize=12)
fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.17)
save(fig, F / "fig3_china_vs_asean.png", SRC, "注：2025年の輸入額が500億円以上の品目。円の大きさは2025年の輸入額。")

# 図4 シフト・シェア分解
ss = pd.read_csv(R / "shift_share.csv").set_index("code")
lab = lambda c: "その他の品目" if c == "other" else items.loc[c, "press_name"]
top = ss.within_contrib_pt.sort_values()
show = list(top.index[:5]) + list(top.index[-3:])
fig, ax = plt.subplots(1, 2, figsize=(9.6, 4.8), gridspec_kw={"width_ratios": [1, 1.6]})
ax[0].bar(["合計の変化", "品目の中の\n割合の変化", "品目の構成\nの変化"], [q["total_change_pt"], q["within_pt"], q["composition_pt"]], color=[INK2, C[0], C[3]])
for i, v in enumerate([q["total_change_pt"], q["within_pt"], q["composition_pt"]]):
    ax[0].text(i, v + (0.06 if v >= 0 else -0.16), f"{v:+.2f}", ha="center", fontsize=9.5)
ax[0].axhline(0, color=INK2, lw=0.8); ax[0].set_ylabel("ポイント"); style(ax[0]); ax[0].set_ylim(-2.6, 1.2)
vals = ss.loc[show, "within_contrib_pt"]
ax[1].barh([lab(c) for c in show][::-1], vals.values[::-1], color=[C[0] if v < 0 else C[1] for v in vals.values[::-1]])
ax[1].axvline(0, color=INK2, lw=0.8)
ax[1].set_xlabel("品目の中の割合の変化の寄与（ポイント）")
ax[1].grid(axis="x", color=GRID, lw=0.8); ax[1].set_axisbelow(True)
fig.suptitle(f"総額の中国の割合（2015→25年 {q['total_change_pt']:+.2f}ポイント）を下げたのは、主に品目の中での変化（衣類など）", x=0.01, ha="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.17, wspace=0.55)
save(fig, F / "fig4_shift_share.png", SRC, "注：38品目と「その他の品目」で分解。品目の構成の変化には、燃料の重みの低下（23.1%→19.5%）などが入る。")
