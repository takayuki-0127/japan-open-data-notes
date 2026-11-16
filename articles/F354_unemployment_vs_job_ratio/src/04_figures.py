"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省「労働力調査」、厚生労働省「一般職業紹介状況」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(R / "annual_indicators.csv").set_index("year")
bev = pd.read_csv(R / "beveridge_by_decade.csv")
sp = pd.read_csv(R / "requestion_ratio_split.csv")

# ---- 図1：失業率と有効求人倍率（上下2段） --------------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(8.8, 5.6), sharex=True)
axes[0].plot(d.index, d.u_rate, color=C[1], lw=2)
axes[0].set_ylabel("完全失業率（%）"); axes[0].set_ylim(0, 6)
axes[1].plot(d.index, d.ratio, color=C[0], lw=2)
axes[1].axhline(1, color=INK2, lw=0.8, ls=":")
axes[1].set_ylabel("有効求人倍率（倍）"); axes[1].set_ylim(0, 2)
for ax in axes:
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for y in [1973, 1990, 2002, 2009, 2018]:
        ax.axvline(y, color=GRID, lw=1, zorder=0)
for y in [2002, 2018, 2025]:
    axes[0].text(y, d.loc[y, "u_rate"] + 0.3, f"{d.loc[y,'u_rate']:.1f}", ha="center", fontsize=8.8, color=INK)
    axes[1].text(y, d.loc[y, "ratio"] + 0.1, f"{d.loc[y,'ratio']:.2f}", ha="center", fontsize=8.8, color=INK)
axes[1].set_xlim(1962, 2026)
fig.suptitle(f"年ごとの変化はおおむね逆向き（相関 {main['hypotheses']['H1']['corr']:.2f}）。2019年から倍率だけが下がった", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：年平均。有効求人倍率はパートを含む実数。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.12, hspace=0.12)
save(fig, "fig1_u_and_ratio.png")

# ---- 図2：ベバリッジ曲線（失業率×欠員率） -------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.4))
pal = {1960: "#9fb8de", 1970: "#2a78d6", 1980: "#1baf7a", 1990: "#eda100", 2000: "#eb6834", 2010: "#7a5bd6", 2020: "#0b0b0b"}
for dec, q in d.groupby((d.index // 10) * 10):
    ax.plot(q.u_rate, q.v_rate, color=pal[dec], lw=1.6, marker="o", ms=4, label=f"{dec}年代")
for y in [1963, 1973, 1990, 2002, 2009, 2018, 2025]:
    ax.annotate(str(y), (d.loc[y, "u_rate"], d.loc[y, "v_rate"]), xytext=(4, 4), textcoords="offset points", fontsize=8.5, color=INK)
lim = np.linspace(0.5, 6, 50); ax.plot(lim, lim, color=INK2, lw=0.8, ls=":")
ax.text(1.55, 1.25, "点線：欠員率＝失業率", fontsize=8.5, color=INK2)
ax.set_xlim(0.5, 6); ax.set_ylim(1, 5.5)
ax.set_xlabel("完全失業率（%）"); ax.set_ylabel("欠員率（%）＝有効求人 ÷（就業者＋有効求人）")
ax.legend(loc="lower right", frameon=False, fontsize=8.6, ncol=2)
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("求人が同じでも、失業率は時代によって違う（曲線が右上に移った）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：年平均。点線より上は求人の方が多い（欠員率＞失業率）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.14)
save(fig, "fig2_beveridge.png")

# ---- 図3：10年ごとの均衡失業率の目安 ------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = np.arange(len(bev)); w = 0.38
ax.bar(x - w / 2 - 0.01, bev.u_mean, width=w, color=C[1], label="実際の失業率（10年の平均）")
ax.bar(x + w / 2 + 0.01, bev.eq_u, width=w, color=C[0], label="欠員率＝失業率となる失業率（目安）")
for i, r in bev.iterrows():
    ax.text(i - w / 2, r.u_mean + 0.08, f"{r.u_mean:.1f}", ha="center", fontsize=8.6, color=INK)
    ax.text(i + w / 2, r.eq_u + 0.08, f"{r.eq_u:.1f}", ha="center", fontsize=8.6, color=INK)
ax.set_xticks(x); ax.set_xticklabels([f"{int(dd)}年代" + ("\n（〜2025）" if dd == 2020 else "") for dd in bev.decade], fontsize=9)
ax.set_ylim(0, 5.5); ax.set_ylabel("%")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"目安の失業率は1960年代{bev.eq_u.iloc[0]:.1f}%→2000年代{bev.eq_u.max():.1f}%→2020年代{bev.eq_u.iloc[-1]:.1f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：10年ごとに ln(欠員率) を ln(失業率) に直線であてはめ、両者が等しくなる失業率を出した。あてはめ方に強く左右される目安。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_equilibrium_u.png")

# ---- 図4：倍率が動いた理由（求人と求職者） --------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
rows = sp.set_index("start").loc[[2009, 2019]]
cats = ["有効求人数", "有効求職者数", "完全失業者数"]
x = np.arange(len(cats)); w = 0.36
for k, (st, r) in enumerate(rows.iterrows()):
    vals = [r.openings_pct, r.applicants_pct, r.unemployed_pct]
    xs = x + (k - 0.5) * (w + 0.02)
    ax.bar(xs, vals, width=w, color=[C[0], C[1]][k], label=f"{int(st)}→{int(r.end)}年（倍率 {r.ratio_start:.2f}→{r.ratio_end:.2f}、失業率 {r.u_start:.1f}→{r.u_end:.1f}%）")
    for xx, v in zip(xs, vals):
        ax.text(xx, v + (3 if v >= 0 else -3), f"{v:+.0f}%", ha="center", va="bottom" if v >= 0 else "top", fontsize=9, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(cats)
ax.set_ylim(-70, 140); ax.set_ylabel("期間の増減（%）")
ax.legend(loc="upper right", frameon=False, fontsize=8.8)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("2019→2025年は、ハローワークの求人が15%減り、求職者が12%増えた", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：有効求人数・有効求職者数は月平均の年平均。完全失業者は労働力調査。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_ratio_split.png")
print("figures ok")
