"""PLAN の仮説 H1〜H5 と頑健性を計算し、results/ に書く。"""
import json, os
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RES = os.path.join(HERE, "..", "results")
RAW = os.path.join(DATA, "raw")
os.makedirs(RES, exist_ok=True)

n = pd.read_csv(os.path.join(DATA, "national.csv"), index_col=0)
p = pd.read_csv(os.path.join(DATA, "prefecture.csv"), index_col=0)
tot = p.drop(columns="region").sum()

# 修了者数（各年3月）から、小学校等1年生の数を逆算する：1年生 ≒ 修了者 ÷ 就園率
g = pd.read_excel(os.path.join(RAW, "gk_000031852313.xlsx"), header=None)
comp = {}
for _, r in g.iterrows():
    try:
        y = int(float(r.iloc[1]))
    except (TypeError, ValueError):
        continue
    if 1940 < y < 2100 and y not in comp:
        kc = pd.to_numeric(r.iloc[2], errors="coerce")
        ec = pd.to_numeric(r.iloc[3], errors="coerce")
        comp[y] = {"kg_comp": kc, "ke_comp": 0.0 if pd.isna(ec) else float(ec)}
comp = pd.DataFrame.from_dict(comp, orient="index")
n = n.join(comp)
n["first_graders_from_kg"] = n["kg_comp"] / (n["kg_rate"] / 100)
n["first_graders_from_ke"] = np.where(n["ke_rate"] > 0, n["ke_comp"] / (n["ke_rate"] / 100), np.nan)
n["rate_sum"] = n["kg_rate"] + n["ke_rate"]
n.loc[1990:].round(4).to_csv(os.path.join(RES, "national_series.csv"))

R = {}
r1 = lambda x: float(round(x, 1))
r3 = lambda x: float(round(x, 3))

# ---- H1：こども園の3〜5歳のうち1号の割合
s1 = {y: tot[f"ke{y}_35_n1"] / tot[f"ke{y}_35"] * 100 for y in (2023, 2024, 2025)}
R["H1"] = {"ke_n1_share_35_2025_pct": r1(s1[2025]), "threshold_pct": 40.0,
           "result": "支持" if s1[2025] < 40 else "外れ",
           "robust_2023_pct": r1(s1[2023]), "robust_2024_pct": r1(s1[2024])}

# ---- H4：幼稚園の3〜5歳のうち2号（保育認定）の割合
s4 = tot["kg2025_35_n2"] / tot["kg2025_35"] * 100
R["H4"] = {"kg_n2_share_35_2025_pct": r1(s4), "threshold_pct": 10.0,
           "result": "支持" if s4 >= 10 else "外れ",
           "kg_n2_share_5y_2025_pct": r1(tot["kg2025_5_n2"] / (tot["kg2025_5_n1"] + tot["kg2025_5_n2"]) * 100)}

