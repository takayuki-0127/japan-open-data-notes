"""不詳の割合の推移、地方別、配偶関係、補完の影響、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
age = pd.read_csv(ROOT / "data" / "age_unknown.csv")
det = pd.read_csv(ROOT / "data" / "age_2025_2020_detail.csv")
mar = pd.read_csv(ROOT / "data" / "marital_unknown_national.csv")
mp = pd.read_csv(ROOT / "data" / "marital_unknown_pref_2025.csv")
REGION = {1: "北海道"}
for c in range(2, 8): REGION[c] = "東北"
for c in range(8, 15): REGION[c] = "関東"
for c in range(15, 24): REGION[c] = "中部"
for c in range(24, 31): REGION[c] = "近畿"
for c in range(31, 36): REGION[c] = "中国"
for c in range(36, 40): REGION[c] = "四国"
for c in range(40, 48): REGION[c] = "九州・沖縄"
RORDER = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
BIG = {11, 12, 13, 14, 26, 27, 28}; SKANTO = {11, 12, 13, 14}

o = age[age.version == "original"].copy()
o["rate"] = 100 * o.unknown / o.total
nat = o[o.pref_code == 0][["year", "total", "unknown", "rate"]].dropna()
nat.to_csv(R / "age_unknown_national.csv", index=False, float_format="%.5f", lineterminator="\n")
r = lambda y: float(nat[nat.year == y].rate.iloc[0])

pref = o[(o.pref_code > 0) & (o.year >= 1980)].copy()
pref["region"] = pref.pref_code.map(REGION)
pref[["year", "pref_code", "pref", "region", "total", "unknown", "rate"]].sort_values(["year", "pref_code"]).to_csv(
    R / "age_unknown_pref.csv", index=False, float_format="%.5f", lineterminator="\n")
reg = pref.groupby(["year", "region"])[["total", "unknown"]].sum().reset_index()
reg["rate"] = 100 * reg.unknown / reg.total
reg["region"] = pd.Categorical(reg.region, RORDER, ordered=True)
reg = reg.sort_values(["year", "region"])
reg.to_csv(R / "age_unknown_region.csv", index=False, float_format="%.5f", lineterminator="\n")


def grp_rate(df, codes, inside=True):
    x = df[df.pref_code.isin(codes) == inside]
    return float(100 * x.unknown.sum() / x.total.sum())


p25 = pref[pref.year == 2025]
p20 = pref[pref.year == 2020]

# 配偶関係（全国）：男女を足して総数を作る
m2 = mar.copy()
mt = m2[m2.sex.isin(["男", "女"])].groupby(["year", "age"])[["total", "unknown"]].sum().reset_index(); mt["sex"] = "総数(計算)"
m2 = pd.concat([m2, mt], ignore_index=True)
m2["rate"] = 100 * m2.unknown / m2.total
m2 = m2[m2.year >= 1950]
m2.to_csv(R / "marital_unknown_national_rate.csv", index=False, float_format="%.5f", lineterminator="\n")
def mrate(y, sex, ages):
    x = m2[(m2.year == y) & (m2.sex == sex) & (m2.age.isin(ages))]
    return float(100 * x.unknown.sum() / x.total.sum())
A2534 = ["25～29歳", "30～34歳"]
A65 = ["65～69歳", "70～74歳", "75～79歳", "80～84歳", "85歳以上"]
ALL = [a for a in m2.age.unique() if a not in ("総数",)]
mp["rate"] = 100 * mp.unknown / mp.total
mp["region"] = mp.pref_code.map(REGION)
mp.to_csv(R / "marital_unknown_pref_2025_rate.csv", index=False, float_format="%.5f", lineterminator="\n")
mpt = mp[(mp.sex == "総数") & (mp.pref_code > 0)]

# 補完の影響（65歳以上・15歳未満の割合）
def shares(year, ver_o, ver_i):
    a = age[(age.year == year) & (age.version == ver_o)].set_index("pref_code")
    b = age[(age.year == year) & (age.version == ver_i)].set_index("pref_code")
    df = pd.DataFrame({"pref": a.pref, "unknown_rate": 100 * a.unknown / a.total,
                       "s65_original": 100 * a.a65 / (a.total - a.unknown), "s65_imputed": 100 * b.a65 / b.total,
                       "s014_original": 100 * a.a0_14 / (a.total - a.unknown), "s014_imputed": 100 * b.a0_14 / b.total,
                       "n65_original": a.a65, "n65_imputed": b.a65})
    df["d65"] = df.s65_imputed - df.s65_original; df["d014"] = df.s014_imputed - df.s014_original
    df["n65_diff"] = df.n65_imputed - df.n65_original
    df["year"] = year; df["imputed_version"] = ver_i
    return df.reset_index()
imp = pd.concat([shares(2025, "original", "imputed"), shares(2020, "original", "imputed_2026retro"),
                 shares(2020, "original", "imputed_2022"), shares(2015, "original", "imputed_2022")], ignore_index=True)
imp["region"] = imp.pref_code.map(REGION)
imp.to_csv(R / "imputation_effect.csv", index=False, float_format="%.5f", lineterminator="\n")
I25 = imp[(imp.year == 2025) & (imp.pref_code == 0)].iloc[0]
I25p = imp[(imp.year == 2025) & (imp.pref_code > 0)]
# 公表の構成比（原数値の表の％）と自分の計算の照合
pub = det[(det.version == "original") & (det.nationality == "国籍総数") & (det.sex == "総数") & (det.pref_code == 0)].iloc[0]

main = {
    "age_unknown_rate": {int(y): float(v) for y, v in zip(nat.year, nat.rate)},
    "age_unknown_n_2025": float(nat[nat.year == 2025].unknown.iloc[0]), "age_unknown_n_2020": float(nat[nat.year == 2020].unknown.iloc[0]),
    "age_unknown_n_2000": float(nat[nat.year == 2000].unknown.iloc[0]),
    "ratio_2025_2000": r(2025) / r(2000),
    "region_rate_2025": {k: float(v) for k, v in reg[reg.year == 2025].set_index("region").rate.items()},
    "region_rate_2000": {k: float(v) for k, v in reg[reg.year == 2000].set_index("region").rate.items()},
    "big7_rate_2025": grp_rate(p25, BIG), "rest_rate_2025": grp_rate(p25, BIG, False),
    "skanto_rate_2025": grp_rate(p25, SKANTO), "rest_skanto_rate_2025": grp_rate(p25, SKANTO, False),
    "pref_rate_2025_min": float(p25.rate.min()), "pref_rate_2025_max": float(p25.rate.max()),
    "pref_rate_2025_median": float(p25.rate.median()),
    "n_pref_up_2020_2025": int((p25.set_index("pref_code").rate > p20.set_index("pref_code").rate).sum()),
    "marital_rate_total15_2025": mrate(2025, "総数", ALL), "marital_rate_2534_2025": mrate(2025, "総数", A2534),
    "marital_rate_65plus_2025": mrate(2025, "総数", A65),
    "marital_rate_total15_by_year": {int(y): mrate(int(y), "総数(計算)", ALL) for y in sorted(m2[m2.sex == "総数(計算)"].year.unique())},
    "marital_rate_2534_by_year": {int(y): mrate(int(y), "総数(計算)", A2534) for y in sorted(m2[m2.sex == "総数(計算)"].year.unique())},
    "marital_rate_male_2529_2025": mrate(2025, "男", ["25～29歳"]), "marital_rate_female_2529_2025": mrate(2025, "女", ["25～29歳"]),
    "marital_pref_2025_min": float(mpt.rate.min()), "marital_pref_2025_max": float(mpt.rate.max()),
    "marital_big7_2025": float(100 * mpt[mpt.pref_code.isin(BIG)].unknown.sum() / mpt[mpt.pref_code.isin(BIG)].total.sum()),
    "marital_rest_2025": float(100 * mpt[~mpt.pref_code.isin(BIG)].unknown.sum() / mpt[~mpt.pref_code.isin(BIG)].total.sum()),
    "corr_age_marital_pref_2025": float(np.corrcoef(p25.sort_values("pref_code").rate, mpt.sort_values("pref_code").rate)[0, 1]),
    "s65_original_2025": float(I25.s65_original), "s65_imputed_2025": float(I25.s65_imputed), "d65_2025": float(I25.d65),
    "s014_original_2025": float(I25.s014_original), "s014_imputed_2025": float(I25.s014_imputed), "d014_2025": float(I25.d014),
    "n65_original_2025": float(I25.n65_original), "n65_imputed_2025": float(I25.n65_imputed), "n65_diff_2025": float(I25.n65_diff),
    "d65_pref_2025_min": float(I25p.d65.min()), "d65_pref_2025_max": float(I25p.d65.max()),
    "d65_pref_2025_absmax": float(I25p.d65.abs().max()), "n_pref_d65_neg_2025": int((I25p.d65 < 0).sum()),
    "corr_unknown_d65_pref_2025": float(np.corrcoef(I25p.unknown_rate, I25p.d65)[0, 1]),
    "pub_pct65_original_2025": float(pub.pct65_pub), "own_pct65_original_2025": float(I25.s65_original),
}
main["H1"] = "支持" if (r(2025) >= 1.5 and main["ratio_2025_2000"] >= 5) else "外れ"
main["H2"] = "支持" if main["marital_rate_2534_2025"] >= 2 * main["marital_rate_65plus_2025"] else "外れ"
main["H3"] = "支持" if main["big7_rate_2025"] > main["rest_rate_2025"] else "外れ"
main["H4"] = "支持" if abs(main["d65_2025"]) <= 0.3 else "外れ"

# 頑健性
rob = []
dd = det[(det.year == 2025) & (det.version == "original") & (det.pref_code == 0)]
for (nt, sx), x in dd.groupby(["nationality", "sex"]):
    rob.append({"check": f"2025年 年齢不詳の割合（{nt}・{sx}）", "value": float(100 * x.unknown.iloc[0] / x.total.iloc[0])})
for ver in ["imputed_2026retro", "imputed_2022"]:
    x = imp[(imp.year == 2020) & (imp.pref_code == 0) & (imp.imputed_version == ver)].iloc[0]
    rob.append({"check": f"2020年 65歳以上の割合 補完値（{ver}）", "value": float(x.s65_imputed)})
    rob.append({"check": f"2020年 65歳以上の割合 補完値−原数値（{ver}）", "value": float(x.d65)})
x = imp[(imp.year == 2015) & (imp.pref_code == 0)].iloc[0]
rob.append({"check": "2015年 65歳以上の割合 補完値−原数値（imputed_2022）", "value": float(x.d65)})
rob.append({"check": "2025年 15歳未満の割合 補完値−原数値", "value": float(I25.d014)})
rob.append({"check": "2025年 年齢不詳の割合 南関東4都県", "value": main["skanto_rate_2025"]})
rob.append({"check": "2025年 年齢不詳の割合 南関東以外", "value": main["rest_skanto_rate_2025"]})
r20 = imp[(imp.year == 2020) & (imp.pref_code > 0)]
a, b = r20[r20.imputed_version == "imputed_2026retro"].set_index("pref_code"), r20[r20.imputed_version == "imputed_2022"].set_index("pref_code")
rob.append({"check": "2020年 都道府県の65歳以上の割合 2つの補完値の差の最大（ポイント）", "value": float((a.s65_imputed - b.s65_imputed).abs().max())})
rob = pd.DataFrame(rob); rob.to_csv(R / "robustness.csv", index=False, float_format="%.5f", lineterminator="\n")
main["robustness"] = dict(zip(rob.check, rob.value.round(5)))
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
for k, v in main.items():
    print(k, v if not isinstance(v, float) else round(v, 4))
