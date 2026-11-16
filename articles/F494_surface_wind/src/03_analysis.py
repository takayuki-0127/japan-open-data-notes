"""PLAN の仮説 H1〜H5 と頑健性を計算し、results/ に書く。"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)
d = pd.read_csv(os.path.join(DATA, "annual_wind.csv"))
GROUPS = {"rural": "15地点", "city": "大都市", "cold": "寒い地域"}
MINSEG = 5
r3 = lambda x: float(round(float(x), 3))


def naive_slope(g, var):
    z = g[["year", var]].dropna()
    return stats.theilslopes(z[var], z["year"])[0] * 10


def ols_slope(g, var):
    z = g[["year", var]].dropna()
    return np.polyfit(z["year"], z[var], 1)[0] * 10


def fe_slope(g, var, seg):
    """区間ごとの定数＋共通の傾き（最小二乗法）。短い区間（5年未満）は除く。10年あたり。"""
    z = g[["year", var, seg]].dropna()
    cnt = z[seg].value_counts()
    z = z[z[seg].map(cnt) >= MINSEG]
    if z[seg].nunique() == 0 or len(z) < 10:
        return np.nan, 0
    D = pd.get_dummies(z[seg], prefix="s").astype(float).values
    X = np.column_stack([z["year"].values - 1990.0, D])
    beta, *_ = np.linalg.lstsq(X, z[var].values, rcond=None)
    return beta[0] * 10, int(z[seg].nunique())


def longest_seg_slope(g, var, seg):
    z = g[["year", var, seg]].dropna()
    k = z[seg].value_counts().idxmax()
    zz = z[z[seg] == k]
    return stats.theilslopes(zz[var], zz["year"])[0] * 10, int(len(zz))


rows = []
for (stn, grp), g in d.groupby(["station", "group"], sort=False):
    fe, nseg = fe_slope(g, "wind_mean", "seg_mean")
    fe10, _ = fe_slope(g, "days_ge10", "seg_d10")
    fe81, _ = fe_slope(g[g.year >= 1981], "wind_mean", "seg_mean")
    ls, ln = longest_seg_slope(g, "wind_mean", "seg_mean")
    mean_w = g["wind_mean"].mean()
    # 切れ目での段差：切れ目の前5年と後5年の平均の差（同じ区間の中だけ）
    steps = []
    for y in g.loc[g.break_mean == 1, "year"]:
        pre = g[(g.year >= y - 5) & (g.year < y)]
        post = g[(g.year >= y) & (g.year < y + 5)]
        pre = pre[pre.seg_mean == pre.seg_mean.max()] if len(pre) else pre
        post = post[post.seg_mean == post.seg_mean.min()] if len(post) else post
        if len(pre) >= 3 and len(post) >= 3:
            steps.append({"station": stn, "group": grp, "year": int(y),
                          "step": float(post["wind_mean"].mean() - pre["wind_mean"].mean())})
    rows.append({"station": stn, "group": grp, "n_years": int(g["wind_mean"].notna().sum()),
                 "n_breaks": int(g["break_mean"].sum()), "mean_wind": mean_w,
                 "wind_1961_1970": g.loc[g.year <= 1970, "wind_mean"].mean(),
                 "wind_2016_2025": g.loc[g.year >= 2016, "wind_mean"].mean(),
                 "naive": naive_slope(g, "wind_mean"), "naive_ols": ols_slope(g, "wind_mean"), "fe": fe, "fe_nseg": nseg,
                 "naive_81": naive_slope(g[g.year >= 1981], "wind_mean"), "fe_81": fe81,
                 "longest_seg": ls, "longest_seg_years": ln,
                 "naive_d10": naive_slope(g, "days_ge10"), "fe_d10": fe10,
                 "d10_1961_1970": g.loc[g.year <= 1970, "days_ge10"].mean(),
                 "d10_2016_2025": g.loc[g.year >= 2016, "days_ge10"].mean(),
                 "steps": steps})
T = pd.DataFrame(rows)
T["fe_pct"] = T["fe"] / T["mean_wind"] * 100
T["naive_pct"] = T["naive"] / T["mean_wind"] * 100
ST = pd.DataFrame([s for r in rows for s in r["steps"]])
T.drop(columns="steps").round(4).to_csv(os.path.join(RES, "station_table.csv"), index=False)
ST.round(3).to_csv(os.path.join(RES, "steps.csv"), index=False)


def signtest(x):
    x = np.asarray(x)[~np.isnan(x)]
    neg, pos = int((x < 0).sum()), int((x > 0).sum())
    return neg, pos, float(stats.binomtest(neg, neg + pos, 0.5).pvalue)


R = {"n_stations": int(len(T))}
R["H1"] = {"naive_median": r3(T["naive"].median()), "threshold": -0.05,
           "n_negative": int((T["naive"] < 0).sum()),
           "result": "支持" if T["naive"].median() <= -0.05 else "外れ",
           "mean_1961_1970_median": r3(T["wind_1961_1970"].median()), "mean_2016_2025_median": r3(T["wind_2016_2025"].median())}
R["H2"] = {"naive_median": r3(T["naive"].median()), "fe_median": r3(T["fe"].median()),
           "result": "支持" if abs(T["fe"].median()) < abs(T["naive"].median()) else "外れ",
           "naive_ols_median": r3(T["naive_ols"].median())}
neg, pos, p = signtest(T["fe"])
R["H3"] = {"neg": neg, "pos": pos, "p": r3(p), "result": "支持" if (neg > pos and p < 0.05) else "外れ"}
gm = T.groupby("group")[["naive", "fe", "fe_pct", "naive_pct", "fe_d10", "naive_d10"]].median()
R["by_group"] = {GROUPS[k]: {c: r3(v) for c, v in row.items()} for k, row in gm.iterrows()}
R["by_group_n"] = {GROUPS[k]: int(v) for k, v in T.groupby("group").size().items()}
diff = gm.loc["city", "fe"] - gm.loc["rural", "fe"]
mw = stats.mannwhitneyu(T.loc[T.group == "city", "fe"], T.loc[T.group == "rural", "fe"])
R["H4"] = {"city_fe_median": r3(gm.loc["city", "fe"]), "rural_fe_median": r3(gm.loc["rural", "fe"]),
           "diff": r3(diff), "threshold": -0.03, "mannwhitney_p": r3(mw.pvalue),
           "result": "支持" if diff <= -0.03 else "外れ"}
n10, p10, pp10 = signtest(T["fe_d10"])
R["H5"] = {"fe_d10_median": r3(T["fe_d10"].median()), "naive_d10_median": r3(T["naive_d10"].median()),
           "neg": n10, "pos": p10, "p": r3(pp10), "result": "支持" if T["fe_d10"].median() < 0 else "外れ",
           "d10_1961_1970_median": r3(T["d10_1961_1970"].median()), "d10_2016_2025_median": r3(T["d10_2016_2025"].median())}

# 頑健性
rob = []
def add(label, col, mask=None):
    x = T[col] if mask is None else T.loc[mask, col]
    ng, ps, pv = signtest(x)
    rob.append({"check": label, "n": int(x.notna().sum()), "median": r3(x.median()), "neg": ng, "pos": ps, "sign_p": r3(pv)})
add("そのまま（Theil–Sen、1961〜2025年）", "naive")
add("そのまま（最小二乗法）", "naive_ols")
add("段差を許した傾き（本線）", "fe")
add("1981〜2025年：そのまま", "naive_81")
add("1981〜2025年：段差を許す", "fe_81")
add("いちばん長い区間だけ（Theil–Sen）", "longest_seg")
add("切れ目が3つ以下の地点だけ：段差を許す", "fe", T["n_breaks"] <= 3)
add("%/10年：そのまま", "naive_pct")
add("%/10年：段差を許す", "fe_pct")
rb = pd.DataFrame(rob)
rb.to_csv(os.path.join(RES, "robustness.csv"), index=False)
R["robust"] = rob
R["breaks_total"] = int(T["n_breaks"].sum())
R["breaks_median_per_station"] = r3(T["n_breaks"].median())

with open(os.path.join(RES, "main.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: v for k, v in R.items() if k != "robust"}, ensure_ascii=False, indent=1))
print(rb.to_string())
print(T[["station", "group", "n_breaks", "naive", "fe", "longest_seg", "fe_d10"]].round(3).to_string())
