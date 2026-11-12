"""289 結婚（婚姻届）が多い月は、変わったのか
人口動態統計 確定数 上巻 9-3「届出月別にみた年次別婚姻件数」（1947〜2025年、2000年以降は毎年）
"""
import calendar
import numpy as np, pandas as pd
from common import rows, num, save_json, savefig, plt, RES

r = rows("jinkou_r7_jokan_9-3_marriage_by_month.csv")
i0 = next(i for i, x in enumerate(r) if x and x[0] == "実数")
i1 = next(i for i, x in enumerate(r) if x and x[0] == "百分率")
cnt = {}
for x in r[i0 + 1:i1]:
    if x and x[0][:4].isdigit():
        cnt[int(x[0][:4])] = [num(v) for v in x[1:14]]
df = pd.DataFrame(cnt, index=["total"] + list(range(1, 13))).T
df.index.name = "year"
assert (df[list(range(1, 13))].sum(axis=1) - df["total"]).abs().max() == 0
M = list(range(1, 13))
share = df[M].div(df["total"], axis=0) * 100

# 1日あたりの件数で見た指数（その年の1日平均＝100）。月の日数の違いを除く
def days(y, m): return calendar.monthrange(y, m)[1]
perday = pd.DataFrame({m: df[m] / [days(y, m) for y in df.index] for m in M})
idx = perday.div(perday.mean(axis=1), axis=0) * 100
idx.round(2).to_csv(RES / "a289_perday_index.csv")
share.round(3).to_csv(RES / "a289_month_share.csv")

# 季節の偏りの大きさ：1日あたり指数の標準偏差・最大と最小の比
conc = pd.DataFrame({"sd_index": idx.std(axis=1, ddof=0), "max_min_ratio": idx.max(axis=1) / idx.min(axis=1),
                     "top_month": idx.idxmax(axis=1), "bottom_month": idx.idxmin(axis=1)})
conc.round(3).to_csv(RES / "a289_concentration.csv")

PER = {"1965-75": [1965, 1970, 1975], "1985-95": [1985, 1990, 1995], "2003-07": list(range(2003, 2008)),
       "2014-18": list(range(2014, 2019)), "2021-25": list(range(2021, 2026))}
prof = pd.DataFrame({k: idx.loc[v].mean() for k, v in PER.items()})
prof.round(2).to_csv(RES / "a289_period_profile.csv")

# 特別に多い月：同じ月の前後3年（自分を除く）の割合の中央値からのずれ
yrs = [y for y in df.index if y >= 2000]
anom = []
for y in yrs:
    nb = [z for z in yrs if z != y and abs(z - y) <= 3]
    for m in M:
        base = share.loc[nb, m].median()
        exc = (share.loc[y, m] - base) / 100 * df.loc[y, "total"]
        anom.append(dict(year=y, month=m, share=share.loc[y, m], base_share=base, diff_pt=share.loc[y, m] - base, excess=exc))
anom = pd.DataFrame(anom).sort_values("diff_pt", ascending=False)
anom.round(3).to_csv(RES / "a289_month_anomaly.csv", index=False)
top = anom.head(10)
# 頑健性：基準を前後3年の平均にしても上位は同じか
alt = sorted(((share.loc[y, m] - share.loc[[z for z in yrs if z != y and abs(z - y) <= 3], m].mean(), y, m) for y in yrs for m in M), reverse=True)[:5]

# 頑健性：月の割合（日数をならさない）でも同じ並びか、2019・2020年を除くと
prof_share = pd.DataFrame({k: share.loc[v].mean() for k, v in PER.items()})
rank_corr = prof["1965-75"].rank().corr(prof["2021-25"].rank())
rank_corr_share = prof_share["1965-75"].rank().corr(prof_share["2021-25"].rank())
corr_2125_0307 = prof["2003-07"].corr(prof["2021-25"])
sd_by_per = {k: float(conc.loc[v, "sd_index"].mean()) for k, v in PER.items()}
excl = [y for y in range(2014, 2026) if y not in (2019, 2020)]
aug = {k: float(prof.loc[8, k]) for k in PER}

