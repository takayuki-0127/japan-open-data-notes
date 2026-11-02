"""04 図：figures/ に5枚"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import RES, FIG, BLOCKS

plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
S = json.load(open(RES / "summary.json")); cur = pd.read_csv(RES / "lag_curves.csv"); er = pd.read_csv(RES / "exposure_response.csv")
rob = pd.read_csv(RES / "robustness.csv")
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator
def logy(ax, ticks=(0.2, 0.3, 0.5, 0.7, 1, 1.5, 2, 3, 5, 8, 12, 20, 30)):
    ax.yaxis.set_major_locator(FixedLocator(ticks)); ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
C1, C2, C3 = "#c0392b", "#2c6fbb", "#7f8c8d"

# 1 遅れごとの RR（35℃ 対 25℃）
fig, ax = plt.subplots(figsize=(7.5, 4.3))
for t, c in [(35, C1), (30, "#e67e22")]:
    d = cur[(cur.model == "基本") & (cur.t == t)]
    ax.plot(d.lag, d.rr, "o-", color=c, label=f"最高気温 {t}℃ の日（対 25℃）")
    ax.fill_between(d.lag, d.lo, d.hi, color=c, alpha=0.15)
ax.axhline(1, color="k", lw=0.8)
ax.set_xticks(range(11)); ax.set_xlabel("暑い日から何日後か"); ax.set_ylabel("搬送の相対リスク（その日の寄与）")
ax.set_yscale("log"); logy(ax); ax.legend(frameon=False, fontsize=9)
ax.set_title("暑い日の影響は当日が大半で、2日後まで残り、3〜4日後はやや下がる", loc="left", fontsize=12)
fig.text(0.01, 0.01, "47都道府県・2015〜2025年6〜9月。網かけは95%区間。出典：総務省消防庁・気象庁から作成", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig1_lag_response.png", dpi=150); plt.close()

# 2 気温×遅れの面
lags = [f"lag{l}" for l in range(11)]
Z = np.log(er[lags].values)
fig, ax = plt.subplots(figsize=(7.5, 4.5))
v = np.nanmax(np.abs(Z))
im = ax.imshow(Z.T, origin="lower", aspect="auto", cmap="RdBu_r", vmin=-v, vmax=v,
               extent=(er.t.min() - 0.25, er.t.max() + 0.25, -0.5, 10.5))
cb = fig.colorbar(im, ax=ax); ticks = [0.5, 1, 2, 4, 8, 16]
cb.set_ticks([np.log(x) for x in ticks if abs(np.log(x)) <= v]); cb.set_ticklabels([str(x) for x in ticks if abs(np.log(x)) <= v]); cb.set_label("相対リスク（対 25℃）")
ax.set_xlabel("その日の最高気温（℃）"); ax.set_ylabel("何日後か"); ax.set_yticks(range(11))
ax.set_title("気温と遅れの2次元で見た効き方", loc="left", fontsize=12)
fig.text(0.01, 0.01, "分布ラグ非線形モデル（自然スプライン×自然スプライン、0〜10日）。出典：総務省消防庁・気象庁から作成", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig2_surface.png", dpi=150); plt.close()

# 3 気温反応（累積 vs 当日のみ）
fig, ax = plt.subplots(figsize=(7.5, 4.3))
ax.plot(er.t, er.cum_rr, color=C1, label="0〜10日の累積")
ax.fill_between(er.t, er.lo, er.hi, color=C1, alpha=0.15)
ax.plot(er.t, er.lag0_rr, color=C2, ls="--", label="当日（遅れ0日）の分だけ")
ax.axhline(1, color="k", lw=0.8); ax.set_yscale("log"); logy(ax)
ax.set_xlabel("その日の最高気温（℃）"); ax.set_ylabel("搬送の相対リスク（対 25℃）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("35℃の日の搬送は、25℃の日のおよそ20倍（0〜10日の累積）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "網かけは累積の95%区間。出典：総務省消防庁・気象庁から作成", fontsize=7.5, color="#555")
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig3_exposure_response.png", dpi=150); plt.close()

# 4 頑健性：遅れの長さ・指標・年齢
fig, axs = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
for m, c in [("L7", "#95a5a6"), ("L14", "#e67e22"), ("L21", "#8e44ad")]:
    d = cur[cur.model == m]; axs[0].plot(d.lag, d.rr, "o-", ms=3, color=c, label=f"遅れ 0〜{m[1:]}日")
d = cur[(cur.model == "基本") & (cur.t == 35)]; axs[0].plot(d.lag, d.rr, "o-", ms=3, color=C1, label="基本（0〜10日）")
axs[0].set_title("遅れの長さを変える（35℃ 対 25℃）", fontsize=10, loc="left")
for m, c in [("指標:最高気温", C1), ("指標:日平均気温", C2), ("指標:WBGT の近似", "#27ae60")]:
    d = cur[cur.model == m]; axs[1].plot(d.lag, d.rr, "o-", ms=3, color=c, label=m.split(":")[1])
axs[1].set_title("気温の指標を変える（97.5%点 対 50%点）", fontsize=10, loc="left")
for a in axs:
    a.axhline(1, color="k", lw=0.8); a.set_yscale("log"); logy(a); a.set_xlabel("何日後か"); a.legend(frameon=False, fontsize=8)
axs[0].set_ylabel("相対リスク")
fig.suptitle("遅れの形は、指標や長さを変えてもほぼ同じ", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig4_robustness.png", dpi=150); plt.close()

# 5 地方ブロック
fig, axs = plt.subplots(2, 4, figsize=(10, 5), sharex=True, sharey=True)
for a, bl in zip(axs.ravel(), BLOCKS):
    d = cur[cur.model == f"地方:{bl}"]
    a.plot(d.lag, d.rr, "o-", ms=3, color=C1); a.fill_between(d.lag, d.lo, d.hi, color=C1, alpha=0.15)
    a.axhline(1, color="k", lw=0.7); a.set_yscale("log"); logy(a); a.set_xticks([0, 2, 4, 6, 8, 10]); a.set_title(f"{bl}（{d.t.iloc[0]:.1f}℃）", fontsize=9)
for a in axs[1]: a.set_xlabel("何日後か", fontsize=8)
fig.suptitle("地方ごとに見ても、影響は当日〜2日後に集中し、3〜4日後はわずかに下がる（各地方の97.5%点 対 中央値）", x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig5_blocks.png", dpi=150); plt.close()
print("ok")
