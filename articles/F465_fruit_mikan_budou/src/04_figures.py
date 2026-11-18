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
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
CM, CB = "#eb6834", "#7b4fc9"  # みかん、ぶどう
INK2, GRID = "#52514e", "#e4e3df"
META = {"Software": None}
S1 = "出典：農林水産省「作物統計（果樹生産出荷統計）」をもとに作成者が加工して作成"
S2 = "出典：農林水産省「生産農業所得統計」「作物統計（果樹生産出荷統計）」をもとに作成者が加工して作成"
N = pd.read_csv(R / "national_series.csv")
M = json.load(open(R / "main.json", encoding="utf-8"))
P = pd.read_csv(R / "pref_area_2004_2024.csv")


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, src, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + src, fontsize=7.6, color=INK2)


def ser(it):
    return N[N.item == it].set_index("year")


# 図1：面積と収穫量（1973〜2024年）
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.6))
for ax, col, scale, yl, ttl in [(axes[0], "area_ha", 1e3, "結果樹面積（千ha）", "結果樹面積"), (axes[1], "harvest_t", 1e4, "収穫量（万t）", "収穫量")]:
    for it, c in [("みかん", CM), ("ぶどう", CB)]:
        g = ser(it)[col] / scale
        ax.plot(g.index, g.values, color=c, lw=2, label=it)
        ax.text(2025, g[2024], f"{g[2024]:.1f}" if scale == 1e3 else f"{g[2024]:.0f}", color=c, fontsize=9, va="center")
    ax.axvline(2004, color=INK2, lw=0.8, ls=":")
    ax.set_title(ttl, fontsize=11, loc="left"); ax.set_ylabel(yl)
    ax.set_ylim(0, None); ax.set_xlim(1972, 2030); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
axes[1].set_yscale("log"); axes[1].set_ylim(10, 400); axes[1].set_yticks([10, 20, 50, 100, 200, 400], ["10", "20", "50", "100", "200", "400"])
axes[0].set_yscale("log"); axes[0].set_ylim(10, 200); axes[0].set_yticks([10, 20, 50, 100, 200], ["10", "20", "50", "100", "200"])
axes[0].legend(frameon=False, loc="upper right")
fig.suptitle("図1　みかんもぶどうも、面積と収穫量は減っている（全国、1973〜2024年）", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.96, top=0.84, bottom=0.2, wspace=0.3)
foot(fig, S1, "縦軸は対数目盛（同じ幅が同じ割合の変化）。点線は2004年。結果樹面積は実がなる木の面積。")
save(fig, "fig1_area_harvest.png")

# 図2：産出額と1kg あたり産出額（2003〜2024年）
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.6))
for it, c in [("みかん", CM), ("ぶどう", CB)]:
    g = ser(it).loc[2003:2024]
    axes[0].plot(g.index, g.value_oku, color=c, lw=2, marker="o", ms=3, label=it)
    axes[0].text(2024.4, g.value_oku[2024], f"{g.value_oku[2024]:,.0f}", color=c, fontsize=9, va="center")
    axes[1].plot(g.index, g.unit_value_yen_kg, color=c, lw=2, marker="o", ms=3, label=it)
    axes[1].text(2024.4, g.unit_value_yen_kg[2024], f"{g.unit_value_yen_kg[2024]:,.0f}", color=c, fontsize=9, va="center")
axes[0].set_title("産出額（億円）", fontsize=11, loc="left"); axes[0].set_ylim(0, 2400)
axes[1].set_title("1kg あたり産出額（円）＝産出額÷収穫量", fontsize=11, loc="left"); axes[1].set_ylim(0, 1450)
for ax in axes:
    ax.set_xlim(2002, 2027.5); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
axes[0].legend(frameon=False, loc="lower right")
axes[0].annotate("2020年にぶどうが\nみかんを上回った", xy=(2020, 1732), xytext=(2008.5, 2050), fontsize=8.8, color=INK2,
                 arrowprops=dict(arrowstyle="->", color=INK2, lw=0.8))
