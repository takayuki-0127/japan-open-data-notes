"""全国の定点当たり報告数の週ごとの動き（2023年第1週〜2026年第41週）：流行の山の時期と高さ、2025年の定点の見直し"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from common import *

t = load_teiten()
nat = t[t.pref == "総数"].copy()
nat["sentinels"] = nat.n / nat.per
DIS = ["インフルエンザ", "ＲＳウイルス感染症", "Ａ群溶血性レンサ球菌咽頭炎", "マイコプラズマ肺炎", "伝染性紅斑",
       "手足口病", "ヘルパンギーナ", "咽頭結膜熱", "感染性胃腸炎"]
WINTER = {"インフルエンザ", "感染性胃腸炎"}  # 9月〜翌8月をひとつのシーズンにする

# 定点数（報告数÷定点当たり）の変化
sen = nat[nat.disease.isin(DIS + ["COVID-19"])].copy()
sen["period"] = np.where((sen.year > 2025) | ((sen.year == 2025) & (sen.week >= 15)), "2025年第15週以降", "それより前")
S = sen.groupby(["disease", "period"]).sentinels.median().unstack().round(0)
S.to_csv(RES / "i1_sentinels.csv", encoding="utf-8-sig"); print(S)

# シーズンごとの山
rows = []
for d in DIS:
    x = nat[nat.disease == d].copy()
    if d in WINTER:
        x["season"] = np.where(x.week >= 36, x.year.astype(str) + "/" + (x.year + 1).astype(str).str[2:], (x.year - 1).astype(str) + "/" + x.year.astype(str).str[2:])
    else:
        x["season"] = x.year.astype(str)
    for s, g in x.groupby("season"):
        i = g.per.idxmax()
        rows.append({"disease": d, "season": s, "weeks": len(g), "peak_per": g.per.max(), "peak_year": int(g.loc[i, "year"]), "peak_week": int(g.loc[i, "week"]),
                     "peak_start": g.loc[i, "start"].date(), "total_reports": g.n.sum(), "weeks_over_1": int((g.per >= 1).sum())})
P = pd.DataFrame(rows); P.to_csv(RES / "i1_peaks.csv", index=False, encoding="utf-8-sig"); print(P.to_string())

# 期間全体で最も高かった週
top = nat[nat.disease.isin(DIS)].sort_values("per", ascending=False).groupby("disease").head(1)[["disease", "year", "week", "start", "per"]]
top.to_csv(RES / "i1_max_week.csv", index=False, encoding="utf-8-sig")

# 図1：9疾患の週ごとの推移
fig, axes = plt.subplots(3, 3, figsize=(12, 8.2), sharex=True)
for ax, d in zip(axes.flat, DIS):
    x = nat[nat.disease == d].sort_values("start")
    ax.plot(x.start, x.per, color=BLUE, lw=1.4)
    ax.axvline(pd.Timestamp("2025-04-07"), color=GRAY, ls=":", lw=1)
    i = x.per.idxmax(); ax.plot(x.loc[i, "start"], x.loc[i, "per"], "o", color=ORANGE, ms=4)
    ax.text(x.loc[i, "start"], x.loc[i, "per"], f" {x.loc[i, 'per']:.1f}\n {int(x.loc[i, 'year'])}年{int(x.loc[i, 'week'])}週", fontsize=7.5, color=ORANGE, va="top", bbox=dict(facecolor="white", edgecolor="none", alpha=.8, pad=0.5))
    ax.set_title(SHORT.get(d, d), loc="left", fontsize=11); ax.set_ylim(0, x.per.max() * 1.25)
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
for ax in axes[:, 0]: ax.set_ylabel("定点当たり報告数")
fig.suptitle("定点当たり報告数の週ごとの推移（全国、2023年第1週〜2026年第41週。点線は2025年第15週の定点の見直し）", x=.02, ha="left", y=1.0, fontsize=12)
note(axes[2, 0], SOURCE + "　速報値", -0.32)
fig.tight_layout(); fig.savefig(FIG / "i1_weekly.png"); plt.close(fig)

# 図2：シーズンごとの山の高さ（季節の型の比較）
fig, ax = plt.subplots(figsize=(10.5, 4.4))
order = DIS
cols = {}
for j, d in enumerate(order):
    g = P[(P.disease == d) & (P.weeks >= 40)].sort_values("season")
    xs = j + np.linspace(-0.3, 0.3, max(len(g), 1))
    for k, (_, r) in enumerate(g.iterrows()):
        ax.bar(xs[k], r.peak_per, 0.6 / max(len(g), 1) * 0.9, color=[LIGHT, BLUE, ORANGE, GREEN][k % 4])
        ax.text(xs[k], r.peak_per, r.season.replace("20", "", 1) if "/" in r.season else r.season[2:], ha="center", va="bottom", fontsize=6.5, rotation=90)
ax.set_yscale("log"); ax.set_xticks(range(len(order))); ax.set_xticklabels([SHORT.get(d, d) for d in order], fontsize=9, rotation=20)
ax.set_ylabel("シーズンの最大の定点当たり報告数（対数目盛）")
ax.set_title("シーズンごとの山の高さ（ほぼ1シーズン分のデータがある年だけ）", loc="left")
note(ax, SOURCE + "\nインフルエンザと感染性胃腸炎は9月〜翌8月、ほかは1〜12月をひとつのシーズンとした。棒の上の数字はシーズン（年）", -0.3)
fig.savefig(FIG / "i1_peaks.png"); plt.close(fig)

# 図3：インフルエンザのシーズンを重ねる（第36週を起点）
fig, ax = plt.subplots(figsize=(9, 4.2))
x = nat[nat.disease == "インフルエンザ"].copy()
x["season"] = np.where(x.week >= 36, x.year, x.year - 1)
x["wk"] = np.where(x.week >= 36, x.week - 36, x.week + 52 - 36)
for s, col in zip([2023, 2024, 2025, 2026], [LIGHT, BLUE, ORANGE, GREEN]):
    g = x[x.season == s].sort_values("wk")
    ax.plot(g.wk, g.per, color=col, lw=2, label=f"{s}/{str(s + 1)[2:]}シーズン")
ticks = [0, 4, 9, 13, 17, 22, 26, 30, 35, 39, 43, 48]
ax.set_xticks(ticks); ax.set_xticklabels(["9月", "10月", "11月", "12月", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月"], fontsize=9)
ax.axhline(1, color=GRAY, lw=.8, ls=":"); ax.axhline(10, color=GRAY, lw=.8, ls="--"); ax.axhline(30, color=GRAY, lw=.8, ls="--")
ax.text(50, 1.2, "1.0", fontsize=8, color=GRAY); ax.text(50, 10.5, "10", fontsize=8, color=GRAY); ax.text(50, 31, "30", fontsize=8, color=GRAY)
ax.set_ylabel("定点当たり報告数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("インフルエンザのシーズンの重ね合わせ（全国）", loc="left")
note(ax, SOURCE + "\n2025年第15週から定点が見直されている（2025/26シーズン以降は定点の数と顔ぶれが違う）", -0.14)
fig.savefig(FIG / "i1_flu_seasons.png"); plt.close(fig)
