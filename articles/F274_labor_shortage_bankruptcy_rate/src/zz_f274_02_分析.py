"""率・割合・比を計算し、仮説 H1〜H4、頑健性、問い直しを results/ に書く。"""
import csv, json, os
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)) + "/../"
P = {int(r["year"]): {k: (float(v) if v != "" else None) for k, v in r.items()} for r in csv.DictReader(open(H + "data/processed/panel.csv", encoding="utf-8"))}
yrs = sorted(P)
def per(num, den, y, scale=1e5):
    a, b = P[y][num], P[y][den]
    return None if a is None or b is None else a / b * scale
def ratio(f, y1=2025, y0=2019):
    a, b = f(y1), f(y0); return None if a is None or b is None else a / b
R = {}
# 年ごとの指標
rows = []
for y in yrs:
    d = {"year": y}
    for s in ["tdb_jinte", "tsr_3f", "tsr_4f", "tsr_koukeisha", "tsr_kyujinnan", "tsr_taishoku", "tsr_jinkenhi"]:
        d[s] = P[y][s]; d[s + "_per10man_hojin"] = per(s, "hojin", y); d[s + "_per10man_kigyo"] = per(s, "kigyo", y)
    d["tdb_share_pct"] = per("tdb_jinte", "tdb_total", y, 100)
    d["tsr3_share_pct"] = per("tsr_3f", "tsr_total", y, 100); d["tsr4_share_pct"] = per("tsr_4f", "tsr_total", y, 100)
    d["tdb_total_per10man_hojin"] = per("tdb_total", "hojin", y)
    d["yuko_kyujin"] = P[y]["yuko_kyujin"]
    rows.append(d)
