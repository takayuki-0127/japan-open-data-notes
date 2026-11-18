"""期間別・地域別の推移、2018年度（山）との比較、増加の分解、仮説の判定、頑健性。結果は results/ に書く。"""
import json
import pandas as pd
from common import ROOT

D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
P = ["m_lt1", "m1_3", "m3_6", "m6_12", "y1plus", "unknown"]
LAB = {"m_lt1": "1か月未満", "m1_3": "1か月以上3か月未満", "m3_6": "3か月以上6か月未満", "m6_12": "6か月以上1年未満",
       "y1plus": "1年以上", "unknown": "不明"}
REG = ["アジア", "中東", "アフリカ", "大洋州", "北米", "中南米", "欧州", "その他・無記入"]
MID = {"m_lt1": 0.5, "m1_3": 2, "m3_6": 4.5, "m6_12": 9, "y1plus": 12, "unknown": 0}
MID_ALT = {"m_lt1": 0.75, "m1_3": 2, "m3_6": 4.5, "m6_12": 9, "y1plus": 18, "unknown": 0}


def r1(x):
    return round(float(x), 1)


panel = pd.read_csv(D / "panel_region_period.csv")
ari = pd.read_csv(D / "panel_ari.csv")
stu = pd.read_csv(D / "students.csv").set_index("year").students_univ_jc
long = pd.read_csv(D / "extract_long_mext.csv")


def by_year(df):
    t = df[df.region == "計"].set_index("year")[P + ["total"]].astype(int)
    t["m3plus"] = t.m3_6 + t.m6_12 + t.y1plus
    t["m6plus"] = t.m6_12 + t.y1plus
    return t


T = by_year(panel)
A = by_year(ari)
out = T.copy()
out["share_lt1_pct"] = (100 * T.m_lt1 / T.total).round(2)
out["months_total"] = sum(T[k] * v for k, v in MID.items())
out["students_univ_jc"] = stu
out["per10k_students"] = (T.total / stu * 1e4).round(2)
out["m3plus_per10k_students"] = (T.m3plus / stu * 1e4).round(2)
out.to_csv(R / "by_year.csv")


def recov(t, base, cols):
    return {c: r1(100 * t.loc[2024, c] / t.loc[base, c]) for c in cols}


cols = ["total", "m_lt1", "m1_3", "m3_6", "m6_12", "y1plus", "m3plus", "m6plus"]
peak = int(T.total.idxmax())
main = {
    "years": [int(T.index.min()), int(T.index.max())],
    "peak_year": peak,
    "total": {int(y): int(v) for y, v in T.total.items()},
    "total_2009": int(T.loc[2009, "total"]), "total_2018": int(T.loc[2018, "total"]), "total_2019": int(T.loc[2019, "total"]),
    "total_2020": int(T.loc[2020, "total"]), "total_2024": int(T.loc[2024, "total"]),
    "period_2018": {c: int(T.loc[2018, c]) for c in cols},
    "period_2019": {c: int(T.loc[2019, c]) for c in cols},
    "period_2024": {c: int(T.loc[2024, c]) for c in cols},
    "recovery_vs_2018_pct": recov(T, 2018, cols),
    "recovery_vs_2019_pct": recov(T, 2019, cols),
    "share_lt1_pct": {y: float(out.loc[y, "share_lt1_pct"]) for y in [2009, 2018, 2019, 2024]},
}
# 2009→2019 の増加を期間別に分ける
inc = {c: int(T.loc[2019, c] - T.loc[2009, c]) for c in P + ["total"]}
main["increase_2009_2019"] = inc
main["increase_2009_2019_share_pct"] = {c: r1(100 * inc[c] / inc["total"]) for c in P}
inc18 = {c: int(T.loc[2018, c] - T.loc[2009, c]) for c in P + ["total"]}
main["increase_2009_2018_share_pct"] = {c: r1(100 * inc18[c] / inc18["total"]) for c in P}
# 3か月以上の山の年
main["m3plus_peak_year"] = int(T.m3plus.idxmax())
main["m3plus_peak"] = int(T.m3plus.max())
main["m3plus_2009"] = int(T.loc[2009, "m3plus"])
# 留学の月数の合計（区分の中央の月数を置いた目安。推測の置き方）
mt = out.months_total
main["months_total"] = {int(y): int(round(v)) for y, v in mt.items()}
main["months_recovery_vs_2018_pct"] = r1(100 * mt[2024] / mt[2018])
main["months_per_person"] = {y: round(float(mt[y] / T.loc[y, "total"]), 2) for y in [2009, 2018, 2019, 2024]}

