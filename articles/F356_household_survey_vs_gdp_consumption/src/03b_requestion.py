"""問い直し（結果を見てから足した）。
GDPの実質家計消費（除く帰属家賃）は1人あたりで12%増えていたが、世帯数は22%増えている。
→ 同じ「1世帯あたり」「1人あたり」の単位にそろえて、実質で比べ直す。家計調査の総世帯（名目）は、GDPの家計消費デフレーター（除く帰属家賃）で実質化する。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def main():
    d = pd.read_csv(RES / "annual_indicators.csv").set_index("year")
    defl = d.gdp_hh_exrent_nom / d.gdp_hh_exrent_real
    defl = defl / defl.loc[2000]
    t = pd.DataFrame(index=d.index)
    t["gdp_real_per_household"] = (d.gdp_hh_exrent_real / d.households) / (d.loc[2000, "gdp_hh_exrent_real"] / d.loc[2000, "households"]) * 100
    t["gdp_real_per_person"] = d.gdp_exrent_real_per_person_idx
    t["survey_two_plus_real_per_household"] = d.tp_real_idx
    t["survey_total_real_per_household"] = (d.th_cons_year / defl) / d.loc[2000, "th_cons_year"] * 100
    t["survey_total_real_per_person"] = (d.th_cons_year / defl / d.th_persons) / (d.loc[2000, "th_cons_year"] / d.loc[2000, "th_persons"]) * 100
    t.round(4).to_csv(RES / "requestion_same_units.csv")
    out = {c: float(t.loc[2025, c]) for c in t.columns}
    out.update({c + "_2019": float(t.loc[2019, c]) for c in t.columns})
    out["deflator_2025"] = float(defl.loc[2025] * 100)
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(t.loc[[2000, 2010, 2019, 2020, 2025]].round(1).to_string()); print(round(out["deflator_2025"], 1))


if __name__ == "__main__":
    main()
