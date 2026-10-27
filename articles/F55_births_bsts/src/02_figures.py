"""F55 図（6枚）"""
from common import *
import matplotlib.ticker as mt

d = monthly()
man = lambda x, p=None: f"{x/10000:.0f}万"

# 1. コロナがなかった場合（月次）
m = pd.read_csv(RES / "A_monthly_forecast.csv", parse_dates=["date"])
fig, ax = plt.subplots(figsize=(10, 5))
hist = d.loc["2015":"2025"]
ax.plot(hist.index, hist["births"], color=INK, lw=1.2, label="実績")
for name, c, lc in [("SARIMA", ORANGE, LORANGE), ("BSTS", BLUE, LIGHT)]:
    s = m[m.model == name]
    ax.fill_between(s.date, s.lo95, s.hi95, color=lc, alpha=0.45 if name == "BSTS" else 0.35, lw=0,
                    label=f"{name} 95%区間")
    ax.plot(s.date, s["median"], color=c, lw=1.3, ls="--", label=f"{name} 予測の中央値")
ax.axvline(pd.Timestamp("2020-01-01"), color=GRAY, lw=0.8)
ax.text(pd.Timestamp("2020-02-01"), ax.get_ylim()[1] * 0.98, "ここから予測（2019年12月までで学習）", fontsize=9, color=GRAY, va="top")
ax.yaxis.set_major_formatter(mt.FuncFormatter(man))
ax.set_title("2010〜19年で学習した「コロナがなかった場合」の出生数（月次）")
ax.set_ylabel("月の出生数（人）"); ax.legend(fontsize=8, ncol=2, loc="lower left", frameon=False)
save(fig, "f55_counterfactual.png")

# 2. 予測区間の幅（予測の長さ別）
fig, ax = plt.subplots(figsize=(8, 4.5))
for name, c in [("BSTS", BLUE), ("SARIMA", ORANGE)]:
    s = m[m.model == name]
    ax.plot(s.h, (s.hi95 - s.lo95) / s["median"] * 100, color=c, lw=2, label=name)
ax.set_xlabel("何か月先の予測か"); ax.set_ylabel("95%区間の幅（予測の中央値に対する%）")
ax.set_title("先の予測ほど幅は広がる：BSTS と SARIMA の95%区間の幅")
ax.legend(frameon=False)
save(fig, "f55_width.png")

# 3. バックテスト：区間に入った割合
b = pd.read_csv(RES / "B_backtest_summary.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
for ax, lev in zip(axes, [0.8, 0.95]):
    s = b[b.level == lev]
    groups = ["1-12", "13-24", "25-36"]
    x = np.arange(len(groups)); w = 0.38
    for j, (name, c) in enumerate([("BSTS", BLUE), ("SARIMA", ORANGE)]):
        v = [s[(s.model == name) & (s.hgrp == g)]["coverage"].values for g in groups]
        v = [x_[0] * 100 if len(x_) else np.nan for x_ in v]
        ax.bar(x + (j - 0.5) * w, v, w, color=c, label=name)
        for xi, vi in zip(x, v):
            ax.text(xi + (j - 0.5) * w, vi + 1, f"{vi:.0f}", ha="center", fontsize=8)
    ax.axhline(lev * 100, color=INK, lw=1, ls=":")
    ax.set_xticks(x, [f"{g}か月先" for g in groups])
    ax.set_title(f"{int(lev*100)}%区間に入った割合（点線が目標）", fontsize=11)
    ax.set_ylim(0, 110)
axes[0].set_ylabel("%"); axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("バックテスト（2014〜18年末を起点に、2019年までを予測）", y=1.02)
save(fig, "f55_backtest.png")

# 4. 2026〜30年
c = pd.read_csv(RES / "C_future_annual.csv")
ann = d.loc["2010":"2025"].groupby("year")["births"].sum()
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(ann.index, ann.values, color=INK, marker="o", ms=3, lw=1.2, label="実績")
s = c[c.model == "BSTS"]
ax.fill_between(s.year, s.lo95, s.hi95, color=LIGHT, alpha=0.5, lw=0, label="BSTS 95%区間")
ax.fill_between(s.year, s.lo80, s.hi80, color=BLUE, alpha=0.25, lw=0, label="BSTS 80%区間")
ax.plot(s.year, s["median"], color=BLUE, marker="o", ms=3, ls="--", label="BSTS 中央値")
s2 = c[c.model == "SARIMA"]
ax.plot(s2.year, s2["median"], color=ORANGE, marker="s", ms=3, ls=":", label="SARIMA 中央値")
ax.yaxis.set_major_formatter(mt.FuncFormatter(man))
ax.set_title("2016〜25年の動きが続いた場合の年間出生数（2026〜30年）")
ax.set_ylabel("年間出生数（人）"); ax.legend(frameon=False, fontsize=8)
ax.xaxis.set_major_locator(mt.MaxNLocator(integer=True))
save(fig, "f55_future.png")

# 5. 傾き（1年あたりの増減率）の推移
sl = pd.read_csv(RES / "D_slope_path.csv", parse_dates=["date"])
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.fill_between(sl.date, (np.exp(sl.lo90) - 1) * 100, (np.exp(sl.hi90) - 1) * 100, color=LIGHT, alpha=0.6, lw=0,
                label="90%区間")
ax.plot(sl.date, sl.pct_per_year_med, color=BLUE, lw=2, label="中央値")
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_ylabel("トレンドの傾き（%/年）")
ax.set_title("出生数（1日あたり）のトレンドは、1年あたり何%のペースで動いていたか")
ax.legend(frameon=False)
save(fig, "f55_slope.png")

# 6. 頑健性
r = pd.read_csv(RES / "E_robustness_counterfactual.csv")
rf = pd.read_csv(RES / "E_robustness_future.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"wspace": 0.75})
ax = axes[0]
yy = np.arange(len(r))[::-1]
ax.errorbar(r.gap2020_22_med / 10000, yy, xerr=[(r.gap2020_22_med - r.gap_lo95) / 10000, (r.gap_hi95 - r.gap2020_22_med) / 10000],
            fmt="o", color=BLUE, capsize=3)
ax.axvline(0, color=GRAY, lw=0.8)
ax.set_yticks(yy, r.variant, fontsize=8); ax.set_xlabel("万人")
ax.set_title("2020〜22年の累計：実績 −「なかった場合」", fontsize=10)
ax = axes[1]
yy = np.arange(len(rf))[::-1]
ax.errorbar(rf.y2030_med / 10000, yy, xerr=[(rf.y2030_med - rf.y2030_lo95) / 10000, (rf.y2030_hi95 - rf.y2030_med) / 10000],
            fmt="o", color=GREEN, capsize=3)
ax.set_yticks(yy, rf.variant, fontsize=8); ax.set_xlabel("万人")
ax.set_title("2030年の年間出生数の予測（95%区間）", fontsize=10)
fig.suptitle("設定を変えた場合（頑健性）", y=1.02)
save(fig, "f55_robust.png")
print("figures done")
