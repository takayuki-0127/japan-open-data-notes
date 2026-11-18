"""年平均・年増加量・季節変動・排出との比較・仮説・頑健性。乱数は使わない。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
M = pd.read_csv(ROOT / "data" / "monthly.csv")
M = M[M.year <= 2025]
E = pd.read_csv(ROOT / "data" / "emissions.csv")
ST = ["綾里", "南鳥島", "与那国島"]
GT_CO2_PER_PPM = 7.78  # 1ppm = 炭素2.124Gt = CO2 7.78Gt


def annual(st):
    d = M[M.station == st].dropna(subset=["co2"])
    g = d.groupby("year").co2.agg(["mean", "count"])
    g = g[g["count"] == 12]["mean"]
    return g


rows = []
for st in ST:
    a = annual(st)
    for y, v in a.items():
        rows.append({"station": st, "year": int(y), "annual_mean": v, "growth": v - a.get(y - 1, np.nan)})
A = pd.DataFrame(rows)
A.round(4).to_csv(R / "annual.csv", index=False)

# 季節変動
srows = []; amp = {}
for st in ST:
    d = M[M.station == st].sort_values(["year", "month"]).reset_index(drop=True)
    s = d.co2.interpolate(limit=2)
    ma = s.rolling(12, center=True).mean().rolling(2).mean().shift(-1)  # 2×12 の中心移動平均
    d["anom"] = s - ma
    c = d.dropna(subset=["anom"]).groupby("month").anom.mean()
    amp[st] = float(c.max() - c.min())
    for mth, v in c.items():
        srows.append({"station": st, "month": int(mth), "anom": v})
SC = pd.DataFrame(srows); SC.round(4).to_csv(R / "seasonal_cycle.csv", index=False)

ry = A[A.station == "綾里"].set_index("year")
mn = A[A.station == "南鳥島"].set_index("year")
def mean_growth(df, y0, y1):
    return float(df.loc[y0:y1, "growth"].mean())

main = {}
main["ryori_first_year"] = int(ry.index.min()); main["ryori_last_year"] = int(ry.index.max())
for st, df in [("ryori", ry), ("mnm", mn)]:
    main[f"{st}_annual_first"] = round(float(df.annual_mean.iloc[0]), 2); main[f"{st}_annual_first_year"] = int(df.index[0])
    main[f"{st}_annual_2025"] = round(float(df.annual_mean.loc[2025]), 2)
main["ryori_growth_1991_2013"] = round(mean_growth(ry, 1991, 2013), 3)
main["ryori_growth_2014_2025"] = round(mean_growth(ry, 2014, 2025), 3)
main["ryori_growth_2025"] = round(float(ry.growth.loc[2025]), 3)
main["ryori_growth_sd_1991_2025"] = round(float(ry.loc[1991:2025, "growth"].std()), 3)
# 10年ごと
for y0 in [1988, 1996, 2006, 2016]:
    y1 = y0 + 9
    main[f"ryori_growth_{y0}_{min(y1, 2025)}"] = round(mean_growth(ry, y0, min(y1, 2025)), 3)

e = E.set_index("fy").co2_total_Mt
main["em_1990"] = round(float(e.loc[1990]), 1); main["em_2013"] = round(float(e.loc[2013]), 1); main["em_2024"] = round(float(e.loc[2024]), 1)
main["em_drop_2013_2024_Mt"] = round(float(e.loc[2013] - e.loc[2024]), 1)
main["em_drop_pct"] = round(float(1 - e.loc[2024] / e.loc[2013]) * 100, 1)
main["em_2024_ppm_upper"] = round(float(e.loc[2024]) / 1000 / GT_CO2_PER_PPM, 4)
main["em_drop_ppm_upper"] = round(main["em_drop_2013_2024_Mt"] / 1000 / GT_CO2_PER_PPM, 4)
main["em_drop_ppm_half"] = round(main["em_drop_ppm_upper"] * 0.5, 4)
main["em_drop_share_of_growth_2014_2025"] = round(main["em_drop_ppm_upper"] / main["ryori_growth_2014_2025"], 4)

# 年ごとの動きの相関（暦年の増加量と同じ数字の年度の排出、どちらも直線を除く）
J = pd.DataFrame({"growth": ry.growth}).join(e.rename("em"), how="inner").dropna()
J = J.loc[1991:2024]
def detr(s):
    x = s.index.values.astype(float); p = np.polyfit(x, s.values, 1); return s - np.polyval(p, x)
r_lvl = float(np.corrcoef(detr(J.growth), detr(J.em))[0, 1])
dem = J.em.diff().dropna(); r_diff = float(np.corrcoef(detr(J.growth.loc[dem.index]), dem)[0, 1])
main["corr_detrended"] = round(r_lvl, 3); main["corr_growth_vs_em_change"] = round(r_diff, 3); main["corr_n"] = int(len(J))
J.round(4).to_csv(R / "growth_vs_emissions.csv")

main["amp"] = {k: round(v, 2) for k, v in amp.items()}
main["amp_ratio_ryo_mnm"] = round(amp["綾里"] / amp["南鳥島"], 2); main["amp_ratio_ryo_yon"] = round(amp["綾里"] / amp["与那国島"], 2)

main["hypotheses"] = {
    "H1": {"rule": "綾里の年増加量の平均は2014〜2025年＞1991〜2013年", "value": [main["ryori_growth_1991_2013"], main["ryori_growth_2014_2025"]],
           "verdict": "支持" if main["ryori_growth_2014_2025"] > main["ryori_growth_1991_2013"] else "外れ"},
    "H2": {"rule": "日本の排出の減少（2013→2024年度）を上限で換算しても0.1ppm/年未満", "value": main["em_drop_ppm_upper"],
           "verdict": "支持" if main["em_drop_ppm_upper"] < 0.1 else "外れ"},
    "H3": {"rule": "排出と年増加量の年ごとの動きの相関は|r|<0.3", "value": main["corr_detrended"],
           "verdict": "支持" if abs(main["corr_detrended"]) < 0.3 else "外れ"},
    "H4": {"rule": "綾里の季節変動の幅は南鳥島・与那国島の2倍以上", "value": [main["amp_ratio_ryo_mnm"], main["amp_ratio_ryo_yon"]],
           "verdict": "支持" if min(main["amp_ratio_ryo_mnm"], main["amp_ratio_ryo_yon"]) >= 2 else "外れ"},
}

# 頑健性
rob = [{"check": "本線：綾里、年平均の前年差、1991〜2013年と2014〜2025年", "before": main["ryori_growth_1991_2013"], "after": main["ryori_growth_2014_2025"]}]
rob.append({"check": "南鳥島（1995〜2013年と2014〜2025年）", "before": round(mean_growth(mn, 1995, 2013), 3), "after": round(mean_growth(mn, 2014, 2025), 3)})
def fit_slope(df, y0, y1):
    d = df.loc[y0:y1]; return round(float(np.polyfit(d.index.values.astype(float), d.annual_mean.values, 1)[0]), 3)
rob.append({"check": "綾里、各期間の年平均に当てた直線の傾き（ppm/年）", "before": fit_slope(ry, 1990, 2013), "after": fit_slope(ry, 2013, 2025)})
rob.append({"check": "綾里、区切りを2008年（1991〜2007年と2008〜2025年）", "before": round(mean_growth(ry, 1991, 2007), 3), "after": round(mean_growth(ry, 2008, 2025), 3)})
rob.append({"check": "綾里、速報値の2025年を除く（2014〜2024年）", "before": main["ryori_growth_1991_2013"], "after": round(mean_growth(ry, 2014, 2024), 3)})
yo = A[A.station == "与那国島"].set_index("year")
rob.append({"check": "与那国島（1998〜2013年と2014〜2023年）", "before": round(mean_growth(yo, 1998, 2013), 3), "after": round(mean_growth(yo, 2014, 2023), 3)})
RB = pd.DataFrame(rob); RB["after_minus_before"] = (RB.after - RB.before).round(3)
RB.to_csv(R / "robustness.csv", index=False)
main["robust_all_after_gt_before"] = bool((RB.after > RB.before).all())
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(RB.to_string())
