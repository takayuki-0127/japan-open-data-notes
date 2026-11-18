"""女性の割合の推移・時期別の上がり方・女性と男性の寄与の分解・大学院・女性の進む先・学科別・仮説・頑健性。
出力：results/main.json、share_by_year.csv、subfield_share.csv、robustness.csv"""
import json
import pandas as pd
from common import DATA, RES

GROUPS = {"理学": ["理学"], "工学": ["工学"], "理工": ["理学", "工学"], "理工農": ["理学", "工学", "農学"],
          "理工農その他": ["理学", "工学", "農学", "その他"], "保健": ["保健"], "人文科学": ["人文科学"],
          "社会科学": ["社会科学"], "教育": ["教育"], "全体": ["計"]}
SUBS = {"工学": ["機械工学", "電気通信工学", "土木建築工学", "応用化学", "経営工学", "その他"],
        "理学": ["数学", "物理学", "化学", "生物", "地学", "その他"]}


def r(x, n=2):
    return round(float(x), n)


def main():
    RES.mkdir(exist_ok=True)
    e = pd.read_csv(DATA / "entrants.csv", keep_default_na=False)
    top = e[e["sub"] == ""]

    def cnt(level, group, year, table="計"):
        q = top[(top.level == level) & (top.table == table) & (top.year == year) & top.field.isin(GROUPS[group])]
        assert len(q) == len(GROUPS[group]), (level, group, year, table)
        return float(q.female.sum()), float(q.male.sum()), float(q.total.sum())

    def share(level, group, year, table="計"):
        f, m, t = cnt(level, group, year, table)
        return 100 * f / t

    # 年度別の女性の割合
    rows = []
    for level in ("ug", "master", "doctor"):
        for g in GROUPS:
            for y in range(2000, 2026):
                f, m, t = cnt(level, g, y)
                rows.append({"level": level, "group": g, "year": y, "female": int(f), "male": int(m), "total": int(t),
                             "female_share": round(100 * f / t, 2)})
    sb = pd.DataFrame(rows)
    sb.to_csv(RES / "share_by_year.csv", index=False)

    # 学科別（学部）
    srows = []
    for fld, subs in SUBS.items():
        for s in subs:
            for y in range(2000, 2026):
                q = e[(e.level == "ug") & (e.table == "計") & (e.year == y) & (e.field == fld) & (e["sub"] == s)]
                assert len(q) == 1, (fld, s, y)
                q = q.iloc[0]
                srows.append({"field": fld, "sub": s, "year": y, "female": int(q.female), "total": int(q.total),
                              "female_share": round(100 * q.female / q.total, 2) if q.total else None})
    ss = pd.DataFrame(srows)
    ss.to_csv(RES / "subfield_share.csv", index=False)

    def S(level, g, y):
        return float(sb[(sb.level == level) & (sb.group == g) & (sb.year == y)].female_share.iloc[0])

    # H1：1年あたりの上がり方
    slope = {g: {"2000_2010": r((S("ug", g, 2010) - S("ug", g, 2000)) / 10, 3),
                 "2010_2025": r((S("ug", g, 2025) - S("ug", g, 2010)) / 15, 3)} for g in ("理学", "工学", "理工")}

    # H2：女性の割合の変化を、女性の人数の変化と男性の人数の変化に分ける（対称な分け方）
    def decomp(level, g, y0, y1):
        f0, m0, _ = cnt(level, g, y0)
        f1, m1, _ = cnt(level, g, y1)
        s = lambda f, m: 100 * f / (f + m)
        fe = 0.5 * ((s(f1, m0) - s(f0, m0)) + (s(f1, m1) - s(f0, m1)))
        me = 0.5 * ((s(f0, m1) - s(f0, m0)) + (s(f1, m1) - s(f1, m0)))
        return {"y0": y0, "y1": y1, "female0": int(f0), "female1": int(f1), "male0": int(m0), "male1": int(m1),
                "female_pct": r(100 * (f1 / f0 - 1)), "male_pct": r(100 * (m1 / m0 - 1)),
                "share0": r(s(f0, m0)), "share1": r(s(f1, m1)), "change": r(s(f1, m1) - s(f0, m0)),
                "female_effect": r(fe), "male_effect": r(me)}

    dec = {f"{lv}_{g}_{y0}_{y1}": decomp(lv, g, y0, y1) for lv in ("ug", "master", "doctor") for g in ("理学", "工学")
           for (y0, y1) in [(2000, 2025), (2000, 2010), (2010, 2025), (2020, 2025)]}

    # H4：女性の学部入学者のうち理学・工学に入る人の割合
    def dest(y, g="理工"):
        f, _, _ = cnt("ug", g, y)
        fa, ma, _ = cnt("ug", "全体", y)
        return 100 * f / fa
    def dest_m(y, g="理工"):
        _, m, _ = cnt("ug", g, y)
        _, ma, _ = cnt("ug", "全体", y)
        return 100 * m / ma
    destination = {str(y): {"women_to_stem": r(dest(y)), "men_to_stem": r(dest_m(y)), "women_to_eng": r(dest(y, "工学")),
                            "women_to_sci": r(dest(y, "理学"))} for y in (2000, 2010, 2020, 2025)}

    # 仮説の判定
    ch = lambda lv, g: S(lv, g, 2025) - S(lv, g, 2000)
    hyp = {
        "H1": {"工学": slope["工学"], "理学": slope["理学"],
               "verdict_eng": "支持" if slope["工学"]["2010_2025"] > slope["工学"]["2000_2010"] else "外れ",
               "verdict_sci": "支持" if slope["理学"]["2010_2025"] > slope["理学"]["2000_2010"] else "外れ"},
        "H2": {"female_effect": dec["ug_工学_2000_2025"]["female_effect"], "male_effect": dec["ug_工学_2000_2025"]["male_effect"],
               "verdict": "支持" if dec["ug_工学_2000_2025"]["female_effect"] > dec["ug_工学_2000_2025"]["male_effect"] else "外れ"},
        "H3": {"ug_eng": r(ch("ug", "工学")), "master_eng": r(ch("master", "工学")), "doctor_eng": r(ch("doctor", "工学")),
               "verdict_master": "支持" if ch("master", "工学") < ch("ug", "工学") else "外れ",
               "verdict_doctor": "支持" if ch("doctor", "工学") < ch("ug", "工学") else "外れ"},
        "H4": {"2000": r(dest(2000)), "2025": r(dest(2025)), "change": r(dest(2025) - dest(2000)),
               "verdict": "支持" if 0 < dest(2025) - dest(2000) < 2 else "外れ"},
    }

    # 頑健性：工学・理学の女性の割合の変化（2000→2025年度）を、定義や表を変えて
    rob = []
    def addr(name, g, y0, y1, table="計", avg3=False):
        if avg3:
            a0 = sum(cnt("ug", g, y, table)[0] for y in (y0, y0 + 1, y0 + 2)) / sum(cnt("ug", g, y, table)[2] for y in (y0, y0 + 1, y0 + 2)) * 100
            a1 = sum(cnt("ug", g, y, table)[0] for y in (y1 - 2, y1 - 1, y1)) / sum(cnt("ug", g, y, table)[2] for y in (y1 - 2, y1 - 1, y1)) * 100
        else:
            a0, a1 = share("ug", g, y0, table), share("ug", g, y1, table)
        rob.append({"check": name, "group": g, "y0": y0, "y1": y1, "share0": r(a0), "share1": r(a1), "change": r(a1 - a0)})
    for g in ("工学", "理学"):
        addr("本線（学部・計の表）", g, 2000, 2025)
        addr("昼間の表", g, 2000, 2025, "昼間")
        addr("修業年限4年の表", g, 2000, 2025, "4年")
        addr("年をずらす", g, 2001, 2024)
        addr("3年の平均どうし（2000〜02→2023〜25）", g, 2000, 2025, avg3=True)
    for g in ("理工", "理工農", "理工農その他"):
        addr("理工系の定義を変える", g, 2000, 2025)
    rb = pd.DataFrame(rob)
    rb.to_csv(RES / "robustness.csv", index=False)

    def sub_share(fld, s, y):
        return float(ss[(ss.field == fld) & (ss["sub"] == s) & (ss.year == y)].female_share.iloc[0])
    main = {
        "ug_share": {g: {str(y): r(S("ug", g, y)) for y in (2000, 2005, 2010, 2015, 2020, 2021, 2022, 2023, 2024, 2025)} for g in GROUPS},
        "master_share": {g: {str(y): r(S("master", g, y)) for y in (2000, 2010, 2020, 2025)} for g in ("理学", "工学", "全体")},
        "doctor_share": {g: {str(y): r(S("doctor", g, y)) for y in (2000, 2010, 2020, 2025)} for g in ("理学", "工学", "全体")},
        "ug_counts": {g: {str(y): dict(zip(["female", "male", "total"], [int(v) for v in cnt("ug", g, y)])) for y in (2000, 2010, 2020, 2025)} for g in ("理学", "工学", "全体")},
        "slope_pt_per_year": slope,
        "decomposition": dec,
        "destination": destination,
        "subfield_share": {f"{fld}|{s}": {str(y): (r(sub_share(fld, s, y)) if sub_share(fld, s, y) == sub_share(fld, s, y) else None) for y in (2000, 2010, 2025)} for fld, subs in SUBS.items() for s in subs},
        "hypotheses": hyp,
    }
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: main[k] for k in ["ug_share", "master_share", "doctor_share", "slope_pt_per_year", "destination", "hypotheses", "subfield_share"]}, ensure_ascii=False))
    print(rb.to_string())
    print({k: v for k, v in dec.items() if k.startswith("ug_工学") or k.startswith("ug_理学")})


if __name__ == "__main__":
    main()
