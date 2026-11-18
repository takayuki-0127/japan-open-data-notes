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
CF, CA = "#2f6db5", "#e08a2e"  # 漁業、養殖
META = {"Software": None}
SRC = "出典：農林水産省「漁業・養殖業生産統計」「漁業産出額」（e-Stat）をもとに作成者が加工して作成"
N = pd.read_csv(R / "national_series.csv").set_index("year")
M = json.load(open(R / "main.json", encoding="utf-8"))
END, YP = M["end"], M["y_peak_total_vol"]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：養殖の割合（量・金額）
fig, ax = plt.subplots(figsize=(9.0, 4.8))
v = N.vol_share_aqua.dropna(); m = N.val_share_aqua.dropna()
ax.plot(m.index, m.values, color="#b5541c", lw=2.2, label="産出額（金額）に占める養殖の割合")
ax.plot(v.index, v.values, color=CA, lw=2.2, ls="--", label="生産量（重さ）に占める養殖の割合")
for s_, c, dy in [(m, "#b5541c", 8), (v, CA, -16)]:
    for y in [YP, END]:
        ax.scatter([y], [s_[y]], color=c, zorder=3, s=18)
        ax.annotate(f"{y}年 {s_[y]:.1f}%", (y, s_[y]), xytext=(0, dy), textcoords="offset points", ha="center" if y == YP else "right", fontsize=9, color=c)
ax.set_ylim(0, 50); ax.set_xlim(1958, 2026); ax.set_ylabel("養殖（海面＋内水面）の割合（%）")
ax.set_title("養殖の割合は、量では2割強、金額では4割強になった", loc="left", fontsize=12)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, loc="upper left", fontsize=9)
fig.subplots_adjust(bottom=0.14, top=0.9); foot(fig, "生産量の部門別の表は1979年から。産出額は名目")
save(fig, "fig1_share.png")

# 図2：漁業と養殖の量と金額
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.7))
ax = axes[0]
ax.plot(N.index, N.vol_fish_t / 1e4, color=CF, lw=2, label="漁業（海面＋内水面）")
ax.plot(N.index, N.vol_aqua_t / 1e4, color=CA, lw=2, label="養殖（海面＋内水面）")
for col, c in [("vol_fish_t", CF), ("vol_aqua_t", CA)]:
    ax.text(END + 0.8, N.loc[END, col] / 1e4, f"{N.loc[END, col] / 1e4:.0f}", color=c, fontsize=9, va="center")
ax.set_title("生産量（万t）", loc="left", fontsize=11); ax.set_xlim(1958, 2030); ax.set_ylim(0, None)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=9)
ax = axes[1]
ax.plot(N.index, N.val_fish_oku / 1e4, color=CF, lw=2, label="漁業")
ax.plot(N.index, N.val_aqua_oku / 1e4, color=CA, lw=2, label="養殖")
for col, c in [("val_fish_oku", CF), ("val_aqua_oku", CA)]:
    ax.text(END + 0.8, N.loc[END, col] / 1e4, f"{N.loc[END, col] / 1e4:.2f}", color=c, fontsize=9, va="center")
ax.set_title("産出額（兆円、名目）", loc="left", fontsize=11); ax.set_xlim(1958, 2030); ax.set_ylim(0, None)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.suptitle("漁業は量も金額も大きく減った。養殖は量が減り、金額は2010年代から増えた", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(bottom=0.15, top=0.83, wspace=0.18); foot(fig, "生産量の部門別の表は1979年から")
save(fig, "fig2_levels.png")

# 図3：割合の変化の内訳（1984→2024）
dec = pd.read_csv(R / f"decomp_{YP}_{END}.csv")
fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.8), gridspec_kw={"width_ratios": [6, 4]})
for ax, meas, ttl in [(axes[0], "量", "生産量の割合 {a:.1f}→{b:.1f}%（{c:+.1f}）"), (axes[1], "金額", "産出額の割合 {a:.1f}→{b:.1f}%（{c:+.1f}）")]:
    d = dec[dec.measure == meas].iloc[::-1]
    key = "vol_decomp" if meas == "量" else "val_decomp"
    ax.barh(d.part, d.contrib_pt, color=[CA if s == "養殖" else CF for s in d.side])
    for i, val in enumerate(d.contrib_pt):
        ax.text(val + (0.3 if val >= 0 else -0.3), i, f"{val:+.1f}", va="center", ha="left" if val >= 0 else "right", fontsize=9)
    ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-6, 23)
    r = M[key]; ax.set_title(ttl.format(a=r["s_from"], b=r["s_to"], c=r["change"]), loc="left", fontsize=10.5)
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True); ax.set_xlabel("寄与（ポイント）")
fig.suptitle(f"{YP}→{END}年に養殖の割合が上がったのは、おもに漁業が減ったため", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.13, bottom=0.2, top=0.84, wspace=0.55)
foot(fig, "漁業の寄与は、漁業が減ると正（割合を上げる向き）。養殖の寄与は、養殖が減ると負。すべての量を同時にまっすぐ動かして積分した分け方（足すと変化に一致）")
save(fig, "fig3_decomposition.png")

# 図4：海面養殖の品目群：2004→2024年の金額・量・1kg あたり
Q = pd.read_csv(R / "requestion_value_split.csv")
q = Q[(Q["from"] == 2004) & (Q["to"] == END)].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9.0, 4.9))
x = np.arange(len(q)); w = 0.26
for j, (col, lab, c) in enumerate([("vol_ratio", "生産量", "#8fb3e0"), ("val_ratio", "産出額（名目）", CA), ("price_ratio", "1kg あたり産出額", "#b5541c")]):
    ax.bar(x + (j - 1) * w, q[col], width=w, color=c, label=lab)
    for i, val in enumerate(q[col]):
        ax.text(i + (j - 1) * w, val + 0.03, f"{val:.2f}", ha="center", fontsize=8.5)
ax.axhline(1, color=INK2, lw=0.8)
ax.set_xticks(x, q.group); ax.set_ylabel(f"{END}年 ÷ 2004年（倍）"); ax.set_ylim(0, 2.6)
ax.set_title("海面養殖の産出額が増えたのは、量ではなく1kg あたりの額が上がったため", loc="left", fontsize=11.5)
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.subplots_adjust(bottom=0.16, top=0.9)
foot(fig, "1kg あたり産出額＝産出額÷生産量（名目）。かきは殻付き、のりは生重量の重さ。真珠は量の表し方が違うので除いた")
save(fig, "fig4_value_split.png")
