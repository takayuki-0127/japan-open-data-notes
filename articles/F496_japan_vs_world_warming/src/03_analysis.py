"""上昇率・倍率・仮説・頑健性。乱数は使わない。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import theilslopes

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
A = pd.read_csv(ROOT / "data" / "annual.csv")
A = A[A.year <= 2025].reset_index(drop=True)
PUB = json.load(open(ROOT / "data" / "published.json", encoding="utf-8"))
OCEAN = 0.71


def land(df, f=OCEAN):
    return (df.world - f * df.sst) / (1 - f)


A["land_est"] = land(A)


def slope(df, col, y0, y1, method="ols"):
    d = df[df.year.between(y0, y1)].dropna(subset=[col])
    x = d.year.values.astype(float); y = d[col].values
    if method == "ts":
        return float(theilslopes(y, x)[0] * 100)
    return float(np.polyfit(x, y, 1)[0] * 100)


def hac_slope(df, col, y0, y1, lags=3):
    d = df[df.year.between(y0, y1)].dropna(subset=[col])
    X = sm.add_constant(d.year.values.astype(float))
    m = sm.OLS(d[col].values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    b, se = m.params[1] * 100, m.bse[1] * 100
    return float(b), float(b - 1.645 * se), float(b + 1.645 * se)


A["diff_jw"] = A.japan - A.world
A["diff_jl"] = A.japan - A.land_est
main = {}
# 公表値の再現
main["rep_japan_1898_2025"] = round(slope(A, "japan", 1898, 2025), 3)
main["rep_world_1891_2025"] = round(slope(A, "world", 1891, 2025), 3)
main["pub"] = PUB
main["land_est_1891_2025"] = round(slope(A, "land_est", 1891, 2025), 3)
main["ratio_pub_japan_to_pub_land"] = round(PUB["japan"] / PUB["world_land"], 3)
main["ocean_weight_implied_by_pub_land"] = round((PUB["world_land"] - slope(A, "world", 1891, 2025)) / (PUB["world_land"] - slope(A, "sst", 1891, 2025)), 3)
main["sst_1891_2025"] = round(slope(A, "sst", 1891, 2025), 3)
# 同じ期間
Y0, Y1 = 1898, 2025
for c in ["japan", "world", "nh", "sh", "sst", "land_est"]:
    main[f"{c}_{Y0}_{Y1}"] = round(slope(A, c, Y0, Y1), 3)
main["ratio_world"] = round(main["japan_1898_2025"] / main["world_1898_2025"], 3)
main["ratio_land"] = round(main["japan_1898_2025"] / main["land_est_1898_2025"], 3)
main["ratio_nh"] = round(main["japan_1898_2025"] / main["nh_1898_2025"], 3)
b, lo, hi = hac_slope(A, "diff_jw", Y0, Y1); main["diff_jw"] = {"slope": round(b, 3), "lo90": round(lo, 3), "hi90": round(hi, 3)}
b, lo, hi = hac_slope(A, "diff_jl", Y0, Y1); main["diff_jl"] = {"slope": round(b, 3), "lo90": round(lo, 3), "hi90": round(hi, 3)}
d = A[A.year.between(Y0, Y1)]
beta = sm.OLS(d.japan.values, sm.add_constant(d.world.values)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
main["beta_japan_on_world"] = round(float(beta.params[1]), 3); main["beta_se"] = round(float(beta.bse[1]), 3)
# ぶれの大きさ（直線を除いた残りの標準偏差）
for c in ["japan", "world", "land_est"]:
    x = d.year.values.astype(float); y = d[c].values; p = np.polyfit(x, y, 1)
    main[f"resid_sd_{c}"] = round(float(np.std(y - np.polyval(p, x), ddof=2)), 3)

# 始まりの年ごと（終わりは2025年）
rows = []
for y0 in range(1898, 1996):
    rows.append({"start": y0, "japan": slope(A, "japan", y0, 2025), "world": slope(A, "world", y0, 2025),
                 "land_est": slope(A, "land_est", y0, 2025), "nh": slope(A, "nh", y0, 2025)})
S = pd.DataFrame(rows); S["ratio_world"] = S.japan / S.world; S["ratio_land"] = S.japan / S.land_est
S.round(4).to_csv(R / "start_year_scan.csv", index=False)
S90 = S[S.start <= 1990]
main["scan_min_ratio_world"] = round(float(S90.ratio_world.min()), 3); main["scan_max_ratio_world"] = round(float(S90.ratio_world.max()), 3)
main["scan_min_ratio_land"] = round(float(S90.ratio_land.min()), 3); main["scan_max_ratio_land"] = round(float(S90.ratio_land.max()), 3)
main["scan_n_japan_le_world"] = int((S90.japan <= S90.world).sum())
main["scan_n_japan_le_land"] = int((S90.japan <= S90.land_est).sum())
# 30年ごとの期間
W = []
for y0 in range(1898, 1997):
    b, lo, hi = hac_slope(A, "diff_jw", y0, y0 + 29)
    W.append({"start": y0, "end": y0 + 29, "japan": slope(A, "japan", y0, y0 + 29), "world": slope(A, "world", y0, y0 + 29),
              "diff": b, "lo90": lo, "hi90": hi, "cross0": bool(lo <= 0 <= hi)})
W = pd.DataFrame(W); W.round(4).to_csv(R / "window30.csv", index=False)
main["win30_n"] = int(len(W)); main["win30_cross0"] = int(W.cross0.sum()); main["win30_share_cross0"] = round(float(W.cross0.mean()), 3)
main["win30_n_diff_neg"] = int((W["diff"] < 0).sum())
# 例：最近の30年
r = W[W.start == 1996].iloc[0]
main["last30"] = {"japan": round(r.japan, 3), "world": round(r.world, 3), "diff": round(r["diff"], 3), "lo90": round(r.lo90, 3), "hi90": round(r.hi90, 3)}

main["hypotheses"] = {
    "H1": {"rule": "1898〜2025年で日本は世界の1.5倍以上", "value": main["ratio_world"], "verdict": "支持" if main["ratio_world"] >= 1.5 else "外れ"},
    "H2": {"rule": "世界の陸（逆算）と比べると1.3倍未満", "value": main["ratio_land"],
           "verdict": ("判定できず" if abs(main["land_est_1891_2025"] - PUB["world_land"]) > 0.1 else ("支持" if main["ratio_land"] < 1.3 else "外れ")),
           "check": "逆算した陸（1891〜2025年）と気象庁の公表値（陸上のみ、1880〜2025年）の差が0.1℃/100年を超えたら、近似が確かでないとして判定しない"},
    "H3": {"rule": "始まり1898〜1990年のどれでも日本＞世界", "value": main["scan_n_japan_le_world"], "verdict": "支持" if main["scan_n_japan_le_world"] == 0 else "外れ"},
    "H4": {"rule": "30年の期間の半分以上で差の90%区間が0をまたぐ", "value": main["win30_share_cross0"], "verdict": "支持" if main["win30_share_cross0"] >= 0.5 else "外れ"},
}

# 頑健性
rob = []
def add(name, j, w, l, extra=""):
    rob.append({"check": name, "japan": round(j, 3), "world": round(w, 3), "land_est": round(l, 3) if l == l else np.nan,
                "ratio_world": round(j / w, 3), "ratio_land": round(j / l, 3) if l == l else np.nan, "note": extra})
add("本線：1898〜2025年、最小二乗法", main["japan_1898_2025"], main["world_1898_2025"], main["land_est_1898_2025"])
add("Theil–Sen", slope(A, "japan", Y0, Y1, "ts"), slope(A, "world", Y0, Y1, "ts"), slope(A, "land_est", Y0, Y1, "ts"))
add("終わりを2022年", slope(A, "japan", Y0, 2022), slope(A, "world", Y0, 2022), slope(A, "land_est", Y0, 2022))
add("相手を北半球", main["japan_1898_2025"], main["nh_1898_2025"], np.nan, "ratio_world の列は北半球に対する倍率")
for f in [0.65, 0.75]:
    A[f"land_{f}"] = land(A, f)
    add(f"海の割合 {f}", main["japan_1898_2025"], main["world_1898_2025"], slope(A, f"land_{f}", Y0, Y1))
add("回帰の傾き（日本の偏差を世界の偏差で回帰）", main["beta_japan_on_world"], 1.0, np.nan, "ratio_world の列は回帰の傾き")
RB = pd.DataFrame(rob); RB.to_csv(R / "robustness.csv", index=False)
A.round(4).to_csv(R / "annual_with_land_est.csv", index=False)
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(RB.to_string())
