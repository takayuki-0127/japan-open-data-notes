"""04 図：順位の安定性の図を作る（県名は出さず、順位と分布だけを示す）。"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data/pref_scores.csv")
YEARS = sorted(df.year.unique())
SERIES = [("小", "国語"), ("小", "算数・数学"), ("中", "国語"), ("中", "算数・数学")]
C_UP, C_MID, C_LOW = "#2a6fb0", "#9a9a9a", "#d17a22"


def L(lv, sb):
    return f"{lv}・" + ("国語" if sb == "国語" else ("算数" if lv == "小" else "数学"))


def wide(lv, sb, col="rate"):
    x = df[(df.level == lv) & (df.subject == sb)]
    return x.pivot(index="pref_code", columns="year", values=col)


# 1 順位の動き（小・国語と中・数学）
fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), sharey=True)
for ax, (lv, sb) in zip(axes, [("小", "国語"), ("中", "算数・数学")]):
    r = wide(lv, sb).rank(ascending=False)
    m = r.mean(1)
    for p in r.index:
        col = C_UP if m[p] <= 10 else (C_LOW if m[p] > 37 else C_MID)
        ax.plot(range(len(YEARS)), r.loc[p], color=col, lw=1.4 if col != C_MID else 0.8, alpha=0.9 if col != C_MID else 0.55)
    ax.set_xticks(range(len(YEARS)), [f"{y}" for y in YEARS], fontsize=9)
    ax.set_title(f"{lv}学校・{sb.replace('算数・数学', '数学' if lv == '中' else '算数')}", fontsize=12)
    ax.set_yticks([1, 10, 20, 30, 40, 47])
axes[0].invert_yaxis()
axes[0].set_ylabel("順位（正答率を小数まで計算）")
fig.suptitle("47都道府県の順位の動き（2020年度は調査なし）", fontsize=13)
fig.text(0.5, 0.005, "青：7回の平均で上位10付近　灰：中位　橙：下位10付近（県名は出していない）", ha="center", fontsize=9, color="#444")
fig.tight_layout(rect=[0, 0.03, 1, 0.97])
fig.savefig(FIG / "f59_bump.png", dpi=160)
plt.close(fig)

# 2 年どうしの順位の相関
cor = pd.read_csv(RES / "rank_correlations.csv")
fig, axes = plt.subplots(1, 4, figsize=(14, 3.9))
for ax, (lv, sb) in zip(axes, SERIES):
    c = cor[(cor.level == lv) & (cor.subject == sb)]
    M = np.full((len(YEARS), len(YEARS)), np.nan)
    for _, r in c.iterrows():
        i, j = YEARS.index(r.y1), YEARS.index(r.y2)
        M[j, i] = r.spearman
    for i in range(len(YEARS)):
        M[i, i] = 1
    im = ax.imshow(M, vmin=0.3, vmax=1, cmap="Blues")
    for i in range(len(YEARS)):
        for j in range(i):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color="white" if M[i, j] > 0.75 else "black")
    ax.set_xticks(range(len(YEARS)), [str(y)[2:] for y in YEARS], fontsize=8)
    ax.set_yticks(range(len(YEARS)), [str(y)[2:] for y in YEARS], fontsize=8)
    ax.set_title(L(lv, sb), fontsize=11)
    for s in ax.spines.values():
        s.set_visible(False)
fig.suptitle("2つの年度の順位の相関（スピアマン、年度は下2桁）", fontsize=13)
fig.colorbar(im, ax=axes, shrink=0.8)
fig.savefig(FIG / "f59_corr.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# 3 1回分の正答率と標本誤差、公表値（整数）の同点
lv, sb, yr = "中", "算数・数学", 2026
x = df[(df.level == lv) & (df.subject == sb) & (df.year == yr)].sort_values("rate", ascending=False).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(11, 5))
pal = plt.cm.tab10(np.arange(10))
vals = sorted(x.rate_pub.unique(), reverse=True)
for i, r in x.iterrows():
    col = pal[vals.index(r.rate_pub) % 10]
    ax.errorbar(i + 1, r.rate, yerr=1.645 * r.se_rate, fmt="o", color=col, ms=4.5, capsize=2, lw=1)
nat = x.nat_rate.iloc[0]
ax.axhline(nat, color="#555", lw=1, ls="--")
ax.text(47.5, nat + 0.15, f"全国（公立）{nat:.1f}%", ha="right", fontsize=9, color="#555")
for v in vals:
    idx = x.index[x.rate_pub == v] + 1
    if len(idx) > 1:
        ax.annotate(f"公表値 {int(v)}%：{len(idx)}県", (float(np.mean(idx)), x.rate[idx - 1].min() - 0.95), ha="center", fontsize=8,
                    color=pal[vals.index(v) % 10])
ax.set_xlabel("順位（正答率を小数まで計算）")
ax.set_ylabel("平均正答率（%）")
ax.set_xticks([1, 10, 20, 30, 40, 47])
ax.set_title(f"{yr}年度・中学校・数学：47都道府県の平均正答率と標本誤差の90%幅\n色は公表値（整数）のまとまり。公表値では{len(vals)}通りの値しかない", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "f59_gaps.png", dpi=160)
plt.close(fig)

# 4 平均順位と順位の幅
rr = pd.read_csv(RES / "rank_range_by_pref.csv")
bs = pd.read_csv(RES / "rank_interval_sampling.csv")
fig, ax = plt.subplots(figsize=(9, 5.2))
mk = {("小", "国語"): "o", ("小", "算数・数学"): "s", ("中", "国語"): "^", ("中", "算数・数学"): "D"}
for (lv, sb), g in rr.groupby(["level", "subject"]):
    ax.scatter(g.mean_rank, g.range, s=18, alpha=0.6, marker=mk[(lv, sb)], label=L(lv, sb))
bins = np.arange(0, 48, 4)
mids = (bins[:-1] + bins[1:]) / 2
med = [rr[(rr.mean_rank > a) & (rr.mean_rank <= b)].range.median() for a, b in zip(bins[:-1], bins[1:])]
ax.plot(mids, med, color="black", lw=2, label="中央値（平均順位4位ごと）")
bsw = bs.groupby(pd.cut(bs["rank"], bins), observed=False).width.median().values
ax.plot(mids, bsw, color="#c0392b", lw=2, ls="--", label="標本誤差だけの順位の90%幅（中央値）")
ax.set_xlabel("7回の平均順位")
ax.set_ylabel("7回の順位の幅（最低位 − 最高位）")
ax.set_title("中位の県ほど、順位は大きく動く", fontsize=13)
ax.legend(fontsize=8.5, frameon=False, ncol=2)
fig.tight_layout()
fig.savefig(FIG / "f59_range.png", dpi=160)
plt.close(fig)

# 5 全国との差の分散の内訳
dec = pd.read_csv(RES / "variance_decomposition.csv")
fig, ax = plt.subplots(figsize=(9, 4.4))
lab = [L(a, b) for a, b in zip(dec.level, dec.subject)]
tot = dec.persistent + dec.year_to_year + dec.sampling
p1, p2, p3 = dec.persistent / tot, dec.year_to_year / tot, dec.sampling / tot
ax.barh(lab, p1, color=C_UP, label="ずっと続く差（7回の平均の違い）")
ax.barh(lab, p2, left=p1, color="#f0b400", label="年ごとの揺れ（問題・学年の違いなど）")
ax.barh(lab, p3, left=p1 + p2, color="#c0392b", label="標本誤差（受けた子どもの偶然）")
for i, (a, b, c) in enumerate(zip(p1, p2, p3)):
    ax.text(a / 2, i, f"{a:.0%}", va="center", ha="center", color="white", fontsize=10)
    ax.text(a + b / 2, i, f"{b:.0%}", va="center", ha="center", fontsize=10)
ax.set_xlim(0, 1)
ax.invert_yaxis()
ax.set_xlabel("全国との差の分散に占める割合")
ax.set_title("都道府県の差の7〜8割は毎年続くが、残りは年ごとに入れ替わる", fontsize=12)
ax.legend(fontsize=8.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=2)
fig.tight_layout()
fig.savefig(FIG / "f59_variance.png", dpi=160, bbox_inches="tight")
plt.close(fig)

# 6 頑健性
rob = pd.read_csv(RES / "robustness.csv", index_col=0).iloc[:, 0]
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(rob.index, rob.values, color=[C_UP] + [C_MID] * (len(rob) - 1))
for i, v in enumerate(rob.values):
    ax.text(v + 0.005, i, f"{v:.2f}", va="center", fontsize=9)
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.set_xlabel("連続する2回の順位の相関（平均）")
ax.set_title("設定を変えても、スピアマンは0.78〜0.85（τは尺度が違う）", fontsize=12)
fig.tight_layout()
fig.savefig(FIG / "f59_robust.png", dpi=160)
plt.close(fig)
print("ok")
