"""入学者の推移、進学の割合、分野別の変化、仮説の判定、頑健性（オフライン、乱数なし）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
Y0, Y1 = 2010, 2025


def main():
    RES.mkdir(exist_ok=True)
    at = pd.read_csv(ROOT / "data" / "admission_total.csv")
    af = pd.read_csv(ROOT / "data" / "admission_by_field.csv")
    g = pd.read_csv(ROOT / "data" / "graduates.csv").set_index("year")
    en = pd.read_csv(ROOT / "data" / "enrollment.csv").set_index("year")
    tot = at[at.sector == "計"].pivot(index="year", columns="course", values="entrants")
    app = at[at.sector == "計"].pivot(index="year", columns="course", values="applicants")
    fem = at[at.sector == "計"].pivot(index="year", columns="course", values="entrants_f")
    r = pd.DataFrame(index=tot.index)
    r["master"] = tot["修士"]; r["doctor"] = tot["博士"]; r["prof"] = tot["専門職"]
    r["master_app"] = app["修士"]; r["doctor_app"] = app["博士"]
    r["univ_grad"] = g.loc[r.index, "univ_grad"]; r["master_grad"] = g.loc[r.index, "master_grad"]
    r["master_rate_pct"] = r.master / r.univ_grad * 100
    r["doctor_rate_pct"] = r.doctor / r.master_grad * 100
    r["doctor_rate_lag2_pct"] = r.doctor / r.master.shift(2) * 100
    r["master_female_pct"] = fem["修士"] / r.master * 100
    r["doctor_female_pct"] = fem["博士"] / r.doctor * 100
    r.round(4).to_csv(RES / "totals_by_year.csv")

    # 分野別（修士・博士、設置者計）
    ff = af[(af.sector == "計") & (af.course.isin(["修士", "博士"]))].pivot_table(index=["course", "field"], columns="year", values="entrants")
    chg = pd.DataFrame({"y2010": ff[Y0], "y2025": ff[Y1]})
    chg["diff"] = chg.y2025 - chg.y2010
    chg["ratio"] = chg.y2025 / chg.y2010
    chg = chg.reset_index()
    chg.round(4).to_csv(RES / "field_change.csv", index=False)
    ff.reset_index().to_csv(RES / "field_by_year.csv", index=False)

    def fr(course, fields, a=Y0, b=Y1):
        q = ff.loc[course]
        return float(q.loc[fields, b].sum() / q.loc[fields, a].sum())

    v = lambda y, c: float(r.loc[y, c])
    hyp = {
        "H1": dict(rule="修士の入学者÷同年3月の学部卒業者 が2010→2025年度に1ポイント以上下がったら外れ", rate2010=v(Y0, "master_rate_pct"), rate2025=v(Y1, "master_rate_pct"),
                   verdict="外れ" if v(Y1, "master_rate_pct") <= v(Y0, "master_rate_pct") - 1 else "支持"),
        "H2": dict(rule="博士の入学者÷同年3月の修士修了者 が2010年度以上なら外れ", rate2010=v(Y0, "doctor_rate_pct"), rate2025=v(Y1, "doctor_rate_pct"),
                   verdict="支持" if v(Y1, "doctor_rate_pct") < v(Y0, "doctor_rate_pct") else "外れ"),
        "H3": dict(rule="博士の入学者の2025/2010 が理学＋工学で保健以上なら外れ", sci_eng=fr("博士", ["理学", "工学"]), health=fr("博士", ["保健"]),
                   verdict="支持" if fr("博士", ["理学", "工学"]) < fr("博士", ["保健"]) else "外れ"),
        "H4": dict(rule="専門職の入学者が2025年度に2010年度以上なら外れ", y2010=v(Y0, "prof"), y2025=v(Y1, "prof"),
                   verdict="支持" if v(Y1, "prof") < v(Y0, "prof") else "外れ"),
    }
    # 頑健性
    rob = []
    def add(name, m_ratio, d_ratio, note=""):
        rob.append(dict(check=name, master_ratio=m_ratio, doctor_ratio=d_ratio, note=note))
    add("本線：入学者 2025/2010", v(Y1, "master") / v(Y0, "master"), v(Y1, "doctor") / v(Y0, "doctor"))
    add("入学志願者 2025/2010", v(Y1, "master_app") / v(Y0, "master_app"), v(Y1, "doctor_app") / v(Y0, "doctor_app"))
    add("起点を2009年度に", v(Y1, "master") / v(2009, "master"), v(Y1, "doctor") / v(2009, "doctor"))
    add("起点を2015年度に", v(Y1, "master") / v(2015, "master"), v(Y1, "doctor") / v(2015, "doctor"))
    ex = [f for f in ff.loc["博士"].index if f != "保健"]
    add("博士から保健を除く", np.nan, fr("博士", ex))
    for s in ["国立", "公立", "私立"]:
        q = at[at.sector == s].pivot(index="year", columns="course", values="entrants")
        add(f"{s}だけ", float(q.loc[Y1, "修士"] / q.loc[Y0, "修士"]), float(q.loc[Y1, "博士"] / q.loc[Y0, "博士"]))
    add("割合（修士÷学部卒、博士÷修士修了）2025/2010", v(Y1, "master_rate_pct") / v(Y0, "master_rate_pct"), v(Y1, "doctor_rate_pct") / v(Y0, "doctor_rate_pct"))
    add("博士の割合の分母を2年前の修士入学者に", np.nan, v(Y1, "doctor_rate_lag2_pct") / v(2012, "doctor_rate_lag2_pct"), "起点は2012年度（2年前が2010年度）")
    rb = pd.DataFrame(rob)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)

    # 長い流れ：修了者と在籍者
    mg = g["master_grad"].dropna(); dg = g["doctor_grad"].dropna()
    long = dict(enrolled_peak_year=int(en.enrolled.idxmax()), enrolled_peak=float(en.enrolled.max()), enrolled_2025=float(en.loc[2025, "enrolled"]),
                enrolled_1990=float(en.loc[1990, "enrolled"]), enrolled_2011=float(en.loc[2011, "enrolled"]),
                master_grad_1990=float(g.loc[1990, "master_grad"]), master_grad_2025=float(g.loc[2025, "master_grad"]),
                master_grad_peak_year=int(mg.idxmax()), master_grad_peak=float(mg.max()),
                doctor_grad_1990=float(g.loc[1990, "doctor_grad"]), doctor_grad_peak_year=int(dg.idxmax()), doctor_grad_peak=float(dg.max()),
                doctor_grad_2025=float(g.loc[2025, "doctor_grad"]))
    mn = r.loc[Y0:Y1]
    main_ = dict(hypotheses=hyp, robustness=rb.round(4).to_dict(orient="records"), long=long,
                 master_2010=v(Y0, "master"), master_2025=v(Y1, "master"), master_min_year=int(mn.master.idxmin()), master_min=float(mn.master.min()),
                 doctor_2010=v(Y0, "doctor"), doctor_2025=v(Y1, "doctor"), doctor_min_year=int(mn.doctor.idxmin()), doctor_min=float(mn.doctor.min()),
                 doctor_2003_note="博士入学者の2009年度以前は集めていない",
                 prof_2009=v(2009, "prof"), prof_min_year=int(mn.prof.idxmin()), prof_min=float(mn.prof.min()),
                 univ_grad_2010=v(Y0, "univ_grad"), univ_grad_2025=v(Y1, "univ_grad"),
                 master_rate_min_year=int(mn.master_rate_pct.idxmin()), master_rate_min=float(mn.master_rate_pct.min()),
                 doctor_rate_min_year=int(mn.doctor_rate_pct.idxmin()), doctor_rate_min=float(mn.doctor_rate_pct.min()),
                 master_female_2010=v(Y0, "master_female_pct"), master_female_2025=v(Y1, "master_female_pct"),
                 doctor_female_2010=v(Y0, "doctor_female_pct"), doctor_female_2025=v(Y1, "doctor_female_pct"),
                 field_change=chg.round(4).to_dict(orient="records"))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(hyp, ensure_ascii=False)); print(rb.round(3).to_string()); print(json.dumps(long)); print(chg.round(3).to_string())
    print(r[["master", "doctor", "prof", "master_rate_pct", "doctor_rate_pct", "doctor_female_pct"]].round(2).to_string())


if __name__ == "__main__":
    main()