with open(H + "results/A_yearly.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
    for d in rows: w.writerow({k: ("" if v is None else (round(v, 4) if isinstance(v, float) else v)) for k, v in d.items()})
Y = {d["year"]: d for d in rows}
g = lambda k: (lambda y: Y[y][k])
# 件数そのものの比
R["count_ratio_2025_2019"] = {"tdb": P[2025]["tdb_jinte"] / P[2019]["tdb_jinte"], "tsr_3f": P[2025]["tsr_3f"] / P[2019]["tsr_3f"], "tsr_4f": P[2025]["tsr_4f"] / P[2019]["tsr_4f"],
    "hojin": P[2025]["hojin"] / P[2019]["hojin"], "kigyo": P[2025]["kigyo"] / P[2019]["kigyo"], "tdb_total": P[2025]["tdb_total"] / P[2019]["tdb_total"], "tsr_total": P[2025]["tsr_total"] / P[2019]["tsr_total"]}
# H1
h1 = ratio(g("tdb_jinte_per10man_hojin"))
R["H1"] = {"tdb_per10man_hojin_2019": Y[2019]["tdb_jinte_per10man_hojin"], "tdb_per10man_hojin_2025": Y[2025]["tdb_jinte_per10man_hojin"], "ratio": h1, "criterion": ">=1.5", "verdict": "支持" if h1 >= 1.5 else "外れ"}
# H2
h2 = ratio(g("tdb_share_pct"))
R["H2"] = {"tdb_share_2019": Y[2019]["tdb_share_pct"], "tdb_share_2025": Y[2025]["tdb_share_pct"], "ratio": h2, "criterion": ">=1.5", "verdict": "支持" if h2 >= 1.5 else "外れ"}
# H3
h3 = ratio(g("tsr_4f_per10man_hojin")); h3c = P[2025]["tsr_4f"] / P[2019]["tsr_4f"]
R["H3"] = {"tsr4_2019": P[2019]["tsr_4f"], "tsr4_2025": P[2025]["tsr_4f"], "count_ratio": h3c, "per_hojin_ratio": h3, "tsr3_count_ratio": P[2025]["tsr_3f"] / P[2019]["tsr_3f"],
           "koukeisha_share_2019": P[2019]["tsr_koukeisha"] / P[2019]["tsr_4f"], "koukeisha_share_2025": P[2025]["tsr_koukeisha"] / P[2025]["tsr_4f"],
           "criterion": "4要因の合計で2025/2019 <1.5 なら支持", "verdict": "支持" if h3c < 1.5 else "外れ"}
# H4：2016-2019 の法人10万社あたり TDB 件数 ~ 有効求人倍率
def fit(ys, key="tdb_jinte_per10man_hojin"):
    x = np.array([Y[y]["yuko_kyujin"] for y in ys]); z = np.array([Y[y][key] for y in ys])
    b, a = np.polyfit(x, z, 1); return a, b, float(np.corrcoef(x, z)[0, 1])
a, b, r = fit([2016, 2017, 2018, 2019])
pred = {y: a + b * Y[y]["yuko_kyujin"] for y in yrs if Y[y]["tdb_jinte"] is not None}
res = {y: Y[y]["tdb_jinte_per10man_hojin"] - pred[y] for y in pred}
R["H4"] = {"fit_years": "2016-2019", "intercept": a, "slope": b, "r": r, "pred": {str(y): pred[y] for y in pred}, "actual": {str(y): Y[y]["tdb_jinte_per10man_hojin"] for y in pred},
           "resid": {str(y): res[y] for y in pred}, "x_range_fit": [1.36, 1.61], "note": "4点の直線を当てはめの範囲（1.36〜1.61）の外へ延ばした予測。2020・2021年は負の件数を予測するので弱い証拠", "verdict": "支持" if all(res[y] > 0 for y in (2023, 2024, 2025)) else "外れ"}
# 頑健性
rb = {}
rb["R1_kigyo_denominator"] = {"tdb_ratio": ratio(g("tdb_jinte_per10man_kigyo")), "tsr3_ratio": ratio(g("tsr_3f_per10man_kigyo")), "tsr4_ratio": ratio(g("tsr_4f_per10man_kigyo"))}
rb["R2_tsr3"] = {"per_hojin_ratio": ratio(g("tsr_3f_per10man_hojin")), "share_ratio": ratio(g("tsr3_share_pct")), "share_2019": Y[2019]["tsr3_share_pct"], "share_2025": Y[2025]["tsr3_share_pct"],
                 "tsr4_share_2019": Y[2019]["tsr4_share_pct"], "tsr4_share_2025": Y[2025]["tsr4_share_pct"], "tsr4_share_ratio": ratio(g("tsr4_share_pct"))}
base = lambda k: np.mean([Y[y][k] for y in (2016, 2017, 2018, 2019)])
rb["R3_vs_2016_2019_avg"] = {"tdb_per_hojin": Y[2025]["tdb_jinte_per10man_hojin"] / base("tdb_jinte_per10man_hojin"), "tdb_share": Y[2025]["tdb_share_pct"] / base("tdb_share_pct"),
                             "tsr3_per_hojin": Y[2025]["tsr_3f_per10man_hojin"] / base("tsr_3f_per10man_hojin"), "tsr4_per_hojin": Y[2025]["tsr_4f_per10man_hojin"] / base("tsr_4f_per10man_hojin")}
rb["R4_fiscal_tsr3"] = {"fy2019": P[2019]["tsr_3f_fy"], "fy2025": P[2025]["tsr_3f_fy"], "count_ratio": P[2025]["tsr_3f_fy"] / P[2019]["tsr_3f_fy"],
                        "per_hojin_ratio": (P[2025]["tsr_3f_fy"] / P[2025]["hojin"]) / (P[2019]["tsr_3f_fy"] / P[2019]["hojin"])}
# 2025年度の法人数を延ばさず2024年度の値のまま使った場合
rb["R5_hojin2025_flat"] = {"tdb_ratio": (P[2025]["tdb_jinte"] / P[2024]["hojin"]) / (P[2019]["tdb_jinte"] / P[2019]["hojin"])}
# 公表時点の違い（TDB 2019年の当時の値185件）
rb["R6_tdb_vintage"] = {"ratio_with_185": (P[2025]["tdb_jinte"] / P[2025]["hojin"]) / (185 / P[2019]["hojin"]), "revision_2019": 192 - 185, "revision_2018": 159 - 153}
# H4 の当てはめ期間を2016-2022 に広げる
a2, b2, r2 = fit([2016, 2017, 2018, 2019, 2020, 2021, 2022])
rb["R7_H4_fit_2016_2022"] = {"intercept": a2, "slope": b2, "r": r2, "resid": {str(y): Y[y]["tdb_jinte_per10man_hojin"] - (a2 + b2 * Y[y]["yuko_kyujin"]) for y in (2023, 2024, 2025)}}
R["robust"] = rb
# 倒産全体（法人10万社あたり）
R["total_per10man_hojin"] = {"2019": Y[2019]["tdb_total_per10man_hojin"], "2025": Y[2025]["tdb_total_per10man_hojin"], "ratio": ratio(g("tdb_total_per10man_hojin"))}
# 問い直し：3要因の中身
comp = {}
for y in (2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025):
    t = P[y]["tsr_3f"]; comp[str(y)] = {k: P[y][k] / t for k in ("tsr_kyujinnan", "tsr_taishoku", "tsr_jinkenhi")}
growth = {k: (P[2025][k] / P[2025]["hojin"]) / (P[2019][k] / P[2019]["hojin"]) for k in ("tsr_kyujinnan", "tsr_taishoku", "tsr_jinkenhi")}
contrib = {k: (P[2025][k] - P[2019][k]) / (P[2025]["tsr_3f"] - P[2019]["tsr_3f"]) for k in ("tsr_kyujinnan", "tsr_taishoku", "tsr_jinkenhi")}
growth16 = {k: (P[2025][k] / P[2025]["hojin"]) / (P[2016][k] / P[2016]["hojin"]) for k in ("tsr_kyujinnan", "tsr_taishoku", "tsr_jinkenhi")}
R["reask"] = {"share": comp, "per_hojin_ratio_2025_2019": growth, "per_hojin_ratio_2025_2016": growth16, "contrib_to_increase": contrib, "yuko_2019": P[2019]["yuko_kyujin"], "yuko_2025": P[2025]["yuko_kyujin"]}
json.dump(R, open(H + "results/main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: R[k] for k in ("count_ratio_2025_2019", "H1", "H2", "H3")}, ensure_ascii=False, indent=0, default=float))
print("H4", R["H4"]["verdict"], round(a, 3), round(b, 3), round(r, 3), {k: round(v, 3) for k, v in R["H4"]["resid"].items()})
print(json.dumps(rb, ensure_ascii=False, default=float)); print(R["total_per10man_hojin"]); print(json.dumps(R["reask"], default=float))
