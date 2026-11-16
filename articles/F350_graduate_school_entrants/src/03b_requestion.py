"""問い直し（結果を見てから足した）。
1. 修士の「教育」は2010→2025年度に6割減った。教員養成の大学院が専門職（教職大学院）に移った分か？
2. 専門職が減っていないのはなぜか：法科大学院・教職大学院・それ以外に分ける。
3. 2010年度は特に多い年だったのか：修了者の長い系列で、修士修了者÷2年前の学部卒業者（進学の割合の長い目安）を見る。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def main():
    at = pd.read_csv(ROOT / "data" / "admission_total.csv")
    af = pd.read_csv(ROOT / "data" / "admission_by_field.csv")
    g = pd.read_csv(ROOT / "data" / "graduates.csv").set_index("year")
    t = at[at.sector == "計"].pivot(index="year", columns="course", values="entrants")
    m_edu = af[(af.course == "修士") & (af.sector == "計") & (af.field == "教育")].set_index("year").entrants
    prof = pd.DataFrame(dict(law=t["専門職のうち法科大学院"], teach=t["専門職のうち教職大学院"], prof_total=t["専門職"]))
    prof["other_prof"] = prof.prof_total - prof.law - prof.teach
    prof["master_edu"] = m_edu
    prof["edu_combined"] = prof.master_edu + prof.teach
    prof.to_csv(RES / "requestion_prof_edu.csv")
    lt = pd.DataFrame(dict(master_grad=g.master_grad, doctor_grad=g.doctor_grad, univ_grad=g.univ_grad))
    lt["master_grad_per_univ_grad_lag2_pct"] = lt.master_grad / lt.univ_grad.shift(2) * 100
    lt["doctor_grad_per_master_grad_lag3_pct"] = lt.doctor_grad / lt.master_grad.shift(3) * 100
    lt.to_csv(RES / "requestion_long_rates.csv")
    q = lambda d, y, c: float(d.loc[y, c])
    ml = lt["master_grad_per_univ_grad_lag2_pct"].dropna()
    ml = ml[ml.index >= 1970]
    out = dict(
        master_edu_2010=q(prof, 2010, "master_edu"), master_edu_2025=q(prof, 2025, "master_edu"),
        teach_2010=q(prof, 2010, "teach"), teach_2025=q(prof, 2025, "teach"),
        edu_combined_2010=q(prof, 2010, "edu_combined"), edu_combined_2025=q(prof, 2025, "edu_combined"),
        law_2009=q(prof, 2009, "law"), law_2010=q(prof, 2010, "law"), law_min_year=int(prof.law.idxmin()), law_min=float(prof.law.min()), law_2025=q(prof, 2025, "law"),
        other_prof_2010=q(prof, 2010, "other_prof"), other_prof_2025=q(prof, 2025, "other_prof"),
        long_master_rate_1990=q(lt, 1990, "master_grad_per_univ_grad_lag2_pct"), long_master_rate_2000=q(lt, 2000, "master_grad_per_univ_grad_lag2_pct"),
        long_master_rate_2012=q(lt, 2012, "master_grad_per_univ_grad_lag2_pct"), long_master_rate_2025=q(lt, 2025, "master_grad_per_univ_grad_lag2_pct"),
        long_master_rate_peak_year=int(ml.idxmax()), long_master_rate_peak=float(ml.max()),
        master_grad_1980=q(lt, 1980, "master_grad"), master_grad_2000=q(lt, 2000, "master_grad"),
    )
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(prof.to_string())


if __name__ == "__main__":
    main()
