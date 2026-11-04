import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import RES, FIG, SUMMER, WINTER

for f in fm.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
C_OBS, C_EXP, C_HOT, C_COLD, C_GRAY = "#333333", "#7a7a7a", "#d1495b", "#2e86ab", "#bbbbbb"

q = pd.read_csv(RES / "excess_main.csv")
S = json.load(open(RES / "summary.json"))

# 1) 実際と期待（1日あたり）
q["date"] = pd.to_datetime(dict(year=q.year, month=q.month, day=15))
r = q[q.year >= 2010]
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(r.date, r.deaths / r.days, color=C_OBS, lw=1.4, label="実際の死亡数")
ax.plot(r.date, r["exp"] / r.days, color=C_EXP, lw=1.2, ls="--", label="期待値（2010〜2019年の月の形と傾きをのばしたもの）")
ax.axvspan(pd.Timestamp("2020-01-01"), pd.Timestamp("2025-12-31"), color="#f2f2f2", zorder=0)
ax.text(pd.Timestamp("2020-03-01"), ax.get_ylim()[1] * 0.98 if False else 5200, "2020年以降は学習に使っていない", fontsize=9, color="#666")
ax.set_ylabel("1日あたりの死亡数（人）")
ax.set_title("全国の死亡数（月ごと・1日あたり）と期待値")
ax.legend(loc="upper left", fontsize=9, frameon=False)
ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "f190_observed_expected.png", dpi=150); plt.close(fig)

# 2) 気温差と「実際÷期待」（夏・冬）
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, s, col, ttl in [(axs[0], "summer", C_HOT, "夏（6〜9月）"), (axs[1], "winter", C_COLD, "冬（12〜3月）")]:
    a = q[(q.season == s) & q.year.between(2010, 2019) & ~((q.year == 2011) & (q.month == 3))]
    b = q[(q.season == s) & (q.year >= 2020)]
    ax.scatter(b.t_anom, 100 * (b.ratio - 1), color=C_GRAY, s=18, label="2020〜2025年（参考）")
    ax.scatter(a.t_anom, 100 * (a.ratio - 1), color=col, s=22, label="2010〜2019年（推定に使用）")
    k = np.log(1 + S["main_relation"][s]["pct_per_1C"] / 100)
    x = np.linspace(a.t_anom.min(), a.t_anom.max(), 50)
    ax.plot(x, 100 * (np.exp(k * x) - 1), color=col, lw=2)
    rr = S["main_relation"][s]
    ax.set_title(f"{ttl}：1℃高いと {rr['pct_per_1C']:+.1f}%（95%区間 {rr['lo']:+.1f}〜{rr['hi']:+.1f}%）", fontsize=10)
    ax.axhline(0, color="#999", lw=0.8); ax.axvline(0, color="#999", lw=0.8)
    ax.set_xlabel("その月の気温の平年差（℃、人口で重みづけ）")
    ax.grid(alpha=0.3)
axs[0].set_ylabel("実際の死亡数÷期待値 −1（%）")
axs[0].legend(fontsize=8, frameon=False, loc="upper left")
fig.suptitle("暑い夏の月はわずかに多く、寒い冬の月ははっきり多い", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f190_temp_ratio.png", dpi=150); plt.close(fig)

# 3) 季節ごとの超過と、気温で説明できる分
a = pd.read_csv(RES / "season_excess.csv")
fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, s, col, ttl in [(axs[0], "summer", C_HOT, "夏（6〜9月）"), (axs[1], "winter", C_COLD, "冬（12〜3月、12月は翌年側）")]:
    b = a[(a.season == s) & (a.sy >= 2010)]
    ax.bar(b.sy, b.excess / 1000, color=C_GRAY, label="超過死亡（実際−期待）")
    ax.scatter(b.sy, b.temp_part / 1000, color=col, s=26, zorder=3, label="うち気温の平年差で説明できる分")
    ax.axhline(0, color="#666", lw=0.8); ax.axvline(2019.5, color="#999", ls=":", lw=1)
    ax.set_title(ttl, fontsize=10); ax.grid(alpha=0.3, axis="y")
axs[0].set_ylabel("千人"); axs[0].legend(fontsize=8, frameon=False, loc="upper left")
fig.suptitle("2020年以降の大きな超過のうち、気温で説明できるのはごく一部", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f190_season_excess.png", dpi=150); plt.close(fig)

# 4) 頑健性（48通り）
rb = pd.read_csv(RES / "robustness.csv")
lab = {"t_anom": "平均気温（人口重み）", "tx_anom": "最高気温の平均", "tn_anom": "最低気温の平均",
       "t_unw_anom": "平均気温（47地点の単純平均）", "t_tokyo_anom": "東京だけ", "anom15": "15地点の平年差（気象庁）"}
fig, axs = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
ys = list(lab)
for ax, col, cc, ttl in [(axs[0], "summer", C_HOT, "夏：1℃あたり（%）"), (axs[1], "winter", C_COLD, "冬：1℃あたり（%）")]:
    for i, t in enumerate(ys):
        b = rb[rb.temp == t]
        sig = b[col + "_p"] < 0.05
        ax.scatter(b[col][sig], [i] * sig.sum(), color=cc, s=26)
        ax.scatter(b[col][~sig], [i] * (~sig).sum(), facecolor="white", edgecolor=cc, s=26)
    ax.axvline(0, color="#666", lw=0.8); ax.set_title(ttl, fontsize=10); ax.grid(alpha=0.3, axis="x")
axs[0].set_yticks(range(len(ys))); axs[0].set_yticklabels([lab[t] for t in ys], fontsize=9)
fig.suptitle("学習期間4通り×傾き2通り×気温の指標6通り（塗り＝p<0.05、白抜き＝はっきりしない）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f190_robustness.png", dpi=150); plt.close(fig)

# 5) コロナ期の扱い
cv = S["covid_handling"]
fig, ax = plt.subplots(figsize=(8, 3.8))
labs = list(cv)
for j, (k, col, nm) in enumerate([("heat", C_HOT, "夏の暑さ（1℃高いと）"), ("cold", C_COLD, "冬の暖かさ（1℃高いと）")]):
    vals = [cv[l][k][0] for l in labs]; ps = [cv[l][k][1] for l in labs]
    y = np.arange(len(labs)) + (j - 0.5) * 0.3
    ax.barh(y, vals, height=0.28, color=[col if pp < 0.05 else "white" for pp in ps], edgecolor=col, label=nm)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(["2010〜2019年", "2010〜2025年（年ごとの水準を別に）", "2020〜2025年だけ（同）"], fontsize=9)
ax.axvline(0, color="#666", lw=0.8); ax.set_xlabel("その月の死亡数の変化（%、塗り＝p<0.05）")
ax.legend(fontsize=9, frameon=False, loc="upper right"); ax.grid(alpha=0.3, axis="x")
ax.set_title("コロナ期を入れると、夏の暑さの効きは見えなくなる", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f190_covid_handling.png", dpi=150); plt.close(fig)

# 季節の形（文中用）
pre = q[q.year.between(2010, 2019)]
pm = (pre.deaths / pre.days).groupby(pre.month).mean()
json.dump({"jan_vs_aug": float(pm[1] / pm[8]), "max_month": int(pm.idxmax()), "min_month": int(pm.idxmin()),
           "min_ratio": float(pm.max() / pm.min())}, open(RES / "seasonality.json", "w"))
print(pm.round(0).to_dict(), pm[1] / pm[8])