out = dict(
    years=[int(df.index.min()), int(df.index.max())], total_2025=df.loc[2025, "total"], total_1970=df.loc[1970, "total"],
    profile_index={k: {int(m): float(prof.loc[m, k]) for m in M} for k in PER},
    profile_share={k: {int(m): float(prof_share.loc[m, k]) for m in M} for k in PER},
    top3={k: [int(m) for m in prof[k].sort_values(ascending=False).index[:3]] for k in PER},
    bottom={k: int(prof[k].idxmin()) for k in PER},
    sd_index_by_period=sd_by_per, august_index=aug,
    rank_corr_1965_75_vs_2021_25=float(rank_corr), rank_corr_share=float(rank_corr_share),
    corr_2003_07_vs_2021_25=float(corr_2125_0307),
    top_anomalies=top.to_dict("records"), top5_mean_based=[dict(year=int(y), month=int(m), diff_pt=float(d)) for d, y, m in alt],
    may2019=dict(count=df.loc[2019, 5], base_share=float(anom.query("year==2019 and month==5").base_share.iloc[0]),
                 excess=float(anom.query("year==2019 and month==5").excess.iloc[0])),
    feb2020=dict(count=df.loc[2020, 2], excess=float(anom.query("year==2020 and month==2").excess.iloc[0])),
    sd_index_2014_25_excl_2019_20=float(conc.loc[excl, "sd_index"].mean()),
    march_top_years_2000_25=int((conc.loc[yrs, "top_month"] == 3).sum()),
    nov_top_years_2000_25=int((conc.loc[yrs, "top_month"] == 11).sum()),
)
save_json(out)

# 図1：期間ごとの月の形（1日あたり指数）
fig, ax = plt.subplots(figsize=(8, 4.3))
sty = {"1965-75": ("#9aa0a6", "--"), "1985-95": ("#5f6368", ":"), "2003-07": ("#7baaf7", "-"), "2021-25": ("#d93025", "-")}
lab = {"1965-75": "1965・70・75年", "1985-95": "1985・90・95年", "2003-07": "2003〜07年", "2021-25": "2021〜25年"}
for k, (c, ls) in sty.items():
    ax.plot(M, prof[k], color=c, ls=ls, marker="o", ms=4, lw=2, label=lab[k])
ax.axhline(100, color="#bbb", lw=0.8)
ax.set_xticks(M); ax.set_xticklabels([f"{m}月" for m in M])
ax.set_ylabel("1日あたりの婚姻届（その年の平均＝100）")
ax.set_title("婚姻届が多い月：春と秋の山から、3月と11月へ")
ax.legend(frameon=False, fontsize=9, ncol=2)
savefig(fig, "a289_profile.png")

# 図2：季節の偏りの大きさ（標準偏差）
fig, ax = plt.subplots(figsize=(8, 3.8))
c2 = conc.copy()
ax.plot(c2.index, c2["sd_index"], color="#1a73e8", marker="o", ms=3, lw=1.5)
for y, dx in ((2019, -34), (2020, 6)):
    ax.annotate(f"{y}年", (y, c2.loc[y, "sd_index"]), textcoords="offset points", xytext=(dx, 4), fontsize=9, color="#d93025")
ax.set_ylabel("月ごとの指数の標準偏差")
ax.set_title("月の偏りは1970年代が最大、2000年代に半分以下、2021年からやや戻る")
ax.set_ylim(0, None)
savefig(fig, "a289_concentration.png")

# 図3：前後の年より多かった月（2000年以降、上位10）
fig, ax = plt.subplots(figsize=(8, 4.2))
t = top.iloc[::-1]
labels = [f"{int(a)}年{int(b)}月" for a, b in zip(t.year, t.month)]
ax.barh(labels, t["diff_pt"], color=["#d93025" if (a, b) in [(2019, 5), (2020, 2)] else "#7baaf7" for a, b in zip(t.year, t.month)])
for yv, (d, e) in enumerate(zip(t["diff_pt"], t["excess"])):
    ax.text(d + 0.1, yv, f"+{d:.1f}ポイント（約{e/10000:.1f}万件）", va="center", fontsize=8.5)
ax.set_xlabel("その月の割合 − 前後3年の同じ月の割合の中央値（ポイント）")
ax.set_xlim(0, t["diff_pt"].max() * 1.45)
ax.set_title("前後の年より婚姻届が多かった月（2000〜2025年、上位10）")
savefig(fig, "a289_anomaly.png")
print(out["top3"], out["sd_index_by_period"], out["may2019"], out["feb2020"])
print(top[["year", "month", "share", "base_share", "diff_pt", "excess"]].round(2).to_string())
