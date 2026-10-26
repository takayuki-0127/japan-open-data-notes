"""図を作る（5〜6枚）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, GREEN, RED, LIGHT

A = pd.read_csv(RES / "power_grid.csv")
MDE = pd.read_csv(RES / "mde_grid.csv")
B = pd.read_csv(RES / "fpr_by_se.csv")
C = pd.read_csv(RES / "error_structure_sim.csv")
E = pd.read_csv(RES / "staggered_twfe_cs.csv")
F = pd.read_csv(RES / "f14_mde.csv")
G = pd.read_csv(RES / "past_flagships.csv")

# 1 検出力曲線（効果の大きさ別、処置23県・12年）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, col, ttl, unit in [(axes[0], "emp_rate", "就業率", "%pt"), (axes[1], "unemp_rate", "完全失業率", "%pt")]:
    for T, c in [(4, LIGHT), (8, BLUE), (12, INK)]:
        d = A[(A.outcome == col) & (A.years == "2008-2019") & (A.k == 23) & (A["T"] == T)]
        ax.plot(d.delta, d.power_cl, marker="o", ms=3, color=c, label=f"{T}年（前後{T//2}年ずつ）")
    ax.axhline(0.8, color=GRAY, ls="--", lw=1); ax.axhline(0.05, color=GRAY, ls=":", lw=1)
    ax.set_xlabel(f"本当の効果の大きさ（{unit}）"); ax.set_ylabel("効果を見つけられた割合")
    ax.set_title(f"{ttl}：処置23県・比較24県"); ax.set_ylim(0, 1.02)
axes[0].legend(frameon=False, fontsize=9, loc="lower right")
axes[0].text(1.2, 0.81, "検出力80%", color=GRAY, fontsize=8, ha="right", va="bottom")
fig.suptitle("差の差で効果を見つけられる割合（実データにでたらめな処置を置いて1,000回）", fontsize=12, y=1.02)
save(fig, "f26_1_power_curve.png")

# 2 処置県の数と最小検出効果
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for T, c in [(4, LIGHT), (6, GRAY), (8, BLUE), (12, INK)]:
    d = MDE[(MDE.outcome == "emp_rate") & (MDE["T"] == T)]
    ax.plot(d.k, d.mde80, marker="o", color=c, label=f"{T}年")
ax.set_xlabel("処置県の数（47県のうち）"); ax.set_ylabel("検出力80%で見つかる最小の効果（就業率 %pt）")
ax.set_title("処置県が少なすぎても多すぎても、見つかる効果は大きくなる")
ax.legend(frameon=False, title="期間", fontsize=9)
save(fig, "f26_2_mde_by_k.png")

# 3 期間と検出力
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for dlt, c in [(0.3, BLUE), (0.5, INK), (0.8, GREEN)]:
    d = A[(A.outcome == "emp_rate") & (A.years == "2008-2025") & (A.k == 23) & (A.delta == dlt)].sort_values("T")
    ax.plot(d["T"], d.power_cl, marker="o", color=c, label=f"効果 {dlt}%pt")
ax.axhline(0.8, color=GRAY, ls="--", lw=1)
ax.set_xlabel("期間の長さ（年、前後半分ずつ）"); ax.set_ylabel("効果を見つけられた割合"); ax.set_ylim(0, 1.02)
ax.set_title("期間を延ばしても、検出力はほとんど上がらない（就業率・23県、2008〜2025年）")
ax.legend(frameon=False, fontsize=9)
save(fig, "f26_3_power_by_T.png")

# 4 標準誤差の種類と誤検出
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
cols = {"OLS（普通の標準誤差）": RED, "HC1（不均一分散に頑健）": ORANGE, "県クラスター": BLUE, "wild cluster bootstrap": GREEN}
for ax, col, ttl in [(axes[0], "emp_rate", "就業率"), (axes[1], "unemp_rate", "完全失業率")]:
    for s, c in cols.items():
        d = B[(B.outcome == col) & (B.se == s)]
        ax.plot(d.k, d.fpr, marker="o", color=c, label=s)
    ax.axhline(0.05, color=GRAY, ls="--", lw=1)
    ax.set_xlabel("処置県の数"); ax.set_title(f"{ttl}（効果0、12年、500回）")
axes[0].set_ylabel("効果0なのに「有意」になった割合")
axes[1].legend(frameon=False, fontsize=8.5)
axes[0].text(23, 0.055, "5%（本来の誤検出率）", color=GRAY, fontsize=8, ha="right", va="bottom")
save(fig, "f26_4_fpr_by_se.png")

# 5 これまでの看板記事
G2 = G.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 4.2))
y = np.arange(len(G2))
ax.barh(y, G2.ratio, color=[BLUE if r >= 1 else GRAY for r in G2.ratio])
ax.axvline(1, color=INK, lw=1, ls="--")
ax.set_yticks(y); ax.set_yticklabels(G2.key)
for i, (r, m, u) in enumerate(zip(G2.ratio, G2.mde80, G2.unit)):
    ax.text(r + 0.02, i, f"{r:.2f}（最小検出効果 {m:.2f}" + ("%pt）" if u == "%pt" else "、弾力性）"), va="center", fontsize=8.5)
ax.set_xlabel("推定値の大きさ ÷ 検出力80%の最小検出効果"); ax.set_xlim(0, max(1.6, G2.ratio.max() + 0.6))
ax.set_title("これまでの看板記事：推定値は「見つけられる大きさ」に届いていたか")
save(fig, "f26_5_past_flagships.png")

# 6 頑健性：誤差の構造と TWFE／CS
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
d0 = C[C.delta == 0.0]; d5 = C[C.delta == 0.5]
x = np.arange(len(d0)); w = 0.27
ax.bar(x - w, d0.power_ols, w, color=RED, label="OLS：誤検出")
ax.bar(x, d0.power_cl, w, color=BLUE, label="県クラスター：誤検出")
ax.bar(x + w, d5.power_cl, w, color=INK, label="県クラスター：効果0.5の検出力")
ax.axhline(0.05, color=GRAY, ls="--", lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"ρ={r}" for r in d0.rho]); ax.set_ylim(0, 1.25); ax.set_yticks([0, .2, .4, .6, .8, 1])
ax.set_title("誤差の時系列の相関（AR(1)）を変えた人工データ"); ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
ax = axes[1]
ax.plot(E.delta, E.true_att, color=GRAY, marker="o", label="本当の平均効果")
ax.plot(E.delta, E.twfe_mean, color=ORANGE, marker="o", label="TWFE の推定（平均）")
ax.plot(E.delta, E.cs_mean, color=BLUE, marker="o", label="CS 型の推定（平均）")
ax.set_xlabel("4年目の効果の大きさ（%pt）"); ax.set_ylabel("推定値（%pt）")
ax.set_title("時期がずれて効果が育つとき（3つの時期×8県）"); ax.legend(frameon=False, fontsize=8.5)
save(fig, "f26_6_robustness.png")
print("figs ok")
