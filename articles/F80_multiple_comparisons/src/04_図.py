"""図を作る"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

S = json.loads((RES / "summary.json").read_text())
tab = pd.read_csv(RES / "east_west_tests.csv")
nr = pd.read_csv(RES / "null_random_splits.csv")
nc = pd.read_csv(RES / "null_contiguous_splits.csv")
M = ["補正なし", "Bonferroni", "Holm", "BH (FDR)", "BY"]
C = ["#7a7a7a", "#2b6cb0", "#4a90c8", "#d9822b", "#b5651d"]

# 図1：東西の100指標の p 値と、補正ごとの有意の数
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.3, 1]})
ax[0].hist(tab.p, bins=np.linspace(0, 1, 21), color="#4a90c8", edgecolor="white")
ax[0].axhline(5, color="#c0392b", ls="--", lw=1); ax[0].text(0.52, 5.6, "差がまったくないときの高さ（各5本）", color="#c0392b", fontsize=9)
ax[0].set_xlabel("p 値"); ax[0].set_ylabel("指標の数"); ax[0].set_title("東日本17 vs 西日本30：100指標の p 値")
v = [S["east_west"][m] for m in M]
b = ax[1].bar(M, v, color=C)
for r, x in zip(b, v): ax[1].text(r.get_x() + r.get_width() / 2, x + 0.6, str(x), ha="center")
ax[1].set_ylim(0, max(v) * 1.15); ax[1].set_title("「有意（5%）」の数"); ax[1].set_ylabel("指標の数"); ax[1].tick_params(axis="x", rotation=20)
fig.tight_layout(); fig.savefig(FIG / "f80_east_west.png", dpi=150); plt.close(fig)

# 図2：でたらめな分け方での有意の数（補正なし）
fig, ax = plt.subplots(figsize=(9, 4.3))
bins = np.arange(0, max(nr["補正なし"].max(), nc["補正なし"].max(), S["east_west"]["補正なし"]) + 3, 2)
ax.hist(nr["補正なし"], bins=bins, alpha=.6, density=True, color="#7a7a7a", label="47県をでたらめに17と30に分ける（10,000回）")
ax.hist(nc["補正なし"], bins=bins, alpha=.6, density=True, color="#d9822b", label="隣どうしつながる17県を選ぶ（5,000回）")
ax.axvline(S["east_west"]["補正なし"], color="#c0392b", lw=2); ax.text(S["east_west"]["補正なし"] + .5, ax.get_ylim()[1] * .9, "東日本 vs 西日本", color="#c0392b")
ax.axvline(5, color="k", ls=":", lw=1); ax.text(5.3, ax.get_ylim()[1] * .75, "100×5%＝5", fontsize=9)
ax.set_xlabel("100指標のうち p<0.05 になった数（補正なし）"); ax.set_ylabel("割合"); ax.legend(fontsize=9)
ax.set_title("意味のない分け方でも「有意」はいくつ出るか")
fig.tight_layout(); fig.savefig(FIG / "f80_null.png", dpi=150); plt.close(fig)

# 図3：人工データでの各補正の成績
sim = S["simulation"]["相関あり_差1SD"]; sim0 = S["simulation"]["全部ゼロ_相関あり"]
fig, ax = plt.subplots(1, 3, figsize=(12, 4))
for i, (key, src, tt) in enumerate([("FWER", sim0, "本当の差がゼロのとき\n誤検出が1つ以上出る確率"),
                                     ("FDR", sim, "見つけたうち誤検出の割合\n（20指標に本当の差）"),
                                     ("power", sim, "本当の差を見つけた割合\n（20指標・差は1標準偏差）")]):
    v = [src[m][key] for m in M]
    b = ax[i].bar(M, v, color=C)
    for r, x in zip(b, v): ax[i].text(r.get_x() + r.get_width() / 2, x + .01, f"{x:.2f}", ha="center", fontsize=9)
    ax[i].set_ylim(0, 1.05); ax[i].set_title(tt, fontsize=10); ax[i].tick_params(axis="x", rotation=30)
    if key != "power": ax[i].axhline(.05, color="#c0392b", ls="--", lw=1)
fig.suptitle("正解がわかる人工データ（実データの相関を保ったまま、2,000回）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f80_simulation.png", dpi=150); plt.close(fig)

# 図4：指標の数を増やすと
R = S["robust"]; ns = [k for k in R if k.startswith("東西_指標")]
n = [int(k.replace("東西_指標", "")) for k in ns]
fig, ax = plt.subplots(figsize=(8.5, 4.3))
for m, c in zip(M, C):
    ax.plot(n, [R[k][m] for k in ns], "o-", color=c, label=m)
ax.plot(n, [x * .05 for x in n], "k:", label="差がゼロでも出る数の目安（指標数×5%）")
ax.set_xlabel("比べた指標の数（東日本 vs 西日本）"); ax.set_ylabel("有意の数"); ax.legend(fontsize=9)
ax.set_title("指標を増やすと、補正なしの「有意」は増え、Bonferroni の基準は厳しくなる")
fig.tight_layout(); fig.savefig(FIG / "f80_n_indicators.png", dpi=150); plt.close(fig)

# 図5：BH で残った指標の差（効果量）
t = tab[tab.p_bh < .05].sort_values("cohen_d")
t = pd.concat([t.head(8), t.tail(8)]).drop_duplicates()
fig, ax = plt.subplots(figsize=(10, 0.36 * len(t) + 1.2))
lab = [s if len(s) <= 34 else s[:33] + "…" for s in t.name]
ax.barh(range(len(t)), t.cohen_d, color=np.where(t.cohen_d > 0, "#2b6cb0", "#d9822b"))
ax.set_yticks(range(len(t))); ax.set_yticklabels(lab, fontsize=8)
ax.axvline(0, color="k", lw=.8); ax.set_xlabel("差の大きさ（標準化した平均の差、＋なら東日本が大きい）")
ax.set_title(f"BH で残った指標（{int((tab.p_bh<.05).sum())}本）のうち、差が大きい両端")
fig.tight_layout(); fig.savefig(FIG / "f80_effects.png", dpi=150); plt.close(fig)

# 図6：頑健性
keys = [k for k in R if isinstance(R[k], dict) and "補正なし" in R[k] and not k.startswith("東西_指標")]
fig, ax = plt.subplots(figsize=(10, 4.5))
w = .16; x = np.arange(len(keys))
for i, (m, c) in enumerate(zip(M, C)):
    ax.bar(x + (i - 2) * w, [R[k][m] for k in keys], w, color=c, label=m)
ax.set_xticks(x); ax.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=8)
ax.set_ylabel("有意の数"); ax.set_ylim(0, 72); ax.legend(fontsize=8, ncol=5, loc="upper left"); ax.set_title("頑健性：分け方・検定・年・指標の選び方を変えても")
fig.tight_layout(); fig.savefig(FIG / "f80_robust.png", dpi=150); plt.close(fig)
print("ok")
