"""F237 の図（6枚目のダッシュボードの画面は 06 で作る）。"""
import os, sys, json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
sys.path.insert(0, os.path.dirname(__file__))
from common import *
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
os.makedirs("figures", exist_ok=True)
M = json.load(open("results/main.json"))
Z = norm.ppf(0.975)
BLUE, RED, GRAY, GREEN, ORANGE = "#2b6cb0", "#c53030", "#888888", "#2f855a", "#dd6b20"

# 図1 見る回数と誤検出
A = pd.read_csv("results/A_peeking_false_positive.csv")
a14 = A[~A.looks.str.contains("28日")]
fig, ax = plt.subplots(figsize=(9, 4.8))
labels = ["1回\n（最後だけ）", "2回", "4回", "7回\n（2日ごと）", "14回\n（毎日）", "336回\n（1時間ごと）"]
y = a14.reject_rate.values * 100
bars = ax.bar(labels, y, color=[GREEN] + [RED] * 5)
for b_, v in zip(bars, y):
    ax.text(b_.get_x() + b_.get_width() / 2, v + 0.8, f"{v:.1f}%", ha="center")
ax.axhline(5, color="k", ls="--", lw=1); ax.text(5.45, 5.6, "決めた誤検出 5%", ha="right", fontsize=10)
ax.set_ylabel("差がないのに「有意」と判定した割合（%）")
ax.set_title("差がない2つの画面を14日間テストし、途中で見るたびに1.96で判定すると（2万回）")
ax.set_ylim(0, 52)
fig.tight_layout(); fig.savefig("figures/f237_01_peeking.png", dpi=150); plt.close()

# 図2 例：差がないのに途中で越える
ex = json.load(open("results/B_examples.json"))
rng = np.random.default_rng(5)
cA, cB, n = sim_cum(40, 14, BASE, BASE, 77)
h = np.arange(1, 15) * HOURS - 1
zz = zstat(cA[:, h], cB[:, h], n[h])
b4 = pd.read_csv("results/C_bounds_4looks.csv")
fig, ax = plt.subplots(figsize=(9, 4.8))
d = np.arange(1, 15)
for r in zz:
    ax.plot(d, r, color=GRAY, alpha=0.25, lw=1)
ax.plot(d, ex["z_H0"], color=RED, lw=2.5, marker="o", label="この記事の例（本当は差がない）")
ax.axhline(Z, color=RED, ls="--", lw=1); ax.axhline(-Z, color=RED, ls="--", lw=1)
ax.text(14.2, Z, "±1.96\n（毎日の判定）", color=RED, va="center", fontsize=9)
ax.scatter(b4.day, b4.obf, color=BLUE, marker="v", s=70, zorder=5, label="O'Brien-Fleming の境界（4回だけ見る）")
ax.scatter(b4.day, -b4.obf, color=BLUE, marker="^", s=70, zorder=5)
ax.set_xlabel("テスト開始からの日数"); ax.set_ylabel("累積の z（新しい画面 − いまの画面）")
ax.set_title("差がなくても、累積の z は行ったり来たりする（灰色は差がない40回）")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=9, frameon=False); ax.set_xticks(d); ax.set_xlim(0.5, 15.5)
fig.tight_layout(); fig.savefig("figures/f237_02_paths.png", dpi=150); plt.close()

# 図3 境界の形
bd = pd.read_csv("results/C_bounds_daily.csv")
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
ax = axs[0]
ax.plot(b4.day, b4.obf, marker="o", color=BLUE, label="O'Brien-Fleming")
ax.plot(b4.day, b4.pocock, marker="s", color=ORANGE, label="Pocock")
ax.axhline(Z, color=RED, ls="--", lw=1, label="毎回1.96（調整なし）")
for x, v, w in zip(b4.day, b4.obf, b4.pocock):
    up = v >= w
    ax.text(x, v + (0.12 if up else -0.28), f"{v:.2f}", ha="center", color=BLUE, fontsize=9)
    ax.text(x, w + (-0.28 if up else 0.12), f"{w:.2f}", ha="center", color=ORANGE, fontsize=9)
