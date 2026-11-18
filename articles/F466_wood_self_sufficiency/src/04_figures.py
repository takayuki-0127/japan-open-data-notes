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
for cand in ["Noto Sans CJK JP", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
INK2, GRID = "#52514e", "#e4e3df"
COL = {"製材用": "#2f6db5", "合板用": "#e08a2e", "パルプ・チップ用": "#8aa63a", "その他用": "#9b6fb8", "しいたけ原木": "#a3a29c", "燃料材": "#c94b4b"}
META = {"Software": None}
SRC = "出典：林野庁「木材需給表」（e-Stat）をもとに作成者が加工して作成"
N = pd.read_csv(R / "national_series.csv").set_index("year")
M = json.load(open(R / "main.json", encoding="utf-8"))
Q = json.load(open(R / "requestion.json", encoding="utf-8"))
a, b = M["y_min"], M["end"]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：自給率の推移
fig, ax = plt.subplots(figsize=(9.0, 4.8))
ax.plot(N.index, N.ss_total_pub, color="#1f4e79", lw=2.2, label="総数（燃料材を含む）")
ax.plot(N.index, N.ss_youzai_pub, color="#2f9e8f", lw=1.8, ls="--", label="用材（製材・合板・パルプ・チップ・その他）")
for y in [a, b]:
    ax.scatter([y], [N.loc[y, "ss_total_pub"]], color="#1f4e79", zorder=3)
    ax.annotate(f"{y}年 {N.loc[y, 'ss_total_pub']:.1f}%", (y, N.loc[y, "ss_total_pub"]), xytext=(-10, -18 if y == a else 8),
                textcoords="offset points", ha="center" if y == a else "right", fontsize=9, color="#1f4e79")
ax.annotate(f"{b}年 {N.loc[b, 'ss_youzai_pub']:.1f}%", (b, N.loc[b, "ss_youzai_pub"]), xytext=(0, -24), textcoords="offset points", ha="right", fontsize=9, color="#2f9e8f")
ax.axvline(2014, color=INK2, lw=0.8, ls=":")
ax.text(2013.5, 88, "2014年から燃料用チップ\n（発電など）を新たに計上", ha="right", fontsize=8.5, color=INK2)
ax.set_ylim(0, 100); ax.set_xlim(1954, 2026); ax.set_ylabel("自給率（%）")
ax.set_title("木材自給率は2002年の18.8%から2024年の42.5%へ上がった", loc="left", fontsize=12)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.80), fontsize=9)
fig.subplots_adjust(bottom=0.14, top=0.9); foot(fig, "自給率＝国内生産量÷総需要量。体積は丸太に換算した量")
save(fig, "fig1_self_sufficiency.png")

# 図2：国内生産と輸入の量（用途別の積み上げ）
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.8), sharey=True)
yrs = N.loc[1995:].index
for ax, side, ttl, uses in [(axes[0], "dom", "国内生産", ["製材用", "合板用", "パルプ・チップ用", "その他用", "しいたけ原木", "燃料材"]),
                            (axes[1], "imp", "輸入", ["製材用", "合板用", "パルプ・チップ用", "その他用", "燃料材"])]:
    key = {"製材用": "seizai", "合板用": "gouhan", "パルプ・チップ用": "pulp", "その他用": "sonota", "しいたけ原木": "shiitake", "燃料材": "nenryo"}
    vals = [N.loc[yrs, f"{side}_{key[u]}"].to_numpy() / 1e3 for u in uses]
    ax.stackplot(yrs, vals, colors=[COL[u] for u in uses], labels=uses, alpha=0.9)
    tot = N.loc[yrs, f"{side}_total"] / 1e3
    for y in [a, b]:
        ax.text(y, tot[y] + 1.5, f"{tot[y]:.1f}", ha="center", fontsize=9)
    ax.set_title(f"{ttl}（{a}年 {tot[a]:.1f} → {b}年 {tot[b]:.1f} 百万m3）", loc="left", fontsize=11)
    ax.axvline(2014, color=INK2, lw=0.8, ls=":")
    ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.set_xlim(1995, 2024)
axes[0].set_ylabel("百万m3（丸太換算）")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h[::-1], l[::-1], frameon=False, loc="upper right", bbox_to_anchor=(0.995, 0.90), fontsize=8.5)
fig.suptitle("国内生産は燃料材と合板用で増え、輸入は用材で減った", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(bottom=0.15, top=0.84, right=0.86, wspace=0.08)
foot(fig, "点線は2014年（燃料用チップを新たに計上）。2020年から輸入の集成材などを「その他用」から「製材用」へ移した")
save(fig, "fig2_volumes.png")

# 図3：2002→2024年の分解
dec = pd.read_csv(R / f"decomp_{a}_{b}.csv")
dec["lab"] = dec.side + "・" + dec.use
dec = dec.iloc[::-1].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9.0, 5.2))
colors = [COL[u] for u in dec.use]
ax.barh(dec.lab, dec.contrib_pt, color=colors, edgecolor=["none" if s == "国内生産" else "#333" for s in dec.side], hatch=None)
for i, (v, s) in enumerate(zip(dec.contrib_pt, dec.side)):
    ax.text(v + (0.15 if v >= 0 else -0.15), i, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("自給率の変化への寄与（ポイント）")
ax.set_xlim(-5, 12)
ax.set_title(f"{a}→{b}年の上昇 {M['change_pt']:.1f}ポイントの内訳：国内生産 {M['dom_contrib_pt']:+.1f}、輸入 {M['imp_contrib_pt']:+.1f}", loc="left", fontsize=11.5)
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
fig.subplots_adjust(left=0.24, bottom=0.17, top=0.9)
foot(fig, "輸入の寄与は、輸入が減ると正（自給率を上げる向き）。すべての量を同時にまっすぐ動かして積分した分け方（足すと変化に一致）")
save(fig, "fig3_decomposition.png")

# 図4：期間ごと（毎年の分解の足し上げ）
P = pd.DataFrame(Q["periods"])
groups = [("国内・用材", "#2f6db5"), ("国内・燃料材", "#c94b4b"), ("国内・しいたけ原木", "#a3a29c"), ("輸入・用材", "#8fb3e0"), ("輸入・燃料材", "#efa3a3")]
fig, ax = plt.subplots(figsize=(9.0, 5.0))
x = np.arange(len(P))
pos = np.zeros(len(P)); neg = np.zeros(len(P))
for g, c in groups:
    v = P[g].to_numpy()
    base = np.where(v >= 0, pos, neg)
    ax.bar(x, v, bottom=base, color=c, label=g.replace("輸入・", "輸入の減少・") if g.startswith("輸入") else g.replace("国内・", "国内生産の増加・"), width=0.62)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
for i, v in enumerate(P.change):
    ax.text(i, pos[i] + 0.2, f"計 {v:+.1f}", ha="center", fontsize=9.5)
ax.set_xticks(x, [f"{p}\n（{s0:.1f}→{s1:.1f}%）" for p, s0, s1 in zip(P.period, P.ss_from, P.ss_to)], fontsize=9)
ax.axhline(0, color=INK2, lw=0.8); ax.set_ylabel("自給率の変化への寄与（ポイント）")
ax.set_title("2019年以降の上昇は、おもに用材の輸入の減少と燃料材の国内生産の増加", loc="left", fontsize=11.5)
ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2); ax.set_ylim(-5, 11)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.subplots_adjust(bottom=0.2, top=0.9)
foot(fig, "毎年の分解を期間ごとに足した。「輸入の減少・燃料材」が負なのは、燃料材の輸入が増えて自給率を下げる向きに働いたため")
save(fig, "fig4_periods.png")