# ---- H2：「幼稚園型」の割合（修了の年＝前の年の5月に5歳）
# 2025年3月の修了者は、2024年5月の5歳。こども園5歳の1号の割合は2024年の値を使う。
ke5_n1_2024 = tot["ke2024_5_n1"] / tot["ke2024_5"]
ke5_n1_2025 = tot["ke2025_5_n1"] / (tot["ke2025_5_n1"] + tot["ke2025_5_n2"])
kg5_n2_2025 = tot["kg2025_5_n2"] / (tot["kg2025_5_n1"] + tot["kg2025_5_n2"])
kg14, kg25, ke25 = n.loc[2014, "kg_rate"], n.loc[2025, "kg_rate"], n.loc[2025, "ke_rate"]
edu = kg25 + ke25 * ke5_n1_2024
edu_alt = kg25 + ke25 * ke5_n1_2025
edu_strict = kg25 * (1 - kg5_n2_2025) + ke25 * ke5_n1_2024
R["H2"] = {
    "kg_rate_2014": float(kg14), "kg_rate_2025": float(kg25), "ke_rate_2025": float(ke25),
    "rate_sum_2025": r1(kg25 + ke25),
    "ke5_n1_share_2024": r3(ke5_n1_2024),
    "edu_type_rate_2025": r1(edu), "gap_vs_2014_pt": r1(kg14 - edu), "threshold_pt": 10.0,
    "result": "支持" if kg14 - edu >= 10 else "外れ",
    "robust_use_2025_share": {"edu_type_rate": r1(edu_alt), "gap_pt": r1(kg14 - edu_alt)},
    "robust_exclude_kg_n2": {"edu_type_rate": r1(edu_strict), "gap_pt": r1(kg14 - edu_strict),
                             "kg5_n2_share_2025_used": r3(kg5_n2_2025)},
    "ke_n2_part_pt": r1(ke25 * (1 - ke5_n1_2024)),
    "ke_n1_part_pt": r1(ke25 * ke5_n1_2024),
}
# 2025年の修了者の内訳（1年生100人あたり）
parts = pd.DataFrame({
    "part": ["幼稚園（1号）", "幼稚園（2号）", "こども園（1号）", "こども園（2号）"],
    "per100_2025": [kg25 * (1 - kg5_n2_2025), kg25 * kg5_n2_2025, ke25 * ke5_n1_2024, ke25 * (1 - ke5_n1_2024)],
})
parts.round(2).to_csv(os.path.join(RES, "completers_breakdown_2025.csv"), index=False)

# 1年生の数（逆算）：2014→2025
fg14, fg25 = n.loc[2014, "first_graders_from_kg"], n.loc[2025, "first_graders_from_kg"]
R["cohort"] = {"first_graders_2014": int(round(fg14)), "first_graders_2025": int(round(fg25)),
               "first_graders_2025_from_ke": int(round(n.loc[2025, "first_graders_from_ke"])),
               "ratio_2025_2014": r3(fg25 / fg14)}
# 修了者の数で見た分け方（2014年3月→2025年3月）
kgc14, kgc25, kec25 = n.loc[2014, "kg_comp"], n.loc[2025, "kg_comp"], n.loc[2025, "ke_comp"]
demo = kgc14 * (fg25 / fg14 - 1)
to_ke1 = kec25 * ke5_n1_2024
R["decomp_completers"] = {
    "kg_completers_2014": int(kgc14), "kg_completers_2025": int(kgc25), "change": int(kgc25 - kgc14),
    "cohort_effect": int(round(demo)), "to_kodomoen_n1": int(round(-to_ke1)),
    "other": int(round(kgc25 - kgc14 - demo + to_ke1)),
    "ke_completers_2025": int(kec25), "ke_completers_2025_n2_est": int(round(kec25 * (1 - ke5_n1_2024))),
}

# ---- H5：園数と在園者数の減り方
en14, en25 = n.loc[2014, "kg_en"], n.loc[2025, "kg_en"]
ji14, ji25 = n.loc[2014, "kg_ji"], n.loc[2025, "kg_ji"]
R["H5"] = {"kg_en_2014": int(en14), "kg_en_2025": int(en25), "en_change_pct": r1((en25 / en14 - 1) * 100),
           "kg_ji_2014": int(ji14), "kg_ji_2025": int(ji25), "ji_change_pct": r1((ji25 / ji14 - 1) * 100),
           "per_en_2014": r1(ji14 / en14), "per_en_2025": r1(ji25 / en25),
           "result": "支持" if (en25 / en14) > (ji25 / ji14) else "外れ",
           "peak_en_year": int(n["kg_en"].idxmax()), "peak_en": int(n["kg_en"].max()),
           "ke_en_2025": int(n.loc[2025, "ke_en"]),
           "kg_plus_ke_en_2025": int(en25 + n.loc[2025, "ke_en"])}