ax.set_title("4回（4・7・11・14日目）だけ見る"); ax.set_xlabel("日数"); ax.set_ylabel("止めるのに必要な |z|")
ax.legend(frameon=False, fontsize=9); ax.set_xticks(b4.day)
ax = axs[1]
ax.plot(bd.day, bd.obf.clip(upper=6), marker="o", color=BLUE, label="O'Brien-Fleming（毎日）")
ax.plot(bd.day, bd.pocock, marker="s", color=ORANGE, label="Pocock（毎日）")
ax.axhline(Z, color=RED, ls="--", lw=1)
ax.text(1.2, 5.85, "1日目は 7.3", fontsize=8, color=BLUE)
ax.set_title("毎日（14回）見る"); ax.set_xlabel("日数"); ax.set_ylim(1.5, 6.2); ax.legend(frameon=False, fontsize=9)
fig.suptitle("誤検出を5%に保つための境界（α 消費関数で決めた値）", y=1.0)
fig.tight_layout(); fig.savefig("figures/f237_03_bounds.png", dpi=150, bbox_inches="tight"); plt.close()

# 図4 方法の比較
C = pd.read_csv("results/C_methods_comparison.csv")
lab = ["固定\n14日目に1回", "毎日見て\n1.96で止める", "4回\nO'Brien-F", "4回\nPocock", "毎日\nO'Brien-F", "mSPRT\n14日まで", "mSPRT\n28日まで"]
col = [GREEN, RED, BLUE, BLUE, BLUE, ORANGE, ORANGE]
fig, axs = plt.subplots(1, 3, figsize=(13, 4.8))
for ax, key, ttl, fmt in [(axs[0], "fpr", "誤検出（差がないとき）", "{:.1f}%"), (axs[1], "power", "検出力（+10%の差があるとき）", "{:.0f}%"),
                          (axs[2], "mean_days_H1", "終わるまでの平均日数（+10%のとき）", "{:.1f}日")]:
    v = C[key].values * (100 if key != "mean_days_H1" else 1)
    bb = ax.barh(lab[::-1], v[::-1], color=col[::-1])
    for b_, x in zip(bb, v[::-1]):
        ax.text(x, b_.get_y() + b_.get_height() / 2, " " + fmt.format(x), va="center", fontsize=9)
    ax.set_title(ttl, fontsize=11)
    if key == "fpr": ax.axvline(5, color="k", ls="--", lw=1); ax.set_xlim(0, 28)
    if key == "power": ax.set_xlim(0, 108)
    if key == "mean_days_H1": ax.set_xlim(0, 17)
    if ax is not axs[0]: ax.set_yticklabels([])
fig.suptitle("基準5%・+10%・1日5,000人（2群合計）でのルールの比べ（各2万回）", y=1.0)
fig.tight_layout(); fig.savefig("figures/f237_04_compare.png", dpi=150, bbox_inches="tight"); plt.close()

# 図5 止まった日と、止まったときの差の大きさ
dist = M["stop_day_dist_H1"]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [2.2, 1]})
ax = axs[0]
for k, c, nm in [("毎日見て1.96で止める", RED, "毎日見て1.96"), ("4回・O'Brien-Fleming", BLUE, "4回・O'Brien-Fleming"),
                 ("mSPRT（1時間ごと・28日まで）", ORANGE, "mSPRT（28日まで）")]:
    dd = dist[k]; days = sorted(int(x) for x in dd if x != "no_stop")
    cum = np.cumsum([dd[str(x)] for x in days]) / 20000 * 100
    ax.step(days, cum, where="post", color=c, lw=2, label=nm)
ax.axvline(14, color=GREEN, ls=":", lw=1.5); ax.text(14.2, 4, "固定の判定日\n（14日目・検出力85%）", color=GREEN, fontsize=9)
ax.set_xlabel("テスト開始からの日数"); ax.set_ylabel("その日までに「差あり」で止まった割合（%）")
ax.set_title("本当に +10% の差があるとき、いつ止まるか"); ax.legend(frameon=False, fontsize=9, loc="lower right"); ax.set_xlim(0, 28)
ax = axs[1]
lab2 = ["固定14日", "毎日1.96", "4回OBF", "毎日OBF", "mSPRT28"]
keys = ["固定（14日目に1回）", "毎日見て1.96で止める", "4回・O'Brien-Fleming", "毎日・O'Brien-Fleming", "mSPRT（1時間ごと・28日まで）"]
v = [float(C.set_index("method").loc[k, "exaggeration_median"]) for k in keys]
bb = ax.bar(lab2, v, color=[GREEN, RED, BLUE, BLUE, ORANGE])
for b_, x in zip(bb, v): ax.text(b_.get_x() + b_.get_width() / 2, x + 0.02, f"{x:.2f}倍", ha="center", fontsize=9)
ax.axhline(1, color="k", lw=1); ax.set_ylim(0.8, 1.5)
ax.set_title("止めたときの差 ÷ 本当の差（中央値）", fontsize=11); ax.tick_params(axis="x", labelsize=9)
fig.tight_layout(); fig.savefig("figures/f237_05_stopday.png", dpi=150); plt.close()
print("ok")
