import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy import stats
from common import DATA, RES, FIG

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
BL, OR, GR = "#2b6cb0", "#c05621", "#8a8a8a"
d = pd.read_csv(DATA / "returns_daily.csv", parse_dates=["date"])

# 1) 年ごとの順位相関
yr = pd.read_csv(RES / "yearly_correlation.csv")
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(yr.date, yr.kendall, color=[BL if k > 0 else OR for k in yr.kendall])
ax.axhline(0, color="k", lw=.8)
for a, b in [(1997.5, 2006.5), (2012.5, 2019.5)]: ax.axvspan(a, b, color="#eee", zorder=0)
ax.set_title("円安の日に株高になりやすいか（年ごとの順位相関 ケンドールのτ）", loc="left")
ax.set_ylabel("ケンドールのτ"); ax.set_xlabel("年（2026年は10月まで）")
ax.text(2002, -.16, "1998〜2006：ほぼ無関係", ha="center", fontsize=10); ax.text(2016, -.16, "2013〜2019", ha="center", fontsize=10); ax.set_ylim(-.22, .6)
fig.tight_layout(); fig.savefig(FIG / "f169_yearly.png", dpi=150); plt.close()

# 2) 順位の散布図（コピュラの目盛り）
u = stats.rankdata(d.r_fx) / (len(d) + 1); v = stats.rankdata(d.r_nk) / (len(d) + 1)
fig, axs = plt.subplots(1, 2, figsize=(10, 4.9))
for ax, (lab, a, b) in zip(axs, [("1998〜2006", "1998", "2007"), ("2007〜2026", "2007", "2027")]):
    m = ((d.date >= a) & (d.date < b)).values
    ax.scatter(u[m], v[m], s=2, color=GR, alpha=.35, lw=0)
    hi = m & (u > .9) & (v > .9); lo = m & (u <= .1) & (v <= .1)
    ax.add_patch(plt.Rectangle((.9, .9), .1, .1, color=BL, alpha=.12)); ax.add_patch(plt.Rectangle((0, 0), .1, .1, color=OR, alpha=.12))
    ax.scatter(u[hi], v[hi], s=5, color=BL, label=f"円安・株高とも上位10%：{hi.sum()}日")
    ax.scatter(u[lo], v[lo], s=5, color=OR, label=f"円高・株安とも下位10%：{lo.sum()}日")
    ax.plot([], [], " ", label=f"（無関係なら各 約{m.sum()*0.01:.0f}日）")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_aspect("equal")
    ax.set_xlabel("ドル円の変化の順位（右ほど円安）"); ax.set_ylabel("日経平均の変化の順位（上ほど株高）")
    ax.set_title(f"{lab}（{m.sum():,}日）", loc="left"); ax.legend(loc="upper left", fontsize=8.5, frameon=True)
fig.suptitle("2つの変化を順位に直した散布図：角に点が集まるほど「大きく動く日に一緒に動く」", x=.02, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f169_rank_scatter.png", dpi=150); plt.close()

# 3) 経験的な裾の依存（閾値別）
e = pd.read_csv(RES / "empirical_tail_dependence.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.6)); x = np.arange(len(e)); wd = .26
ax.bar(x - wd, e.upper, wd, color=BL, yerr=[e.upper - e.upper_lo, e.upper_hi - e.upper], capsize=3, label="円安×株高（上の裾）")
ax.bar(x, e.lower, wd, color=OR, yerr=[e.lower - e.lower_lo, e.lower_hi - e.lower], capsize=3, label="円高×株安（下の裾）")
ax.bar(x + wd, e.gauss_mean, wd, color="#cfcfcf", yerr=[np.zeros(len(e)), e.gauss_hi - e.gauss_mean], capsize=3, label="ふつうの相関だけなら（ガウス）")
ax.set_xticks(x, [f"上位・下位{(1-q)*100:g}%\n（各{n}日）" for q, n in zip(e.q, e.days_each)])
ax.set_ylabel("片方が極端な日に、もう片方も極端な割合")
ax.set_title("大きく動く日ほど、ふつうの相関から予想されるより一緒に動く", loc="left"); ax.legend(fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f169_tail_q.png", dpi=150); plt.close()

# 4) 「大きく動いた日だけの相関」の落とし穴
b = pd.read_csv(RES / "big_move_correlation.csv")
lab = ["日経平均が\n大きく動いた日", "ドル円が\n大きく動いた日", "ふつうの日"]
bb = b.iloc[[0, 1, 3]].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8, 4.4)); x = np.arange(3)
ax.bar(x - .18, bb["corr"], .36, color=BL, label="実際の相関")
ax.bar(x + .18, bb.gauss_mean, .36, color="#cfcfcf", yerr=[bb.gauss_mean - bb.gauss_lo, bb.gauss_hi - bb.gauss_mean], capsize=3, label="ふつうの相関だけでも出る値（ガウス）")
for i, r in bb.iterrows(): ax.text(i - .18, r["corr"] + .015, f"{r['corr']:.2f}", ha="center", fontsize=10)
ax.set_xticks(x, lab); ax.set_ylabel("相関係数"); ax.set_ylim(0, .85)
ax.set_title("大きく動いた日だけ選ぶと、相関は「何もなくても」高く出る", loc="left"); ax.legend(fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "f169_bigmove.png", dpi=150); plt.close()

# 5) 期間・日次と週次
r = pd.read_csv(RES / "robustness.csv")
cases = ["日次・1998-2006", "日次・2007-2012", "日次・2013-2019", "日次・2020-2026", "日次・全期間・GARCHで標準化", "週次・全期間", "日次・全期間"]
rr = r.set_index("case").loc[cases]
fig, ax = plt.subplots(figsize=(9, 4.8)); y = np.arange(len(cases))
ax.barh(y + .27, rr["upper_0.95"], .27, color=BL, label="円安×株高（上位5%どうし）")
ax.barh(y, rr["lower_0.95"], .27, color=OR, label="円高×株安（下位5%どうし）")
ax.barh(y - .27, rr["gauss_mean_0.95"], .27, color="#cfcfcf", xerr=[np.zeros(len(cases)), rr["gauss_hi_0.95"] - rr["gauss_mean_0.95"]], capsize=2, label="ふつうの相関だけなら")
ax.set_yticks(y, [c.replace("日次・", "日次 ").replace("週次・", "週次 ").replace("GARCHで標準化", "\n値動きの荒さを調整") for c in cases])
ax.set_xlabel("片方が極端な日に、もう片方も極端な割合")
ax.set_title("期間・単位を変えると：裾の依存がはっきりするのは2007〜2012年", loc="left"); ax.legend(fontsize=8.5, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f169_periods.png", dpi=150); plt.close()
print("ok")