# ---- H3：都道府県
q = pd.DataFrame(index=p.index)
q["region"] = p["region"]
q["kg_decline_pct"] = (1 - p["kg2025"] / p["kg2014"]) * 100
q["kg_decline_pct_from2015"] = (1 - p["kg2025"] / p["kg2015"]) * 100
q["kg5_decline_pct"] = (1 - p["kg2025_5"] / p["kg2014_5"]) * 100
q["ke_n1_share"] = p["ke2025_35_n1"] / (p["kg2025_35_n1"] + p["ke2025_35_n1"]) * 100
q["ke5_n1_share"] = p["ke2025_5_n1"] / (p["kg2025_5_n1"] + p["ke2025_5_n1"]) * 100
den = p["kg2025_35"] + p["ke2025_35"]
q["sh_kg_n1"] = p["kg2025_35_n1"] / den * 100
q["sh_kg_n2"] = p["kg2025_35_n2"] / den * 100
q["sh_ke_n1"] = p["ke2025_35_n1"] / den * 100
q["sh_ke_n2"] = p["ke2025_35_n2"] / den * 100
q["ke_share_35"] = p["ke2025_35"] / den * 100
q["kg_plus_ke_vs_kg2014"] = den / p["kg2014"] * 100
q.round(2).to_csv(os.path.join(RES, "prefecture_metrics.csv"))


def corr(x, y):
    rs = stats.spearmanr(x, y)
    pr = stats.pearsonr(x, y)
    return {"spearman": r3(rs.statistic), "spearman_p": float(f"{rs.pvalue:.2e}"),
            "pearson": r3(pr.statistic), "pearson_p": float(f"{pr.pvalue:.2e}")}

c_main = corr(q["ke_n1_share"], q["kg_decline_pct"])
R["H3"] = {"n": int(len(q)), **c_main, "threshold_spearman": 0.5,
           "result": "支持" if c_main["spearman"] >= 0.5 else "外れ",
           "robust_base2015": corr(q["ke_n1_share"], q["kg_decline_pct_from2015"]),
           "robust_5y_only": corr(q["ke5_n1_share"], q["kg5_decline_pct"]),
           "kg_decline_pct_median": r1(q["kg_decline_pct"].median()),
           "kg_decline_pct_min": r1(q["kg_decline_pct"].min()), "kg_decline_pct_max": r1(q["kg_decline_pct"].max()),
           "ke_n1_share_median": r1(q["ke_n1_share"].median()),
           "ke_n1_share_min": r1(q["ke_n1_share"].min()), "ke_n1_share_max": r1(q["ke_n1_share"].max()),
           "ke_share_35_median": r1(q["ke_share_35"].median()),
           "ke_share_35_min": r1(q["ke_share_35"].min()), "ke_share_35_max": r1(q["ke_share_35"].max())}
# 減り方の割合をこども園1号の割合で説明した直線の傾き（%ポイントあたり）
sl = stats.linregress(q["ke_n1_share"], q["kg_decline_pct"])
R["H3"]["ols_slope"] = r3(sl.slope)
R["H3"]["ols_intercept"] = r1(sl.intercept)

# 地域ごと（北から南）
reg_order = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
pr = p.groupby("region").sum(numeric_only=True).loc[reg_order]
reg = pd.DataFrame({
    "kg_decline_pct": (1 - pr["kg2025"] / pr["kg2014"]) * 100,
    "ke_n1_share": pr["ke2025_35_n1"] / (pr["kg2025_35_n1"] + pr["ke2025_35_n1"]) * 100,
    "ke_share_35": pr["ke2025_35"] / (pr["kg2025_35"] + pr["ke2025_35"]) * 100,
    "ke_n1_within_ke": pr["ke2025_35_n1"] / pr["ke2025_35"] * 100,
})
reg.index.name = "region"
reg.round(2).to_csv(os.path.join(RES, "region_metrics.csv"))
R["region"] = {k: {c: r1(v) for c, v in row.items()} for k, row in reg.iterrows()}

R["national_kg_ji_peak"] = {"year": int(n["kg_ji"].idxmax()), "value": int(n["kg_ji"].max())}
R["national_ke"] = {"ke_ji_2025": int(n.loc[2025, "ke_ji"]), "ke_35_2025": int(tot["ke2025_35"]),
                    "ke_02_2025": int(n.loc[2025, "ke_ji"] - tot["ke2025_35"]),
                    "kg_plus_ke35_2025": int(ji25 + tot["ke2025_35"])}

with open(os.path.join(RES, "main.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(R, ensure_ascii=False, indent=1)[:4000])
