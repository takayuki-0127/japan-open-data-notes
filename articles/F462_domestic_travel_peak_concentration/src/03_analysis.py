"""仮説 H1〜H4 と頑健性。結果は results/main.json と表 CSV に書く。"""
import calendar, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "japanese_stays_monthly.csv")
d["days"] = [calendar.monthrange(y, m)[1] for y, m in zip(d.year, d.month)]
d["per_day"] = d.stays / d.days
EARLY, LATE, PRE = [2012, 2013, 2014], [2023, 2024, 2025], [2017, 2018, 2019]


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def measures(g):
    g = g.sort_values("month")
    tot = g.stays.sum()
    return pd.Series({"aug_share": g.stays.iloc[7] / tot * 100, "decjan_share": (g.stays.iloc[11] + g.stays.iloc[0]) / tot * 100,
                      "may_share": g.stays.iloc[4] / tot * 100, "gini_perday": gini(g.per_day), "gini_raw": gini(g.stays),
                      "cv_perday": g.per_day.std(ddof=0) / g.per_day.mean(), "peak_ratio": g.per_day.max() / g.per_day.mean(),
                      "peak_month": int(g.month.iloc[int(np.argmax(g.per_day.values))]), "total": tot})


M = d.groupby(["code", "pref", "year"]).apply(measures, include_groups=False).reset_index()
M.to_csv(R / "measures_by_pref_year.csv", index=False, float_format="%.4f")
nat = M[M.code == 0].set_index("year")
nat.drop(columns=["code", "pref"]).to_csv(R / "measures_national.csv", float_format="%.4f")
# 全国の月別の割合（期間平均）
sh = d[d.code == 0].copy(); sh["share"] = sh.stays / sh.groupby("year").stays.transform("sum") * 100
msh = pd.DataFrame({"2012-14": sh[sh.year.isin(EARLY)].groupby("month").share.mean(),
                    "2017-19": sh[sh.year.isin(PRE)].groupby("month").share.mean(),
                    "2023-25": sh[sh.year.isin(LATE)].groupby("month").share.mean()})
msh["diff_late_early"] = msh["2023-25"] - msh["2012-14"]
msh.round(3).to_csv(R / "monthly_share_national.csv")


def avg(col, ys, frame=nat):
    return float(frame.loc[ys, col].mean())


def r3(x):
    return round(float(x), 3)


main = {"source": "観光庁「宿泊旅行統計調査」日本人延べ宿泊者数（月別、2011〜2025年）"}
main["monthly_share"] = {int(m): {k: r3(v) for k, v in row.items()} for m, row in msh.iterrows()}
a_e, a_l = avg("aug_share", EARLY), avg("aug_share", LATE)
main["H1"] = {"aug_share_2012_14": r3(a_e), "aug_share_2023_25": r3(a_l), "diff_pt": r3(a_l - a_e), "result": "当たり" if a_l - a_e <= -0.3 else "外れ"}
g_e, g_l = avg("gini_perday", EARLY), avg("gini_perday", LATE)
main["H2"] = {"gini_2012_14": round(g_e, 4), "gini_2023_25": round(g_l, 4), "result": "当たり" if g_l < g_e else "外れ"}
main["decjan"] = {"2012_14": r3(avg("decjan_share", EARLY)), "2017_19": r3(avg("decjan_share", PRE)), "2023_25": r3(avg("decjan_share", LATE))}
main["may"] = {"2012_14": r3(avg("may_share", EARLY)), "2017_19": r3(avg("may_share", PRE)), "2023_25": r3(avg("may_share", LATE))}
main["national_by_year"] = {int(y): {"aug_share": r3(r.aug_share), "gini_perday": round(float(r.gini_perday), 4), "peak_month": int(r.peak_month),
                                     "total_million": round(float(r.total) / 1e6, 2)} for y, r in nat.iterrows()}

# 都道府県
P = M[M.code > 0]
pe = P[P.year.isin(EARLY)].groupby(["code", "pref"])[["aug_share", "gini_perday", "decjan_share"]].mean()
pl = P[P.year.isin(LATE)].groupby(["code", "pref"])[["aug_share", "gini_perday", "decjan_share"]].mean()
pp = pe.join(pl, lsuffix="_early", rsuffix="_late")
pp["aug_diff"] = pp.aug_share_late - pp.aug_share_early
pp["gini_diff"] = pp.gini_perday_late - pp.gini_perday_early
pp.round(4).to_csv(R / "pref_change.csv")
n_down = int((pp.aug_diff < 0).sum())
main["H3"] = {"n_pref_aug_down": n_down, "n_pref_gini_down": int((pp.gini_diff < 0).sum()), "result": "当たり" if n_down >= 24 else "外れ"}
rho = float(pd.Series(pp.aug_share_early.values).rank().corr(pd.Series(pp.aug_diff.values).rank()))
main["H4"] = {"spearman": r3(rho), "result": "当たり" if rho < -0.3 else "外れ"}
main["pref_aug_early_range"] = [r3(pp.aug_share_early.min()), r3(pp.aug_share_early.max())]
main["pref_aug_diff_range"] = [r3(pp.aug_diff.min()), r3(pp.aug_diff.max())]

# 頑健性
rob = {}
yy = np.arange(2012, 2020)
rob["R1_slope_2012_19"] = {"aug_share_pt_per_year": r3(np.polyfit(yy, nat.loc[yy, "aug_share"], 1)[0]),
                           "gini_per_year": round(float(np.polyfit(yy, nat.loc[yy, "gini_perday"], 1)[0]), 5)}
rob["R1_pre_vs_late"] = {"aug_share_2017_19": r3(avg("aug_share", PRE)), "aug_share_2023_25": r3(a_l),
                         "gini_2017_19": round(avg("gini_perday", PRE), 4), "gini_2023_25": round(g_l, 4)}
rob["R2_gini_raw"] = {"2012_14": round(avg("gini_raw", EARLY), 4), "2023_25": round(avg("gini_raw", LATE), 4)}
rob["R3_other_measures"] = {"peak_ratio_2012_14": r3(avg("peak_ratio", EARLY)), "peak_ratio_2023_25": r3(avg("peak_ratio", LATE)),
                            "cv_2012_14": r3(avg("cv_perday", EARLY)), "cv_2023_25": r3(avg("cv_perday", LATE))}
rob["R4_single_year"] = {"aug_share_2012": r3(nat.loc[2012, "aug_share"]), "aug_share_2025": r3(nat.loc[2025, "aug_share"]),
                         "gini_2012": round(float(nat.loc[2012, "gini_perday"]), 4), "gini_2025": round(float(nat.loc[2025, "gini_perday"]), 4)}
# 都道府県：2017〜19年平均でくらべた場合
p17 = P[P.year.isin(PRE)].groupby(["code", "pref"]).aug_share.mean()
rob["R5_pref_vs_2017_19"] = {"n_pref_aug_down": int(((pl.aug_share - p17) < 0).sum())}
main["robustness"] = rob
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print({k: main[k]["result"] for k in ["H1", "H2", "H3", "H4"]})