# 地域別
reg = panel[panel.region != "計"].copy()
rt = reg.pivot(index="year", columns="region", values="total").reindex(columns=REG).fillna(0).astype(int)
rt.to_csv(R / "by_region_total.csv")
rlt = reg.pivot(index="year", columns="region", values="m_lt1").reindex(columns=REG).fillna(0).astype(int)
reg["m3plus"] = reg.m3_6 + reg.m6_12 + reg.y1plus
r3 = reg.pivot(index="year", columns="region", values="m3plus").reindex(columns=REG).fillna(0).astype(int)
rows = []
for g in REG:
    rows.append({"region": g, "total_2018": int(rt.loc[2018, g]), "total_2024": int(rt.loc[2024, g]),
                 "recovery_total_pct": r1(100 * rt.loc[2024, g] / rt.loc[2018, g]) if rt.loc[2018, g] else None,
                 "lt1_2018": int(rlt.loc[2018, g]), "lt1_2024": int(rlt.loc[2024, g]),
                 "recovery_lt1_pct": r1(100 * rlt.loc[2024, g] / rlt.loc[2018, g]) if rlt.loc[2018, g] else None,
                 "m3plus_2018": int(r3.loc[2018, g]), "m3plus_2024": int(r3.loc[2024, g]),
                 "recovery_m3plus_pct": r1(100 * r3.loc[2024, g] / r3.loc[2018, g]) if r3.loc[2018, g] else None,
                 "share_of_total_2018_pct": r1(100 * rt.loc[2018, g] / T.loc[2018, "total"]),
                 "share_of_total_2024_pct": r1(100 * rt.loc[2024, g] / T.loc[2024, "total"])})
regdf = pd.DataFrame(rows)
regdf.to_csv(R / "by_region_recovery.csv", index=False)
main["region"] = {r["region"]: {k: v for k, v in r.items() if k != "region"} for r in rows}

# 仮説
rv = main["recovery_vs_2018_pct"]
h = {
    "H1": {"rule": "2024年度の合計 < 2018年度", "value": [main["total_2024"], main["total_2018"]],
           "verdict": "支持" if main["total_2024"] < main["total_2018"] else "外れ"},
    "H2": {"rule": "1か月未満の戻り ≥90% かつ 3か月以上の戻り <90%（2018年度比）", "value": [rv["m_lt1"], rv["m3plus"]],
           "verdict": "支持" if rv["m_lt1"] >= 90 and rv["m3plus"] < 90 else "外れ"},
    "H3": {"rule": "2009→2019年度の増加のうち1か月未満の分 ≥60%", "value": main["increase_2009_2019_share_pct"]["m_lt1"],
           "verdict": "支持" if main["increase_2009_2019_share_pct"]["m_lt1"] >= 60 else "外れ"},
    "H4": {"rule": "北米の戻り <100% かつ アジアの戻り > 北米の戻り（2018年度比）",
           "value": [main["region"]["北米"]["recovery_total_pct"], main["region"]["アジア"]["recovery_total_pct"]],
           "verdict": "支持" if main["region"]["北米"]["recovery_total_pct"] < 100 and
           main["region"]["アジア"]["recovery_total_pct"] > main["region"]["北米"]["recovery_total_pct"] else "外れ"},
}
main["hypotheses"] = h

# 頑健性
rob = []


