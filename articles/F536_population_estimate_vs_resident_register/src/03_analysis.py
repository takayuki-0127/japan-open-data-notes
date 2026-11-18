"""03_analysis.py：住民基本台帳（10月1日に按分）÷ 人口推計 − 1 を、全国・都道府県・年齢で出す。
都道府県は北から南（コードの順）に並べ、地方別にもまとめる。順位は出さない。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "population_long.csv")
PREF = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
REGION = {1: "北海道", **{c: "東北" for c in range(2, 8)}, **{c: "関東" for c in range(8, 15)}, **{c: "中部" for c in range(15, 24)},
          **{c: "近畿" for c in range(24, 31)}, **{c: "中国" for c in range(31, 36)}, **{c: "四国" for c in range(36, 40)},
          **{c: "九州・沖縄" for c in range(40, 48)}}
YEARS = list(range(2014, 2025))


def series(source, kind, age="total"):
    s = d[(d["source"].isin(source if isinstance(source, list) else [source])) & (d["kind"] == kind) & (d["age"] == age)]
    return s.pivot_table(index="pref", columns="year", values="value", aggfunc="first")


J = {k: series("juki", k) for k in ["total", "japanese"]}
J["foreign"] = J["total"] - J["japanese"]
S = {k: series(["suikei_revised", "suikei_census"], k) for k in ["total", "japanese"]}
S["foreign"] = S["total"] - S["japanese"]
SO = {k: series("suikei_original", k) for k in ["total", "japanese"]}


def oct1(Jk, t):  # t年1月1日とt+1年1月1日の間を直線で按分して10月1日の値に
    return 0.25 * Jk[t] + 0.75 * Jk[t + 1]


# 全国
nat = []
for t in YEARS:
    row = dict(year=t)
    for k in ["total", "japanese", "foreign"]:
        jo = float(oct1(J[k], t).sum()); su = float(S[k][t].sum()); jn = float(J[k][t + 1].sum())
        row[f"juki_oct_{k}"] = round(jo); row[f"suikei_{k}"] = round(su)
        row[f"gap_{k}"] = round(jo - su); row[f"gap_{k}_pct"] = round(100 * (jo / su - 1), 3)
        row[f"gap_noint_{k}_pct"] = round(100 * (jn / su - 1), 3)  # 按分しない（t+1年1月1日）
    nat.append(row)
NAT = pd.DataFrame(nat); NAT.to_csv(R / "national_gap.csv", index=False)

# 都道府県
pref_rows = []
for t in YEARS:
    for k in ["total", "japanese"]:
        jo = oct1(J[k], t); su = S[k][t]
        for c in range(1, 48):
            pref_rows.append(dict(year=t, kind=k, pref=c, name=PREF[c - 1], region=REGION[c], juki_oct=round(float(jo[c])), suikei=float(su[c]),
                                  gap=round(float(jo[c] - su[c])), gap_pct=round(100 * float(jo[c] / su[c] - 1), 3),
                                  # 丸めの範囲（人口推計は千人単位、±500人）
                                  gap_pct_lo=round(100 * float(jo[c] / (su[c] + 500) - 1), 3), gap_pct_hi=round(100 * float(jo[c] / (su[c] - 500) - 1), 3)))
P = pd.DataFrame(pref_rows); P.to_csv(R / "pref_gap.csv", index=False)
reg = P[P["kind"] == "total"].groupby(["year", "region"], sort=False)[["juki_oct", "suikei"]].sum().reset_index()
reg["gap_pct"] = (100 * (reg["juki_oct"] / reg["suikei"] - 1)).round(3)
reg.to_csv(R / "region_gap.csv", index=False)

# 国勢調査による直し：2019年（補間補正 ÷ 公表時 − 1）
rev = pd.DataFrame({"pref": range(1, 48), "name": PREF, "region": [REGION[c] for c in range(1, 48)],
                    "original_2019": SO["total"][2019].values, "revised_2019": S["total"][2019].values})
rev["revision_pct"] = (100 * (rev["revised_2019"] / rev["original_2019"] - 1)).round(3)
rev["juki_oct_2019"] = oct1(J["total"], 2019).round().values
rev["gap_vs_original_pct"] = (100 * (rev["juki_oct_2019"] / rev["original_2019"] - 1)).round(3)
rev["gap_vs_revised_pct"] = (100 * (rev["juki_oct_2019"] / rev["revised_2019"] - 1)).round(3)
rev.to_csv(R / "census_revision_2019.csv", index=False)
nat_rev = {k: round(100 * (S[k][2019].sum() / SO[k][2019].sum() - 1), 3) for k in ["total", "japanese"]}
nat_rev_persons = {k: int(S[k][2019].sum() - SO[k][2019].sum()) for k in ["total", "japanese"]}
nat_rev["foreign_persons"] = int((S["total"][2019].sum() - S["japanese"][2019].sum()) - (SO["total"][2019].sum() - SO["japanese"][2019].sum()))

# 年齢別（2024年、2020年）
AGES = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85+"]
age_rows = []
for t in [2020, 2024]:
    sa = d[(d["source"] == "suikei_age") & (d["year"] == t)].pivot_table(index="pref", columns="age", values="value")
    ja = {}
    for y in (t, t + 1):
        g = d[(d["source"] == "juki_age") & (d["year"] == y)].pivot_table(index="pref", columns="age", values="value")
        g["85+"] = g[["85-89", "90-94", "95-99", "100+"]].sum(axis=1)
        ja[y] = g
    jo = 0.25 * ja[t] + 0.75 * ja[t + 1]
    for a in AGES + ["total"]:
        for c in range(1, 48):
            age_rows.append(dict(year=t, age=a, pref=c, name=PREF[c - 1], region=REGION[c], juki_oct=round(float(jo.loc[c, a])),
                                 suikei=float(sa.loc[c, a]), gap_pct=round(100 * float(jo.loc[c, a] / sa.loc[c, a] - 1), 3)))
        age_rows.append(dict(year=t, age=a, pref=0, name="全国", region="全国", juki_oct=round(float(jo[a].sum())), suikei=float(sa[a].sum()),
                             gap_pct=round(100 * float(jo[a].sum() / sa[a].sum() - 1), 3)))
A = pd.DataFrame(age_rows); A.to_csv(R / "age_gap.csv", index=False)

# まとめ
p20 = P[(P["year"] == 2020) & (P["kind"] == "total")]
p24 = P[(P["year"] == 2024) & (P["kind"] == "total")]
a24 = A[(A["year"] == 2024) & (A["pref"] > 0) & (A["age"] == "20-24")]
a20 = A[(A["year"] == 2020) & (A["pref"] > 0) & (A["age"] == "20-24")]
nat_age = {t: A[(A["year"] == t) & (A["pref"] == 0)].set_index("age")["gap_pct"].to_dict() for t in [2020, 2024]}
main = {
    "national": NAT.set_index("year")[["gap_total", "gap_total_pct", "gap_japanese_pct", "gap_foreign_pct", "gap_noint_total_pct", "juki_oct_total", "suikei_total"]].to_dict(orient="index"),
    "pref_2020_n_juki_more": int((p20["gap_pct"] > 0).sum()),
    "pref_2024_n_juki_more": int((p24["gap_pct"] > 0).sum()),
    "pref_2020_gap_range": [float(p20["gap_pct"].min()), float(p20["gap_pct"].max())],
    "pref_2024_gap_range": [float(p24["gap_pct"].min()), float(p24["gap_pct"].max())],
    "pref_2020_sign_uncertain_by_rounding": int(((p20["gap_pct_lo"] < 0) & (p20["gap_pct_hi"] > 0)).sum()),
    "pref_2024_sign_uncertain_by_rounding": int(((p24["gap_pct_lo"] < 0) & (p24["gap_pct_hi"] > 0)).sum()),
    "pref_juki_less": {str(t): P[(P["year"] == t) & (P["kind"] == "total") & (P["gap_pct"] < 0)]["name"].tolist() for t in [2014, 2020, 2024]},
    "region_2020": reg[reg["year"] == 2020].set_index("region")["gap_pct"].to_dict(),
    "region_2024": reg[reg["year"] == 2024].set_index("region")["gap_pct"].to_dict(),
    "census_revision_2019_national_pct": nat_rev, "census_revision_2019_persons": nat_rev_persons,
    "national_gap_2019_vs_original_pct": round(100 * (float(rev["juki_oct_2019"].sum()) / float(rev["original_2019"].sum()) - 1), 3),
    "national_gap_2019_vs_revised_pct": round(100 * (float(rev["juki_oct_2019"].sum()) / float(rev["revised_2019"].sum()) - 1), 3),
    "census_revision_n_within_1pct": int((rev["revision_pct"].abs() <= 1).sum()),
    "census_revision_range": [float(rev["revision_pct"].min()), float(rev["revision_pct"].max())],
    "age_20_24_n_ge5pct": {"2024": int((a24["gap_pct"] >= 5).sum()), "2020": int((a20["gap_pct"] >= 5).sum())},
    "age_20_24_n_negative": {"2024": int((a24["gap_pct"] < 0).sum()), "2020": int((a20["gap_pct"] < 0).sum())},
    "age_national_gap_pct": {str(k): v for k, v in nat_age.items()},
}
n = main["national"]
H = {
    "H1": dict(min_gap_pct=float(NAT["gap_total_pct"].min()), rule="all>0", supported=bool((NAT["gap_total_pct"] > 0).all())),
    "H2": dict(n=main["pref_2020_n_juki_more"], rule=">=40", supported=main["pref_2020_n_juki_more"] >= 40),
    "H3": dict(n=main["age_20_24_n_ge5pct"]["2024"], rule=">=24", supported=main["age_20_24_n_ge5pct"]["2024"] >= 24),
    "H4": dict(n=main["census_revision_n_within_1pct"], rule=">=40", supported=main["census_revision_n_within_1pct"] >= 40),
}
main["hypotheses"] = H
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=float)
print(json.dumps(main, ensure_ascii=False, indent=1, default=float))
print(NAT.to_string())
