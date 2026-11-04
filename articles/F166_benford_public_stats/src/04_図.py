"""04 図：results/ の集計から図を5枚作る（市区町村の名前・順位は描かない）。"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

BASE = Path(__file__).resolve().parents[1]
RES, FIG = BASE / "results", BASE / "figures"
FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 100})
INK, MUTED, ACC, ACC2, BAND = "#222222", "#888888", "#2a6fb0", "#d0632a", "#e9eef5"
TH = {"d1": (0.006, 0.012, 0.015), "d2": (0.008, 0.010, 0.012), "d12": (0.0012, 0.0018, 0.0022)}
P1 = np.log10(1 + 1 / np.arange(1, 10))

main = pd.read_csv(RES / "main10_summary.csv")
fd = pd.read_csv(RES / "main10_first_digit.csv")
alls = pd.read_csv(RES / "all_series_2026.csv")
ss = pd.read_csv(RES / "sample_size.csv")
sc = pd.read_csv(RES / "scale_invariance.csv")
order = main.series.tolist()

# 1. 第1桁の分布（10系列）
fig, axes = plt.subplots(2, 5, figsize=(13, 5.6), sharey=True)
for ax, name in zip(axes.flat, order):
    d = fd[fd.series == name]
    ax.bar(d.digit, d.share, color=ACC, width=0.7)
    ax.plot(np.arange(1, 10), P1, color=ACC2, marker="o", ms=3, lw=1.5)
    r = main[main.series == name].iloc[0]
    ax.set_title(f"{name}\nMAD {r.mad_d1:.4f}（{r.judge_d1}）", fontsize=10.5)
    ax.set_xticks(range(1, 10))
    ax.tick_params(labelsize=9)
axes[0, 0].set_ylabel("割合")
axes[1, 0].set_ylabel("割合")
fig.suptitle("市区町村の10系列：先頭の数字の割合（棒）と、ベンフォードの法則（線）", fontsize=13)
fig.text(0.5, 0.005, "先頭の数字（第1桁）　出典：統計センター SSDSE-A-2026（1,733〜1,741市区町村）", ha="center", fontsize=9.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.95))
fig.savefig(FIG / "f166_first_digit.png", dpi=150)
plt.close(fig)

# 2. ずれの大きさと「標本の揺れだけ」の幅（3つの桁の位置）
fig, axes = plt.subplots(1, 3, figsize=(13.5, 5.2), sharey=True)
spec = [("d1", "mad_d1", "null_mad_median", "null_mad_p95", "第1桁"),
        ("d2", "mad_d2", None, "null_mad_d2_p95", "第2桁"),
        ("d12", "mad_d12", "null_mad_d12_median", "null_mad_d12_p95", "先頭2桁")]
y = np.arange(len(order))[::-1]
for ax, (k, col, med, p95, title) in zip(axes, spec):
    t = TH[k]
    xmax = max(main[col].max(), main[p95].max(), t[2]) * 1.25
    ax.axvspan(0, t[0], color="#e3f0e3", lw=0)
    ax.axvspan(t[0], t[1], color="#f4f4e0", lw=0)
    ax.axvspan(t[1], t[2], color="#f8eadc", lw=0)
    ax.axvspan(t[2], xmax, color="#f6dede", lw=0)
    for i, (_, r) in enumerate(main.iterrows()):
        ax.plot([0, r[p95]], [y[i]] * 2, color="#9bb6d3", lw=6, solid_capstyle="butt")
        ax.plot(r[col], y[i], "o", color=INK, ms=6)
    ax.set_xlim(0, xmax)
    ax.set_title(title, pad=8)
    ax.set_ylim(-1.2, len(order) - 0.5)
    ax.set_xlabel("MAD（ベンフォードからの平均のずれ）")
    for v, lab in zip((t[0] / 2, (t[0] + t[1]) / 2, (t[1] + t[2]) / 2, (t[2] + xmax) / 2),
                      ("よく合う", "おおむね", "ぎりぎり", "合わない")):
        ax.text(v, -0.95, lab, ha="center", fontsize=8.5, color=MUTED)
axes[0].set_yticks(y)
axes[0].set_yticklabels(order)
fig.suptitle("黒い点＝実際のずれ　青い帯＝本当にベンフォードに従う数を同じ件数だけ引いたときのずれ（95%まで）", fontsize=12)
fig.text(0.5, 0.005, "背景の色は Nigrini の目安。先頭2桁は、件数が約1,700だと揺れだけで「ぎりぎり」に入る", ha="center", fontsize=9.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 0.93))
fig.savefig(FIG / "f166_noise.png", dpi=150)
plt.close(fig)

# 3. SSDSE-A の全119項目：桁の広がりとずれ
cnt = alls[~alls.is_ratio]
small = cnt.share_below_10 >= 0.1
fig, ax = plt.subplots(figsize=(9.5, 6))
for lo, hi, c in [(0, 0.006, "#e3f0e3"), (0.006, 0.012, "#f4f4e0"), (0.012, 0.015, "#f8eadc"), (0.015, 0.08, "#f6dede")]:
    ax.axhspan(lo, hi, color=c, lw=0)
ax.scatter(cnt.log10_sd[~small], cnt.mad_d1[~small], s=28, color=ACC, label="10未満の値が1割未満の項目", zorder=3)
ax.scatter(cnt.log10_sd[small], cnt.mad_d1[small], s=36, facecolor="white", edgecolor=ACC2, lw=1.5,
           label="10未満の値が1割以上の項目（学校数・病院数など）", zorder=3)
m = cnt[cnt.main]
ax.scatter(m.log10_sd, m.mad_d1, s=90, facecolor="none", edgecolor=INK, lw=1.2, label="この記事の主な10系列", zorder=4)
ax.set_ylim(0, 0.07)
ax.set_xlabel("桁の広がり（log10 の標準偏差）　右ほど、何桁にもまたがる")
ax.set_ylabel("第1桁の MAD")
ax.set_title("SSDSE-A の数を数えた119項目：桁の広がりが狭い・小さい数が多い項目ほど、ずれが大きい")
for v, lab in [(0.003, "よく合う"), (0.009, "おおむね"), (0.0135, "ぎりぎり"), (0.04, "合わない")]:
    ax.text(cnt.log10_sd.max() * 1.02, v, lab, fontsize=9, color=MUTED, va="center")
ax.legend(loc="upper right", fontsize=9, frameon=False)
fig.text(0.5, 0.005, "出典：統計センター SSDSE-A-2026（正の値が300件以上の項目。比率の2項目は除く）", ha="center", fontsize=9, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "f166_all_series.png", dpi=150)
plt.close(fig)

# 4. 件数と検定
fig, ax = plt.subplots(figsize=(9.5, 5.6))
ends = []
for name in order:
    d = ss[ss.series == name]
    hi = name in ("出生数", "総面積")
    ax.plot(d.n, d.reject_share, marker="o", ms=3.5, lw=1.4, color=ACC if not hi else "#7fa7cf", alpha=0.85)
    ends.append([d.reject_share.iloc[-1], name])
ends.sort()
pos = []
for v, name in ends:
    v2 = max(v, pos[-1] + 0.022) if pos else v
    pos.append(v2)
    ax.text(1040, v2, name, fontsize=8.5, va="center", color=MUTED)
d = ss[ss.series == "（本当のベンフォード）"]
ax.plot(d.n, d.reject_share, color=ACC2, lw=2.2, marker="s", ms=4)
ax.text(1760, 0.065, "本当のベンフォード", color=ACC2, fontsize=9)
ax.axhline(0.05, color=MUTED, lw=0.8, ls="--")
ax.set_xscale("log")
ax.set_xticks([50, 100, 200, 500, 1000, 1741])
ax.set_xticklabels(["50", "100", "200", "500", "1000", "1741"])
ax.set_xlabel("抜き出す市区町村の数（各1,000回）")
ax.set_ylabel("カイ二乗検定で「合わない」（p<0.05）になる割合")
ax.set_title("同じ系列でも、件数を増やすほど検定は「合わない」と言いやすくなる")
fig.tight_layout()
fig.savefig(FIG / "f166_sample_size.png", dpi=150)
plt.close(fig)

# 5. 単位を変えるとずれは動く
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for lo, hi, c in [(0, 0.006, "#e3f0e3"), (0.006, 0.012, "#f4f4e0"), (0.012, 0.015, "#f8eadc")]:
    ax.axvspan(lo, hi, color=c, lw=0)
y = np.arange(len(sc))[::-1]
for i, (_, r) in enumerate(sc.iterrows()):
    ax.plot([r.scaled_min, r.scaled_max], [y[i]] * 2, color="#9bb6d3", lw=6, solid_capstyle="butt")
    ax.plot(r.mad_d1, y[i], "o", color=INK, ms=6)
ax.set_yticks(y)
ax.set_yticklabels(sc.series)
ax.set_xlim(0, 0.015)
ax.set_ylim(-1.2, len(sc) - 0.5)
ax.set_xlabel("第1桁の MAD")
ax.set_title("黒い点＝元の単位　帯＝1〜10倍に換算した200通りのずれの範囲")
for v, lab in [(0.003, "よく合う"), (0.009, "おおむね合う"), (0.0135, "ぎりぎり")]:
    ax.text(v, -0.95, lab, ha="center", fontsize=9, color=MUTED)
fig.text(0.5, 0.005, "円→ドルのように単位を換えるだけで、判定が入れ替わる系列がある", ha="center", fontsize=9.5, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "f166_scale.png", dpi=150)
plt.close(fig)
print("figures:", sorted(p.name for p in FIG.glob("*.png")))