fig.suptitle("図2　産出額は、ぶどうが2004→2024年に2.1倍。1kg あたりの値はどちらも上がった", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.07, right=0.95, top=0.84, bottom=0.2, wspace=0.25)
foot(fig, S2, "産出額は名目（物価で割っていない）。2024年のみかんは収穫量が特に少ない年。")
save(fig, "fig2_value.png")

# 図3：産出額の変化の分け方（7品目、2004→2024年）
items = ["みかん", "ぶどう", "りんご", "日本なし", "もも", "かき", "おうとう"]
d = M["decomp_2004_2024"]
fig, ax = plt.subplots(figsize=(9.2, 4.9))
y = np.arange(len(items))[::-1]
la = np.array([d[i]["log_area"] for i in items]); ly = np.array([d[i]["log_yield"] for i in items]); lp = np.array([d[i]["log_unit_value"] for i in items])
for vals, c, nm in [(la, "#2a78d6", "面積"), (ly, "#1baf7a", "単収（10a あたり収穫量）"), (lp, "#eda100", "1kg あたり産出額")]:
    pos = np.where(vals > 0, vals, 0); neg = np.where(vals < 0, vals, 0)
    if nm == "面積":
        bp, bn = np.zeros(len(items)), np.zeros(len(items))
    ax.barh(y, pos, left=bp, color=c, height=0.55, label=nm); ax.barh(y, neg, left=bn, color=c, height=0.55)
    bp = bp + pos; bn = bn + neg
tot = la + ly + lp
ax.scatter(tot, y, marker="D", color="#2b2a28", zorder=4, s=28, label="産出額の変化（合計）")
for yy, t, it in zip(y, tot, items):
    ax.text(max(bp[list(items).index(it)], 0) + 0.03, yy, f"産出額 {d[it]['value_change_pct']:+.0f}%", va="center", fontsize=8.8, color=INK2)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(y, items); ax.set_xlim(-0.9, 1.45)
ax.set_xlabel("変化の大きさ（対数の差。0.1 は約10%）")
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower right", fontsize=8.8)
ax.set_title("図3　2004→2024年の産出額の変化を、面積・単収・1kg あたり産出額に分ける", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.11, right=0.98, top=0.9, bottom=0.2)
foot(fig, S2, "並びは品目の固定の順（値の順ではない）。3つの棒を足すと産出額の変化（◆）になる。名目。")
save(fig, "fig3_decomp.png")

# 図4：主な産地の結果樹面積（2004年と2024年、都道府県コード順）
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.8), gridspec_kw={"width_ratios": [6, 8]})
for ax, it, c in [(axes[0], "ぶどう", CB), (axes[1], "みかん", CM)]:
    g = P[(P.item == it) & (P.share_2004_pct >= 3)].sort_values("pref_code")
    x = np.arange(len(g))
    ax.bar(x - 0.2, g.area_2004 / 1e3, 0.4, color="#c9c8c4", label="2004年")
    ax.bar(x + 0.2, g.area_2024 / 1e3, 0.4, color=c, label="2024年")
    for xi, (a, ch) in enumerate(zip(g.area_2024 / 1e3, g.change_pct)):
        ax.text(xi + 0.2, a + 0.1, f"{ch:+.0f}%", ha="center", fontsize=8.2, color=INK2)
    ax.set_xticks(x, g.pref, fontsize=9.5)
    ax.set_title(f"{it}（2004年に全国の3%以上の{'道県' if it == 'ぶどう' else '県'}）", fontsize=10.5, loc="left")
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=8.8, loc="upper right")
axes[0].set_ylabel("結果樹面積（千ha）"); axes[0].set_ylim(0, 5); axes[1].set_ylim(0, 9.5)
fig.suptitle("図4　ぶどうは長野・岡山で面積が増えた。みかんは主な県すべてで減った", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.07, right=0.98, top=0.84, bottom=0.18, wspace=0.18)
foot(fig, S1, "並びは都道府県コード順（北から南）で、値の順ではない。数字は2004→2024年の増減率。")
save(fig, "fig4_pref.png")
