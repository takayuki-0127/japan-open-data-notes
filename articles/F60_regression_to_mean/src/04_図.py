"""図を作る"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG

IND = ["完全失業率", "就業率", "有効求人倍率", "合計特殊出生率"]
C = ["#2E6DB4", "#E07B39", "#3A9E6F", "#8C5BB5"]

# 1) 完全失業率：今年の位置と翌年の位置（全国の中央値からの差、良い向き＝失業率が低いほど右・上）
pref = pd.read_csv(DATA / "pref_long.csv")
w = pref[pref.indicator == "完全失業率"].pivot(index="year", columns="code", values="good")
r = w.sub(w.median(axis=1), axis=0)
xs, ys, wx, wy = [], [], [], []
for y in r.index[:-1]:
    a, b = r.loc[y], r.loc[y + 1]
    xs += list(a); ys += list(b)
    o = a.sort_values().index[:5]
    wx += list(a[o]); wy += list(b[o])
fig, ax = plt.subplots(figsize=(6.4, 5.6))
ax.scatter(xs, ys, s=10, color="#BBBBBB", label="すべての県×年")
ax.scatter(wx, wy, s=22, color="#D1495B", label="その年の下位5県")
lim = [min(xs + ys) - 0.1, max(xs + ys) + 0.1]
ax.plot(lim, lim, color="black", lw=1, ls="--", label="翌年も同じ位置（45度線）")
X = np.column_stack([np.ones(len(xs)), xs]); b = np.linalg.lstsq(X, ys, rcond=None)[0]
ax.plot(lim, b[0] + b[1] * np.array(lim), color=C[0], lw=1.6, label=f"当てはめた直線（傾き {b[1]:.2f}）")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("その年の位置（全国の中央値との差、ポイント。右ほど失業率が低い）")
ax.set_ylabel("翌年の位置（同じ）")
ax.set_title("完全失業率：下位5県（赤）は翌年、45度線より上に来やすい\n2008〜2025年の都道府県（モデル推計値）")
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "f60_scatter_unemp.png"); plt.close(fig)

# 2) 下位5・中位・上位5の翌年の変化（その年の標準偏差の単位）
d = json.load(open(RES / "summary.json"))["base"]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
x = np.arange(len(IND)); wdt = 0.26
p = pd.read_csv(RES / "pairs_gap1.csv")
mid_sd = [(p[p.indicator == i].mid_d / p[p.indicator == i].sd).mean() for i in IND]
ax.bar(x - wdt, [d[i]["worst_d_sd"] for i in IND], wdt, color="#D1495B", label="その年の下位5")
ax.bar(x, mid_sd, wdt, color="#999999", label="中位（6〜42位）")
ax.bar(x + wdt, [d[i]["best_d_sd"] for i in IND], wdt, color=C[0], label="その年の上位5")
for i, ind in enumerate(IND):
    ax.text(i - wdt, d[ind]["worst_d_sd"] + 0.01, f"{d[ind]['worst_d_sd']:+.2f}", ha="center", fontsize=8)
    ax.text(i + wdt, d[ind]["best_d_sd"] - 0.03, f"{d[ind]['best_d_sd']:+.2f}", ha="center", fontsize=8)
ax.axhline(0, color="black", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{i}\n（相関 {d[i]['corr']:.2f}）" for i in IND])
ax.set_ylabel("翌年の位置の変化（標準偏差の単位、＋が良くなる向き）")
ax.set_title("その年の下位は翌年少し良く、上位は少し悪く見える\n（全国の中央値からの差。カッコは今年と翌年の位置の相関）")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "f60_bars.png"); plt.close(fig)

# 3) 何年あけるか
g = pd.read_csv(RES / "gaps.csv")
fig, ax = plt.subplots(figsize=(6.6, 4.2))
for i, ind in enumerate(IND):
    q = g[g.indicator == ind]
    ax.plot(q.gap, q.worst_d_sd, marker="o", color=C[i], label=ind)
ax.axhline(0, color="black", lw=0.8)
ax.set_xlabel("何年後と比べるか")
ax.set_ylabel("下位5の位置の変化（標準偏差の単位）")
ax.set_title("間をあけるほど「良くなったように見える」幅は広がる\n（完全失業率は5年後に0.65標準偏差）")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "f60_gaps.png"); plt.close(fig)

# 4) 見かけの施策効果
pp = pd.read_csv(RES / "placebo_policy_unemp.csv")
fig, ax = plt.subplots(figsize=(7.0, 4.2))
lab = {"naive": "前後で比べる", "vs_next": "6〜10位の県と比べる", "adjusted": "回帰の分を差し引く"}
for k, (c, col) in enumerate(lab.items()):
    jitter = (k - 1) * 0.12
    ax.scatter(np.full(len(pp), k) + jitter, pp[c], color=[C[0], C[1], C[2]][k], s=18, alpha=0.7)
    ax.hlines(pp[c].mean(), k - 0.3, k + 0.3, color="black", lw=2)
    ax.text(k + 0.32, pp[c].mean(), f"平均 {pp[c].mean():+.3f}\n（＋の年 {int((pp[c] > 0).sum())}/{len(pp)}）", va="center", fontsize=8)
ax.axhline(0, color="black", lw=0.8, ls=":")
ax.set_xticks(range(3)); ax.set_xticklabels(list(lab.values()))
ax.set_xlim(-0.5, 2.9)
ax.set_ylabel("「効果」（失業率のポイント、＋が改善）")
ax.set_title("何もしていないのに「効果」が出る：失業率の高い5県に施策をしたとみなした場合\n（2008→09年〜2024→25年の17回）")
fig.tight_layout(); fig.savefig(FIG / "f60_placebo_policy.png"); plt.close(fig)

# 5) 市区町村の検診受診率：規模別
ms = pd.read_csv(RES / "muni_screening_summary.csv")
fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.2))
x = np.arange(len(ms))
axes[0].bar(x - 0.2, ms.low_d, 0.4, color="#D1495B", label="全体の下位10%に入った団体")
axes[0].bar(x + 0.2, ms.high_d, 0.4, color=C[0], label="全体の上位10%に入った団体")
for i in x:
    axes[0].text(i - 0.2, ms.low_d[i] + 0.15, f"{ms.low_d[i]:+.1f}", ha="center", fontsize=8)
    axes[0].text(i + 0.2, ms.high_d[i] - 0.5, f"{ms.high_d[i]:+.1f}", ha="center", fontsize=8)
axes[0].axhline(0, color="black", lw=0.8)
axes[0].set_xticks(x); axes[0].set_xticklabels(ms["size"], fontsize=8)
axes[0].set_xlabel("対象者数（国保・40〜69歳）")
axes[0].set_ylabel("翌年の受診率の変化（ポイント、全国の中央値との差）")
axes[0].legend(fontsize=7)
axes[0].set_title("下位だった町の翌年の伸び", fontsize=10)
axes[1].bar(x, ms.slope, color="#666666")
for i in x:
    axes[1].text(i, ms.slope[i] + 0.01, f"{ms.slope[i]:.2f}", ha="center", fontsize=8)
axes[1].set_ylim(0.6, 1.0)
axes[1].set_xticks(x); axes[1].set_xticklabels(ms["size"], fontsize=8)
axes[1].set_ylabel("今年の位置に対する翌年の位置の傾き（1なら回帰なし）")
axes[1].set_title("規模が小さいほど傾きが1から離れる", fontsize=10)
fig.suptitle("市区町村の大腸がん検診受診率（2021→22〜2023→24年度）：小さい町ほど平均に戻る", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f60_muni_size.png"); plt.close(fig)

# 6) シミュレーション：信頼性と回帰の大きさ
sim = pd.read_csv(RES / "simulation.csv")
rf = pd.read_csv(RES / "reliability_vs_rtm.csv")
fig, ax = plt.subplots(figsize=(6.6, 4.4))
ax.fill_between(sim.rho, sim.worst5_d_q05, sim.worst5_d_q95, color="#DDDDDD", label="シミュレーションの90%の範囲")
ax.plot(sim.rho, sim.worst5_d, color="black", marker="o", label="シミュレーション（下位5の平均の変化）")
for i, row in rf.iterrows():
    ax.scatter(row["corr"], row["worst_d_sd"], color=C[i], s=50, zorder=5, label=f"実データ：{row['indicator']}")
ax.axhline(0, color="black", lw=0.6)
ax.set_xlabel("今年と翌年の位置の相関（信頼性）")
ax.set_ylabel("下位5の翌年の変化（標準偏差の単位）")
ax.set_title("回帰の大きさは「毎年の値がどれだけ同じか」でほぼ決まる\n（47地域・下位5・2,000回）")
ax.legend(fontsize=7, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "f60_simulation.png"); plt.close(fig)
print("図を保存しました")
