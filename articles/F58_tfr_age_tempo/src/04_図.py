"""図を5枚作る"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, AGES

FIG.mkdir(exist_ok=True)
asfr = pd.read_csv(DATA / "asfr_single_year.csv").set_index("year")
A = asfr[[str(a) for a in AGES]]
yr = pd.read_csv(RES / "tfr_mab_bf.csv", index_col=0)
dec = pd.read_csv(RES / "decomp_periods.csv")
order = pd.read_csv(DATA / "order_tfr_mab.csv").set_index("year")
coh = pd.read_csv(RES / "cohort_cfr.csv")
rob = pd.read_csv(RES / "robustness_bf.csv", index_col=0)
C = ["#2a6fbb", "#e07b39", "#3c9d5d", "#b8417a", "#7b6fc4", "#8c8c8c"]

# 1) 年齢別出生率の形
fig, ax = plt.subplots(figsize=(8, 4.6))
for y, c in zip([1975, 2005, 2015, 2023], C):
    ax.plot(AGES, A.loc[y].values, color=c, lw=2.2, label=f"{y}年（合計 {A.loc[y].sum():.2f}）")
ax.set_xlabel("母の年齢（歳）")
ax.set_ylabel("年齢別出生率（女性1人あたり）")
ax.set_title("年齢別出生率の山は、48年で右へ移り、低くなった")
ax.legend(frameon=False)
ax.grid(alpha=.3)
fig.tight_layout()
fig.savefig(FIG / "f58_asfr.png")

# 2) TFR の変化の年齢別の内訳
groups = ["15-24", "25-29", "30-34", "35-39", "40-49"]
labels = ["15〜24歳", "25〜29歳", "30〜34歳", "35〜39歳", "40〜49歳"]
d = dec[dec.period.isin(["1975→2005", "2005→2015", "2015→2023"])].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 4.8))
x = np.arange(len(d))
pos = np.zeros(len(d)); neg = np.zeros(len(d))
for g, lab, c in zip(groups, labels, C):
    v = d[g].values
    base = np.where(v >= 0, pos, neg)
    ax.bar(x, v, 0.55, bottom=base, color=c, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
for i, ch in enumerate(d.change):
    ax.plot([i - .3, i + .3], [ch, ch], color="k", lw=2)
    ax.text(i + .32, ch, f"合計 {ch:+.2f}", va="center", fontsize=10)
ax.axhline(0, color="k", lw=.8)
ax.set_xticks(x)
ax.set_xticklabels([p.replace("→", "→\n") + "年" for p in d.period])
ax.set_ylabel("合計特殊出生率の変化")
ax.set_title("出生率の変化を、母の年齢に分ける")
ax.legend(frameon=False, ncol=2, fontsize=9, loc="lower right")
ax.set_xlim(-.6, len(d) - .1)
fig.tight_layout()
fig.savefig(FIG / "f58_decomp.png")

# 3) 平均出生年齢（出生順位別）
o = order.loc[1975:]
fig, ax = plt.subplots(figsize=(8, 4.5))
for col, lab, c in zip(["mab1", "mab2", "mab3", "mab"], ["第1子", "第2子", "第3子", "全体"], C[:3] + ["k"]):
    ax.plot(o.index, o[col], color=c, lw=2.2 if col != "mab" else 1.5, ls="-" if col != "mab" else "--", label=lab)
ax.set_ylabel("平均出生年齢（歳）")
ax.set_title("第1子の平均出生年齢は、25.7歳から30.7歳へ")
ax.legend(frameon=False)
ax.grid(alpha=.3)
fig.tight_layout()
fig.savefig(FIG / "f58_mab.png")

# 4) テンポ調整した TFR とコーホートの完結出生率
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.plot(yr.index, yr.tfr, color="k", lw=2, label="合計特殊出生率（公表）")
ax.plot(yr.index, yr.bf_order, color=C[0], lw=2, label="テンポ調整（出生順位別、Bongaarts–Feeney）")
ax.plot(yr.index, yr.bf_total, color=C[0], lw=1, ls=":", label="テンポ調整（順位別にしない）")
cc = coh.dropna(subset=["cfr49"])
cc = cc[cc.year_at_mab >= 1975]
ax.plot(cc.year_at_mab, cc.cfr49, "o", color=C[1], ms=4, label="コーホートの完結出生率（平均出生年齢の年に置く）")
ax.set_xlim(1975, 2024)
ax.set_ylim(1.0, 2.2)
ax.set_ylabel("女性1人あたりの子ども数")
ax.set_title("出産を遅らせる動きを除くと、出生率は0.1〜0.2高くなる")
ax.legend(frameon=False, fontsize=9)
ax.grid(alpha=.3)
fig.tight_layout()
fig.savefig(FIG / "f58_tempo.png")

# 5) 頑健性：テンポ調整の作り方
fig, ax = plt.subplots(figsize=(8, 4.5))
for col, c in zip(rob.columns, C):
    ax.plot(rob.index, rob[col], color=c, lw=2 if col.startswith("基本") else 1.2,
            ls="-" if col != "公表TFR" else "--", label=col)
ax.set_xlim(1976, 2023)
ax.set_ylabel("女性1人あたりの子ども数")
ax.set_title("テンポ調整の作り方を変えても、水準はほぼ同じ")
ax.legend(frameon=False, fontsize=8.5)
ax.grid(alpha=.3)
fig.tight_layout()
fig.savefig(FIG / "f58_robust.png")
print("ok")
