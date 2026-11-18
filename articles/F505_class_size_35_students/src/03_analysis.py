"""平均の人数・36人以上の割合・差の差・分解・都道府県（北から南）・仮説・頑健性。
出力：results/main.json、by_year.csv、sizebins_share.csv、did.csv、by_pref.csv、by_region.csv、robustness.csv"""
import json, math
import pandas as pd
from common import DATA, RES, PREFS, REGION, REGIONS

POLICY = {1: 2011, 2: 2021, 3: 2022, 4: 2023, 5: 2024, 6: 2025}  # 小学校の学年が35人の標準になった年度
BIG = ["36～40人", "41～45人", "46人", "47人", "48人", "49人", "50人以上"]


def r(x, n=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), n)


def main():
    RES.mkdir(exist_ok=True)
    gp = pd.read_csv(DATA / "grade_panel.csv")
    gp["avg"] = gp["pupils"] / gp["classes"]
    gp["avg_all"] = gp["pupils_all"] / gp["classes_all"]
    sb = pd.read_csv(DATA / "sizebins.csv")

    def A(school, ent, year, grade=0, col="avg"):
        v = gp[(gp.school == school) & (gp.entity == ent) & (gp.year == year) & (gp.grade == grade)][col]
        assert len(v) == 1, (school, ent, year, grade)
        return float(v.iloc[0])

    # 年度別・学年別の平均（公立と計）
    by_year = gp[gp.entity.isin(["公立", "計"])].copy()
    by_year = by_year.sort_values(["school", "entity", "grade", "year"]).reset_index(drop=True)
    by_year["diff_prev"] = by_year.groupby(["school", "entity", "grade"], sort=True)["avg"].diff()
    out = by_year[["school", "entity", "grade", "year", "classes", "pupils", "avg", "diff_prev", "classes_all", "pupils_all", "avg_all"]].copy()
    for c in ["avg", "diff_prev", "avg_all"]:
        out[c] = out[c].round(3)
    out.to_csv(RES / "by_year.csv", index=False)

    # 36人以上の割合（単式学級に対して）。36人以上の学級は単式学級にしかない（複式・特別支援は最大で20人）。
    sh = []
    for (school, ent, year), g in sb.groupby(["school", "entity", "year"], sort=True):
        if ent not in ("公立|単式学級", "計"):
            continue
        d = dict(zip(g.bin, g.n))
        big = sum(d.get(b, 0) for b in BIG)
        sh.append({"school": school, "entity": ent, "year": year, "classes": d["計"], "n_31_35": d["31～35人"],
                   "n_36_40": d["36～40人"], "n_36plus": big, "n_41plus": big - d["36～40人"],
                   "share_31_35": round(100 * d["31～35人"] / d["計"], 2), "share_36plus": round(100 * big / d["計"], 2)})
    sh = pd.DataFrame(sh)
    sh.to_csv(RES / "sizebins_share.csv", index=False)

    def S(school, ent, year, col="share_36plus"):
        v = sh[(sh.school == school) & (sh.entity == ent) & (sh.year == year)][col]
        return float(v.iloc[0])

    pub = by_year[(by_year.entity == "公立")]
    # H2：学年ごとに、前の年からの下がり幅が最も大きい年（2009〜2025年度）
    h2 = {}
    for g in range(1, 7):
        s = pub[(pub.school == "es") & (pub.grade == g) & (pub.year >= 2009)].set_index("year")["diff_prev"]
        h2[g] = {"policy_year": POLICY[g], "largest_drop_year": int(s.idxmin()), "largest_drop": r(s.min(), 3),
                 "drop_in_policy_year": r(s[POLICY[g]], 3)}

    # 差の差：その学年が35人になった年の下がり幅 −（同じ年のまだ35人でない学年の下がり幅の平均）
    def did(control):
        rows = []
        for g in range(1, 7):
            T = POLICY[g]
            dg = float(pub[(pub.school == "es") & (pub.grade == g) & (pub.year == T)]["diff_prev"].iloc[0])
            if control == "upper_es":
                hs = [h for h in range(g + 1, 7)]
                cs = [float(pub[(pub.school == "es") & (pub.grade == h) & (pub.year == T)]["diff_prev"].iloc[0]) for h in hs]
                ctrl_name = "小学校の上の学年" if hs else None
                if not hs:  # 小6は上の学年がないので中学校で代える
                    cs = [float(pub[(pub.school == "jh") & (pub.grade == h) & (pub.year == T)]["diff_prev"].iloc[0]) for h in range(1, 4)]
                    ctrl_name = "中学校1〜3年"
            elif control == "next_grade":
                if g < 6:
                    cs = [float(pub[(pub.school == "es") & (pub.grade == g + 1) & (pub.year == T)]["diff_prev"].iloc[0])]
                    ctrl_name = f"小学校{g + 1}年"
                else:
                    cs = [float(pub[(pub.school == "jh") & (pub.grade == 1) & (pub.year == T)]["diff_prev"].iloc[0])]
                    ctrl_name = "中学校1年"
            elif control == "jh":
                cs = [float(pub[(pub.school == "jh") & (pub.grade == h) & (pub.year == T)]["diff_prev"].iloc[0]) for h in range(1, 4)]
                ctrl_name = "中学校1〜3年"
            c = sum(cs) / len(cs)
            rows.append({"control": control, "grade": g, "year": T, "drop_treated": round(dg, 3), "control_group": ctrl_name,
                         "drop_control": round(c, 3), "did": round(dg - c, 3)})
        return rows

    did_rows = did("upper_es") + did("next_grade") + did("jh")
    dd = pd.DataFrame(did_rows)
    dd.to_csv(RES / "did.csv", index=False)
    did_main = dd[(dd.control == "upper_es") & (dd.grade >= 2)]

    # 分解：平均＝児童数÷学級数 → Δlog平均＝Δlog児童数 − Δlog学級数
    def decomp(school, ent, y0, y1, grade=0):
        p0, p1 = A(school, ent, y0, grade, "pupils"), A(school, ent, y1, grade, "pupils")
        c0, c1 = A(school, ent, y0, grade, "classes"), A(school, ent, y1, grade, "classes")
        return {"y0": y0, "y1": y1, "pupils0": p0, "pupils1": p1, "classes0": c0, "classes1": c1,
                "pupils_pct": r(100 * (p1 / p0 - 1), 2), "classes_pct": r(100 * (c1 / c0 - 1), 2),
                "avg0": r(p0 / c0, 2), "avg1": r(p1 / c1, 2), "avg_pct": r(100 * ((p1 / c1) / (p0 / c0) - 1), 2),
                "dlog_avg": r(100 * math.log((p1 / c1) / (p0 / c0)), 2), "dlog_pupils": r(100 * math.log(p1 / p0), 2),
                "dlog_classes": r(100 * math.log(c1 / c0), 2)}

    dec = {"es_2020_2025": decomp("es", "公立", 2020, 2025), "es_2015_2020": decomp("es", "公立", 2015, 2020),
           "jh_2020_2025": decomp("jh", "公立", 2020, 2025), "es_2010_2015": decomp("es", "公立", 2010, 2015)}

    # 都道府県（公立、単式学級の全学年）：2020→2025年度、北から南の順。36人以上の割合も。
    sbp = sb[(sb.school == "es") & sb.entity.isin(PREFS)]
    prow = []
    for p in PREFS:
        a0, a1 = A("es", p, 2020), A("es", p, 2025)
        big = {}
        for y in (2020, 2025):
            d = sbp[(sbp.entity == p) & (sbp.year == y)]
            dd_ = dict(zip(d.bin, d.n))
            big[y] = 100 * sum(dd_.get(b, 0) for b in BIG) / A("es", p, y, 0, "classes")
        prow.append({"pref": p, "region": REGION[p], "avg2020": round(a0, 2), "avg2025": round(a1, 2), "change": round(a1 - a0, 2),
                     "share36_2020": round(big[2020], 2), "share36_2025": round(big[2025], 2),
                     "jh_avg2020": round(A("jh", p, 2020), 2), "jh_avg2025": round(A("jh", p, 2025), 2),
                     "jh_change": round(A("jh", p, 2025) - A("jh", p, 2020), 2)})
    bp = pd.DataFrame(prow)
    bp.to_csv(RES / "by_pref.csv", index=False)
    rrow = []
    for reg in REGIONS:
        ps = [p for p in PREFS if REGION[p] == reg]
        def agg(school, y):
            q = gp[(gp.school == school) & gp.entity.isin(ps) & (gp.year == y) & (gp.grade == 0)]
            return q.pupils.sum() / q.classes.sum()
        rrow.append({"region": reg, "n_pref": len(ps), "avg2020": round(agg("es", 2020), 2), "avg2025": round(agg("es", 2025), 2),
                     "change": round(agg("es", 2025) - agg("es", 2020), 2),
                     "jh_change": round(agg("jh", 2025) - agg("jh", 2020), 2)})
    br = pd.DataFrame(rrow)
    br.to_csv(RES / "by_region.csv", index=False)

    # 仮説の判定
    es15, es20, es25 = A("es", "公立", 2015), A("es", "公立", 2020), A("es", "公立", 2025)
    jh20, jh25 = A("jh", "公立", 2020), A("jh", "公立", 2025)
    n_match = sum(1 for g in range(2, 7) if h2[g]["largest_drop_year"] == POLICY[g])
    s20, s25 = S("es", "公立|単式学級", 2020), S("es", "公立|単式学級", 2025)
    hyp = {
        "H1": {"drop_2020_2025": r(es25 - es20, 3), "drop_2015_2020": r(es20 - es15, 3),
               "verdict": "支持" if (es25 - es20) < (es20 - es15) and es25 < es20 else "外れ"},
        "H2": {"n_grades_policy_year_is_largest": n_match, "of": 5,
               "verdict": "支持" if n_match >= 4 else "外れ"},
        "H3": {"share36_2020": r(s20), "share36_2025": r(s25),
               "verdict": "支持" if s20 >= 10 and s25 <= 1 else "外れ"},
        "H4": {"es_drop": r(es25 - es20, 3), "jh_drop": r(jh25 - jh20, 3),
               "verdict": "支持" if (jh25 - jh20) > (es25 - es20) else "外れ"},
        "H5": {"pupils_pct": dec["es_2020_2025"]["pupils_pct"], "classes_pct": dec["es_2020_2025"]["classes_pct"],
               "verdict": "支持" if dec["es_2020_2025"]["classes_pct"] > dec["es_2020_2025"]["pupils_pct"] else "外れ"},
    }

    # 頑健性
    rob = []
    def add(name, school, ent, y0, y1, col):
        a0, a1 = A(school, ent, y0, 0, col), A(school, ent, y1, 0, col)
        rob.append({"check": name, "school": school, "entity": ent, "y0": y0, "y1": y1, "avg0": round(a0, 2), "avg1": round(a1, 2), "change": round(a1 - a0, 2)})
    add("本線（公立・単式学級）", "es", "公立", 2020, 2025, "avg")
    add("本線（公立・単式学級）", "jh", "公立", 2020, 2025, "avg")
    add("全学級（複式・特別支援を含む）", "es", "公立", 2020, 2025, "avg_all")
    add("全学級（複式・特別支援を含む）", "jh", "公立", 2020, 2025, "avg_all")
    add("国立・私立を含む計", "es", "計", 2020, 2025, "avg")
    add("国立・私立を含む計", "jh", "計", 2020, 2025, "avg")
    add("比べる年を変える", "es", "公立", 2019, 2025, "avg")
    add("比べる年を変える", "jh", "公立", 2019, 2025, "avg")
    add("比べる年を変える", "es", "公立", 2020, 2024, "avg")
    add("比べる年を変える", "jh", "公立", 2020, 2024, "avg")
    add("以前の5年（比べる相手）", "es", "公立", 2015, 2020, "avg")
    add("以前の5年（比べる相手）", "jh", "公立", 2015, 2020, "avg")
    rb = pd.DataFrame(rob)
    rb.to_csv(RES / "robustness.csv", index=False)

    # 2023年度の値の直し（2024年度の表の前年の行：単式学級の数が各学年33多い）。全体（計）の平均への影響
    rev = json.loads((DATA / "build_checks.json").read_text(encoding="utf-8"))
    rev_rows = [f for f in rev["failed"] if f[0] == "prev_year_row"]
    p23, c23 = A("es", "計", 2023, 0, "pupils"), A("es", "計", 2023, 0, "classes")
    add_c = sum(float(f[5]) - float(f[6]) for f in rev_rows)
    revision = {"n_cells": len(rev_rows), "added_classes": add_c, "avg2023_table": r(p23 / c23, 3),
                "avg2023_revised": r(p23 / (c23 + add_c), 3)}

    did_summary = {int(row.grade): {"year": int(row.year), "drop_treated": row.drop_treated, "drop_control": row.drop_control,
                                    "control": row.control_group, "did": row.did} for row in dd[dd.control == "upper_es"].itertuples()}
    main = {
        "es_public_avg": {str(y): r(A("es", "公立", y), 2) for y in (2008, 2010, 2015, 2019, 2020, 2021, 2022, 2023, 2024, 2025)},
        "jh_public_avg": {str(y): r(A("jh", "公立", y), 2) for y in (2008, 2010, 2015, 2019, 2020, 2021, 2022, 2023, 2024, 2025)},
        "es_public_avg_by_grade": {str(g): {str(y): r(A("es", "公立", y, g), 2) for y in (2010, 2011, 2020, 2021, 2022, 2023, 2024, 2025)} for g in range(1, 7)},
        "es_public_share36": {str(y): r(S("es", "公立|単式学級", y)) for y in range(2008, 2026)},
        "es_public_n36plus": {str(y): int(sh[(sh.school == "es") & (sh.entity == "公立|単式学級") & (sh.year == y)]["n_36plus"].iloc[0]) for y in (2008, 2020, 2024, 2025)},
        "es_public_share31_35": {str(y): r(S("es", "公立|単式学級", y, "share_31_35")) for y in (2008, 2020, 2025)},
        "jh_public_share36": {str(y): r(S("jh", "公立|単式学級", y)) for y in (2008, 2020, 2025)},
        "largest_drop_by_grade": {str(g): v for g, v in h2.items()},
        "did_upper_es": did_summary,
        "did_mean_grades2_6": r(did_main["did"].mean(), 3),
        "did_mean_grades3_6": r(did_main[did_main.grade >= 3]["did"].mean(), 3),
        "did_mean_grades3_6_jh_control": r(dd[(dd.control == "jh") & (dd.grade >= 3)]["did"].mean(), 3),
        "did_mean_grades3_6_next_grade": r(dd[(dd.control == "next_grade") & (dd.grade >= 3)]["did"].mean(), 3),
        "decomposition": dec,
        "pref": {"n_avg_down": int((bp.change < 0).sum()), "n_avg_up": int((bp.change > 0).sum()),
                 "change_min": r(bp.change.min()), "change_max": r(bp.change.max()), "change_median": r(bp.change.median()),
                 "n_share36_2020_ge10": int((bp.share36_2020 >= 10).sum()), "n_share36_2025_le1": int((bp.share36_2025 <= 1).sum()),
                 "share36_2025_max": r(bp.share36_2025.max()), "jh_n_down": int((bp.jh_change < 0).sum())},
        "region": {row.region: {"avg2020": row.avg2020, "avg2025": row.avg2025, "change": row.change, "jh_change": row.jh_change} for row in br.itertuples()},
        "hypotheses": hyp,
        "revision_2023": revision,
    }
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: main[k] for k in ["es_public_avg", "jh_public_avg", "es_public_share36", "hypotheses", "did_upper_es", "decomposition"]}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
