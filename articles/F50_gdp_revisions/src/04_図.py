"""図を作る"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

d = pd.read_csv(RES / "revisions_real_qoq.csv")
rob = pd.read_csv(RES / "robustness.csv")
k = json.load(open(RES / "key_numbers.json", encoding="utf-8"))
C1, C2, C3, GR = "#2a6f97", "#d1495b", "#edae49", "#888888"

# 図1 1次速報と最新値
fig, ax = plt.subplots(figsize=(6.4, 5.6))
flip = (d.v1 * d.vL) < 0
ax.axhline(0, color=GR, lw=0.8); ax.axvline(0, color=GR, lw=0.8)
lim = [-9, 9]
ax.plot(lim, lim, color="black", lw=0.8, ls="--", label="45度線（直されなかった場合）")
ax.scatter(d.v1[~flip], d.vL[~flip], s=22, color=C1, alpha=0.75, label="符号は同じ")
ax.scatter(d.v1[flip], d.vL[flip], s=34, color=C2, label=f"符号が逆になった（{flip.sum()}四半期）")
for _, r in d[d.v1.abs() > 3].iterrows():
    ax.annotate(r.q, (r.v1, r.vL), fontsize=8, xytext=(4, -10), textcoords="offset points")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("1次速報の実質GDP成長率（前期比、%）"); ax.set_ylabel("最新の値（2026年4-6月期2次速報時点、%）")
ax.set_title(f"1次速報と最新の値（{k['targets'][0]}〜{k['targets'][1]}、{k['targets'][2]}四半期）", fontsize=11)
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "f50_scatter.png"); plt.close(fig)

# 図2 改定幅の分布
fig, axes = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
bins = np.arange(-2.25, 2.5, 0.1)
for ax, (c, lab, col) in zip(axes, [("r2", "2次速報で", C3), ("r1y", "1年後に", C1), ("rL", "最新までに", C2)]):
    x = d[c].dropna()
    ax.hist(x.clip(-2.2, 2.2), bins=bins, color=col, alpha=0.85)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(f"{lab}（n={len(x)}）\n平均{x.mean():+.2f}・平均絶対{x.abs().mean():.2f}pt", fontsize=10)
    ax.set_xlabel("改定幅（ポイント）")
axes[0].set_ylabel("四半期の数")
fig.suptitle("1次速報からの改定幅の分布（実質・前期比、±2.2で切り詰めて表示）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f50_hist.png"); plt.close(fig)

# 図3 改定幅の推移（後退期の網掛け・基準改定）
fig, ax = plt.subplots(figsize=(10, 3.8))
x = np.array([pd.Period(q, "Q").ordinal for q in d.q])
rec = pd.read_csv(RES / "revisions_real_qoq.csv")
from common import recession_quarters
rq = recession_quarters()
flag = [int(rq.get(pd.Period(q, "Q"), 0)) for q in d.q]
for i, f in enumerate(flag):
    if f:
        ax.axvspan(x[i] - 0.5, x[i] + 0.5, color="#dddddd", lw=0)
ax.bar(x, d.rL, color=np.where(d.rL >= 0, C1, C2), width=0.8, label="最新までの改定")
ax.plot(x, d.r2, color="black", marker=".", lw=0, ms=5, label="2次速報での改定")
ax.axhline(0, color="black", lw=0.6)
ty = list(range(2001, 2027, 3))
ax.set_xticks([pd.Period(f"{y}Q1", "Q").ordinal for y in ty]); ax.set_xticklabels([str(y) for y in ty])
ax.set_ylabel("改定幅（ポイント）"); ax.set_ylim(-2.6, 2.6)
ax.set_title("対象四半期ごとの改定幅（灰色は景気後退期）", fontsize=11)
ax.legend(fontsize=8, loc="lower left")
fig.tight_layout(); fig.savefig(FIG / "f50_timeline.png"); plt.close(fig)

# 図4 符号が逆になった四半期（1次→2次→1年後→最新）
f = d[flip].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 4.2))
xs = [0, 1, 2, 3]
for i, r in f.iterrows():
    y = [r.v1, r.v2, r.v1y, r.vL]
    col = C2 if r.v1 < 0 else C1
    ax.plot(xs, y, color=col, marker="o", lw=1.2, alpha=0.8)
for vl, g in f.groupby("vL"):
    ax.annotate("・".join(g.q), (3, vl), fontsize=7.5, xytext=(5, 0), textcoords="offset points", va="center")
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(xs); ax.set_xticklabels(["1次速報", "2次速報", "1年後", "最新"])
ax.set_xlim(-0.2, 4.0)
ax.set_ylabel("実質GDP成長率（前期比、%）")
ax.set_title(f"1次と最新で符号が逆になった{len(f)}四半期（赤：1次はマイナス、青：1次はプラス）", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f50_flips.png"); plt.close(fig)

# 図5 景気局面別と、2次での改定のあとの動き
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
d["後退期"] = flag
ax = axes[0]
data = [d.loc[d.後退期 == 0, "rL"].dropna(), d.loc[d.後退期 == 1, "rL"].dropna()]
ax.boxplot(data, widths=0.5)
ax.set_xticks([1, 2]); ax.set_xticklabels([f"拡張期（{len(data[0])}）", f"後退期（{len(data[1])}）"])
for i, g in enumerate(data, 1):
    ax.scatter(np.random.default_rng(42).normal(i, 0.05, len(g)), g, s=10, alpha=0.5, color=C1)
    ax.text(i, -2.85, f"平均{g.mean():+.2f}・平均絶対{g.abs().mean():.2f}", ha="center", fontsize=8.5)
ax.axhline(0, color=GR, lw=0.8); ax.set_ylim(-3.1, 2.8)
ax.set_ylabel("最新までの改定（ポイント）"); ax.set_title("景気局面別の改定幅", fontsize=10.5)
ax = axes[1]
dd = d.dropna(subset=["r2", "rL"])
later = dd.rL - dd.r2
ax.scatter(dd.r2, later, s=16, color=C1, alpha=0.7)
b = np.polyfit(dd.r2, later, 1)
xx = np.linspace(dd.r2.min(), dd.r2.max(), 10)
ax.plot(xx, np.polyval(b, xx), color=C2, lw=1.2, label=f"直線の傾き {b[0]:.2f}")
ax.axhline(0, color=GR, lw=0.8); ax.axvline(0, color=GR, lw=0.8)
ax.set_xlabel("2次速報での改定（ポイント）"); ax.set_ylabel("2次速報のあと、最新までの改定")
ax.set_title("2次で上に直された四半期は、そのあとも上に直されやすいか", fontsize=10.5)
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "f50_phase.png"); plt.close(fig)

# 図6 頑健性（平均絶対改定と平均）
r = rob[rob["改定"].isin(["rL", "r1y"])].copy()
r["label"] = [a if ("最新）" in a or "1年後）" in a) else a + "→" + {"rL": "最新", "r1y": "1年後"}[b] for a, b in zip(r["設定"], r["改定"])]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
y = np.arange(len(r))
ax.barh(y, r["平均絶対"], color=C1, alpha=0.8, label="平均絶対の改定")
ax.scatter(r["平均"], y, color=C2, zorder=3, label="平均（偏り）")
ax.axvline(0, color="black", lw=0.6)
ax.set_yticks(y); ax.set_yticklabels(r.label, fontsize=8.5); ax.invert_yaxis()
ax.set_xlabel("ポイント"); ax.legend(fontsize=8, loc="lower right")
ax.set_title("設定を変えた場合の改定の大きさと偏り", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f50_robust.png"); plt.close(fig)
print("ok")