def add(name, base_total, cur_total, base_lt1, cur_lt1, base_long, cur_long, note=""):
    rob.append({"check": name, "total_recovery_pct": r1(100 * cur_total / base_total),
                "lt1_recovery_pct": r1(100 * cur_lt1 / base_lt1) if base_lt1 is not None else None,
                "long_recovery_pct": r1(100 * cur_long / base_long), "note": note})


add("本線（合計、2018年度比、3か月以上）", T.loc[2018, "total"], T.loc[2024, "total"], T.loc[2018, "m_lt1"], T.loc[2024, "m_lt1"],
    T.loc[2018, "m3plus"], T.loc[2024, "m3plus"])
add("基準を2019年度にする", T.loc[2019, "total"], T.loc[2024, "total"], T.loc[2019, "m_lt1"], T.loc[2024, "m_lt1"],
    T.loc[2019, "m3plus"], T.loc[2024, "m3plus"])
add("協定ありだけ（2018年度比）", A.loc[2018, "total"], A.loc[2024, "total"], A.loc[2018, "m_lt1"], A.loc[2024, "m_lt1"],
    A.loc[2018, "m3plus"], A.loc[2024, "m3plus"])
add("長い留学を6か月以上にする", T.loc[2018, "total"], T.loc[2024, "total"], T.loc[2018, "m_lt1"], T.loc[2024, "m_lt1"],
    T.loc[2018, "m6plus"], T.loc[2024, "m6plus"])
s18, s24 = stu[2018], stu[2024]
add("在学者1万人あたり（大学＋短大の在学者で割る）", T.loc[2018, "total"] / s18, T.loc[2024, "total"] / s24,
    T.loc[2018, "m_lt1"] / s18, T.loc[2024, "m_lt1"] / s24, T.loc[2018, "m3plus"] / s18, T.loc[2024, "m3plus"] / s24,
    note=f"在学者 {int(s18)}→{int(s24)}人")
mt2 = sum(T[k] * v for k, v in MID_ALT.items())
rob.append({"check": "留学の月数の合計（区分の中央の月数）", "total_recovery_pct": main["months_recovery_vs_2018_pct"],
            "lt1_recovery_pct": None, "long_recovery_pct": None, "note": "1か月未満=0.5、1年以上=12か月と置く（推測の置き方）"})
rob.append({"check": "留学の月数の合計（置き方を変える）", "total_recovery_pct": r1(100 * mt2[2024] / mt2[2018]),
            "lt1_recovery_pct": None, "long_recovery_pct": None, "note": "1か月未満=0.75、1年以上=18か月と置く"})
lg = long.set_index("year")
lv = {2020: int(lg.loc[2021, "n_prev"]), 2021: int(lg.loc[2021, "n"]), 2022: int(lg.loc[2022, "n"]), 2023: int(lg.loc[2023, "n"])}
rob.append({"check": "別の統計：海外の機関が把握する日本人留学者（主に長期、暦年）", "total_recovery_pct": None,
            "lt1_recovery_pct": None, "long_recovery_pct": None,
            "note": "2020年 {0}、2021年 {1}、2022年 {2}、2023年 {3} 人".format(*[lv[y] for y in [2020, 2021, 2022, 2023]])})
robdf = pd.DataFrame(rob)
robdf.to_csv(R / "robustness.csv", index=False)
main["robustness"] = rob
main["long_mext"] = lv
main["long_mext_2023_vs_2020_pct"] = r1(100 * lv[2023] / lv[2020])
main["students"] = {int(y): int(v) for y, v in stu.items()}
main["students_change_2018_2024_pct"] = r1(100 * (s24 / s18 - 1))
json.dump(main, open(R / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: main[k] for k in ["total_2018", "total_2019", "total_2024", "recovery_vs_2018_pct", "recovery_vs_2019_pct",
                                      "increase_2009_2019_share_pct", "m3plus_peak_year", "months_recovery_vs_2018_pct",
                                      "months_per_person", "hypotheses", "share_lt1_pct"]}, ensure_ascii=False, indent=1))
print(regdf.to_string())
print(robdf.to_string())
