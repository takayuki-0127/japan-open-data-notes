"""図（Noto Sans CJK JP）。"""
import calendar
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import DATA, RES, FIG, WD

for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C1, C2, C3, C4 = "#2b6cb0", "#c05621", "#2f855a", "#805ad5"
TYPES = WD + ["祝日", "年末年始"]

# 1. 曜日の指数（年ごとの幅つき）
it = pd.read_csv(RES / "weekday_index_by_year.csv", index_col=0)[TYPES]
fig, ax = plt.subplots(figsize=(8, 4.6))
m = it.mean()
cols = [C1] * 5 + [C2] * 2 + [C3, C3]
ax.bar(range(len(TYPES)), m.values, color=cols, alpha=.85)
ax.errorbar(range(len(TYPES)), m.values, yerr=[m - it.min(), it.max() - m], fmt="none", ecolor="#333", capsize=4, lw=1)
for i, v in enumerate(m.values):
    ax.text(i, it.iloc[:, i].max() + 2, f"{v:.0f}", ha="center", fontsize=10)
ax.axhline(100, color="#666", lw=.8, ls="--")
ax.set_xticks(range(len(TYPES)), TYPES)
ax.set_ylabel("1日あたり出生数の指数（その年の平均＝100）")
ax.set_ylim(0, 140)
ax.set_title("出生数は、土日・祝日・年末年始に3〜4割少ない（2018〜2025年、線は年ごとの幅）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f172_weekday.png"); plt.close(fig)

# 2. 出生の場所別
pl = pd.read_csv(RES / "weekday_index_by_place.csv", index_col=0)
sel = ["土", "日", "祝日", "年末年始"]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(sel)); w = .2
for j, (p, c) in enumerate(zip(["病院", "診療所", "助産所", "自宅"], [C1, C4, C3, C2])):
    v = pl.loc[p, sel].values
    ax.bar(x + (j - 1.5) * w, v, w, color=c, label=p)
ax.axhline(100, color="#666", lw=.8, ls="--")
ax.set_xticks(x, sel)
ax.set_ylabel("平日（月〜金）の1日平均＝100")
ax.set_ylim(0, 115)
ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(.5, 1.0))
ax.set_title("土日の落ち込みは病院・診療所で大きく、助産所・自宅ではほとんどない（2018〜2025年）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f172_place.png"); plt.close(fig)

# 3. 時刻
hp = pd.read_csv(RES / "births_per_hour_per_day.csv", index_col=0)
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.plot(hp.index, hp["平日"], marker="o", ms=3.5, color=C1, label="平日（月〜金）")
ax.plot(hp.index, hp["日曜・祝日"], marker="o", ms=3.5, color=C2, label="日曜・祝日")
ax.fill_between(hp.index, hp["日曜・祝日"], hp["平日"], where=hp["平日"] > hp["日曜・祝日"], color=C1, alpha=.12)
ax.axvspan(8.5, 16.5, color="#999", alpha=.08)
ax.text(12.5, hp["平日"].max() * 1.02, "9時台〜16時台", ha="center", fontsize=9, color="#555")
ax.set_xticks(range(0, 24, 2))
ax.set_xlabel("出生の時刻（時台）"); ax.set_ylabel("1日あたりの出生数（全国）")
ax.legend(frameon=False)
ax.set_title("平日と日曜の差の8割は、9時台〜16時台に集まっている（2018〜2025年）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f172_hour.png"); plt.close(fig)

# 4. 季節の円（月別、1日あたりに直した指数）
mo = pd.read_csv(DATA / "births_deaths_monthly.csv")
fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), subplot_kw={"projection": "polar"})
for ax, kind, title in [(axs[0], "births", "出生"), (axs[1], "deaths", "死亡")]:
    for y, c in [(1955, C3), (1985, C4), (2024, C2)]:
        g = mo[mo.year == y].sort_values("month")
        days = np.array([calendar.monthrange(y, m)[1] for m in range(1, 13)])
        r = g[kind].values / days
        r = r / r.mean() * 100
        th = 2 * np.pi * (np.cumsum(days) - days / 2) / days.sum()
        ax.plot(np.r_[th, th[0]], np.r_[r, r[0]], color=c, lw=1.8, label=str(y))
    ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
    ax.set_xticks(2 * np.pi * (np.arange(12) + .5) / 12, [f"{m}月" for m in range(1, 13)], fontsize=9)
    ax.set_ylim(60, 145); ax.set_yticks([80, 100, 120]); ax.tick_params(axis="y", labelsize=8)
    ax.set_title(f"{title}（1日あたり、年平均＝100）", fontsize=11, pad=14)
axs[1].legend(loc="lower right", bbox_to_anchor=(1.25, -.08), frameon=False, fontsize=9)
fig.suptitle("死亡は冬に大きく張り出す。出生のふくらみは冬から夏の終わりへ移り、小さくなった", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f172_season_circle.png"); plt.close(fig)

# 5. 集中度 R の推移
cs = pd.read_csv(RES / "season_circular_by_year.csv")
fig, axs = plt.subplots(1, 2, figsize=(9, 4.2))
for kind, c, lab in [("births", C1, "出生"), ("deaths", C2, "死亡")]:
    s = cs[cs.kind == kind]
    axs[0].plot(s.year, s.R, marker="o", ms=3.5, color=c, label=lab)
    axs[1].plot(s.year, s.mean_doy.where(s.mean_doy < 300, s.mean_doy - 365.25), marker="o", ms=3.5, color=c, label=lab)
axs[0].axhline(0.0217, color=C1, ls=":", lw=1)
axs[0].text(1947, 0.0235, "出生：月を並べ替えても出る大きさ（95%点）", fontsize=8, color=C1)
axs[0].set_ylabel("季節への集中度 R（0＝偏りなし）"); axs[0].set_ylim(0, .14)
axs[0].legend(frameon=False)
ticks = [0, 59, 120, 181, 243, 304]
axs[1].set_yticks(ticks, ["1月", "3月", "5月", "7月", "9月", "11月"])
axs[1].set_ylabel("平均の方向（季節の重心）")
axs[0].set_title("集中度", fontsize=11); axs[1].set_title("重心の時期", fontsize=11)
fig.suptitle("死亡の季節の偏りは1970年代以降、出生の数倍。出生の重心は1960年ごろの1〜2月から、2000年代は9月ごろへ", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f172_season_trend.png"); plt.close(fig)
print("ok")
