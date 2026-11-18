"""主な分析：H1〜H4 と頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
from common import fe_ols, coef, SEED, REG7, REG_ORDER, SMALL

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
P = pd.read_csv(D / "panel.csv")
T = pd.read_csv(D / "jma_monthly_temp.csv")
P = P[P.pref != "全国"].copy()
ORDER = {p: i for i, p in enumerate(P.pref.unique())}  # panel.csv は北から南の県の順
norm = T[(T.year >= 1991) & (T.year <= 2020)].pivot_table(index="pref", columns="month", values="temp", aggfunc="mean")
P["n_aug"] = P.pref.map(norm[8]); P["n_julaug"] = P.pref.map((norm[7] + norm[8]) / 2); P["n_augsep"] = P.pref.map((norm[8] + norm[9]) / 2)
P["a_aug"] = P.t_aug - P.n_aug; P["a_julaug"] = P.t_julaug - P.n_julaug; P["a_augsep"] = P.t_augsep - P.n_augsep
P["reg7"] = P.region.map(REG7)
P = P.sort_values(["year", "pref"]).reset_index(drop=True)
MAIN = P[~P.pref.isin(SMALL)].copy()
assert MAIN.pref.nunique() == 41
M = {"n_pref_main": int(MAIN.pref.nunique()), "years": [int(P.year.min()), int(P.year.max())]}

# H1：M1
r = fe_ols(MAIN, ["a_aug"]); h1 = coef(r, "a_aug")
r_p = fe_ols(MAIN, ["a_aug"], cluster="pref"); h1["se_pref"] = coef(r_p, "a_aug")["se"]
h1["lo_pref"] = h1["b"] - 1.96 * h1["se_pref"]; h1["hi_pref"] = h1["b"] + 1.96 * h1["se_pref"]
h1["trend"] = float(r.params["trend"])
M["H1"] = h1
M["H1_verdict"] = "支持" if (h1["b"] <= -3 and h1["hi"] < 0) else "外れ"

# H2：区間（実の気温）と折れ線
bins = [-np.inf, 25, 26, 27, 28, 29, np.inf]
labs = ["25℃未満", "25〜26℃", "26〜27℃", "27〜28℃", "28〜29℃", "29℃以上"]
MAIN["tbin"] = pd.cut(MAIN.t_aug, bins=bins, labels=labs, right=False)
for i, l in enumerate(labs):
    MAIN[f"bin{i}"] = (MAIN.tbin == l).astype(float)
bcols = [f"bin{i}" for i in range(6) if i != 2]
rb = fe_ols(MAIN, bcols)
binrows = []
for i, l in enumerate(labs):
    n = int((MAIN.tbin == l).sum())
    if i == 2:
        binrows.append(dict(bin=l, b=0.0, lo=0.0, hi=0.0, n_obs=n, mean_r1=float(MAIN.r1[MAIN.tbin == l].mean())))
    else:
        c = coef(rb, f"bin{i}"); binrows.append(dict(bin=l, b=c["b"], lo=c["lo"], hi=c["hi"], n_obs=n, mean_r1=float(MAIN.r1[MAIN.tbin == l].mean())))
pd.DataFrame(binrows).to_csv(R / "h2_bins.csv", index=False, float_format="%.4f")
K = 27.0
MAIN["t_lo"] = np.minimum(MAIN.t_aug, K) - K; MAIN["t_hi"] = np.maximum(MAIN.t_aug - K, 0)
rk = fe_ols(MAIN, ["t_lo", "t_hi"])
lo, hi = coef(rk, "t_lo"), coef(rk, "t_hi")
dd = MAIN.reset_index(drop=True)
M["H2"] = {"knot": K, "slope_below": lo, "slope_above": hi, "ratio_above_below": hi["b"] / lo["b"] if lo["b"] != 0 else None,
           "share_obs_above": float((MAIN.t_aug >= K).mean())}
M["H2_verdict"] = "支持" if (hi["b"] < 0 and lo["b"] < 0 and hi["b"] <= 2 * lo["b"]) else "外れ"
# 折れ点を 26〜28℃ で動かしたとき（頑健性の参考）
kn = []
for k in [26.0, 26.5, 27.0, 27.5, 28.0]:
    MAIN["tl"] = np.minimum(MAIN.t_aug, k) - k; MAIN["th"] = np.maximum(MAIN.t_aug - k, 0)
    rr = fe_ols(MAIN, ["tl", "th"])
    kn.append(dict(knot=k, below=float(rr.params["tl"]), above=float(rr.params["th"]), share_above=float((MAIN.t_aug >= k).mean())))
pd.DataFrame(kn).to_csv(R / "h2_knots.csv", index=False, float_format="%.4f")

# H3：前後に分ける
E = MAIN[MAIN.year <= 2014]; L = MAIN[MAIN.year >= 2015]
be = coef(fe_ols(E, ["a_aug"]), "a_aug"); bl = coef(fe_ols(L, ["a_aug"]), "a_aug")
rng = np.random.default_rng(SEED)
prefs = np.array(sorted(MAIN.pref.unique()))
G = {p: g for p, g in MAIN.groupby("pref", sort=True)}


def slope(d):
    # 県の平均と県ごとの直線の年を除いたあとの傾き（固定効果＋年の直線と同じ）
    d = d.copy()
    for c in ["r1", "a_aug"]:
        d[c] = d[c] - d.groupby("pref")[c].transform("mean")
    t = d.year - d.year.mean()
    X = np.column_stack([d.a_aug.values, t.values])
    return np.linalg.lstsq(X, d.r1.values, rcond=None)[0][0]


diffs = []
for _ in range(2000):
    s = rng.choice(prefs, size=len(prefs), replace=True)
    d = pd.concat([G[p].assign(pref=f"{p}_{i}") for i, p in enumerate(s)], ignore_index=True)
    diffs.append(slope(d[d.year >= 2015]) - slope(d[d.year <= 2014]))
diffs = np.array(diffs)
M["H3"] = {"early": be, "late": bl, "shrink": 1 - bl["b"] / be["b"], "diff_late_minus_early": bl["b"] - be["b"],
           "boot_lo": float(np.quantile(diffs, 0.025)), "boot_hi": float(np.quantile(diffs, 0.975)), "n_boot": 2000,
           "check_slope_early": float(slope(E)), "check_slope_late": float(slope(L))}
v = "支持" if (abs(bl["b"]) <= 0.7 * abs(be["b"])) else "外れ"
if v == "支持" and M["H3"]["boot_lo"] <= 0 <= M["H3"]["boot_hi"]:
    v = "支持（ただし差の区間は0をまたぐ）"
M["H3_verdict"] = v
# 2010年と2023年の比較（同じくらい暑い年）
yy = []
for y in [2010, 2023]:
    d = MAIN[MAIN.year == y]
    yy.append(dict(year=y, mean_a_aug=float(d.a_aug.mean()), mean_t_aug=float(d.t_aug.mean()), national_r1=float(P[P.year == y].q1.sum() / P[P.year == y].total.sum() * 100)))
M["hot_years"] = yy

# H4：地方別
rows = []
for g in REG_ORDER:
    d = MAIN[MAIN.reg7 == g]
    c = coef(fe_ols(d, ["a_aug"]), "a_aug")
    rows.append(dict(region=g, n_pref=int(d.pref.nunique()), prefs="・".join(pd.unique(d.sort_values("pref", key=lambda s: s.map(ORDER)).pref)),
                     b=c["b"], lo=c["lo"], hi=c["hi"], mean_t_aug=float(d.t_aug.mean()), mean_r1=float(d.r1.mean())))
reg = pd.DataFrame(rows)
reg.to_csv(R / "h4_regions.csv", index=False, float_format="%.4f")
M["H4"] = reg[["region", "b", "lo", "hi"]].to_dict("records")
M["H4_verdict"] = "支持" if (reg.b < 0).all() else "外れ"

# 頑健性
rob = [dict(name="主（8月の偏差、41道府県、重みなし、年の直線）", **coef(r, "a_aug"))]
rob.append(dict(name="気温を7〜8月の平均に", **coef(fe_ols(MAIN, ["a_julaug"]), "a_julaug")))
rob.append(dict(name="気温を8〜9月の平均に", **coef(fe_ols(MAIN, ["a_augsep"]), "a_augsep")))
rob.append(dict(name="47都道府県すべて", **coef(fe_ols(P, ["a_aug"]), "a_aug")))
rob.append(dict(name="検査数量で重み", **coef(fe_ols(MAIN, ["a_aug"], weights="total"), "a_aug")))
rob.append(dict(name="2010年と2023年を除く", **coef(fe_ols(MAIN[~MAIN.year.isin([2010, 2023])], ["a_aug"]), "a_aug")))
rob.append(dict(name="年の固定効果（同じ年の県の間の差だけ）", **coef(fe_ols(MAIN, ["a_aug"], year_fe=True, cluster="pref"), "a_aug")))
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False, float_format="%.4f")
M["robustness"] = rob[["name", "b", "lo", "hi", "n"]].to_dict("records")

# レビューで足した確かめ：年の固定効果（県でクラスター）でも、折れ線（H2）と前後の差（H3）が残るか
MAIN["t_lo"] = np.minimum(MAIN.t_aug, K) - K; MAIN["t_hi"] = np.maximum(MAIN.t_aug - K, 0)
rk_fe = fe_ols(MAIN, ["t_lo", "t_hi"], year_fe=True, cluster="pref")
M["review_yearfe"] = {"H2_slope_below": coef(rk_fe, "t_lo"), "H2_slope_above": coef(rk_fe, "t_hi"),
                      "H3_early": coef(fe_ols(E, ["a_aug"], year_fe=True, cluster="pref"), "a_aug"),
                      "H3_late": coef(fe_ols(L, ["a_aug"], year_fe=True, cluster="pref"), "a_aug")}

# 図用：全国の推移と、全国の検査数量で重みをつけた8月の偏差
nat = P.groupby("year", sort=True).apply(lambda d: pd.Series({"r1": d.q1.sum() / d.total.sum() * 100,
                                                              "a_aug_w": np.average(d.a_aug, weights=d.total)}), include_groups=False).reset_index()
nat.to_csv(R / "national_series.csv", index=False, float_format="%.4f")
M["national"] = {int(k): round(float(v), 1) for k, v in nat.set_index("year").r1.items()}
M["corr_national_r1_aaug"] = float(np.corrcoef(nat.r1, nat.a_aug_w)[0, 1])
MAIN[["pref", "region", "reg7", "year", "r1", "t_aug", "a_aug", "total"]].to_csv(R / "panel_main.csv", index=False, float_format="%.4f")
json.dump(M, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: M[k] for k in ["H1", "H1_verdict", "H2", "H2_verdict", "H3", "H3_verdict", "H4_verdict", "hot_years", "corr_national_r1_aaug"]}, ensure_ascii=False, indent=1))
print(reg.to_string()); print(rob.to_string()); print(pd.read_csv(R / "h2_bins.csv").to_string()); print(pd.read_csv(R / "h2_knots.csv").to_string())
