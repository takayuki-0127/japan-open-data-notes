"""家計調査とGDPの消費の比較：指数、差の分解、前年比の相関、仮説、頑健性（オフライン、乱数なし）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def L(d, c, a, b):
    return float(np.log(d.loc[b, c] / d.loc[a, c]))


def decomp(d, a, b, gdp_col="gdp_hh_exrent_nom", hh_col="households"):
    tp = L(d, "tp_cons_month", a, b)              # 二人以上・1世帯あたり（名目）
    th = L(d, "th_cons_year", a, b)               # 総世帯・1世帯あたり（名目）
    agg = th + L(d, hh_col, a, b)                 # 総世帯×世帯数（名目の総額）
    gd = L(d, gdp_col, a, b)                      # GDP（名目）
    gap = gd - tp
    return dict(start=a, end=b, two_plus=tp, total_hh=th, survey_aggregate=agg, gdp=gd, gap=gap,
                part_coverage=th - tp, part_households=agg - th, part_residual=gd - agg,
                share_closed_by_households=(agg - tp) / gap if gap != 0 else np.nan)


def main():
    RES.mkdir(exist_ok=True)
    d = pd.read_csv(ROOT / "data" / "annual.csv").set_index("year")
    # 実質の指数（二人以上：実質増減率をつなぐ、2000年＝100）
    idx = [100.0]
    for y in range(2001, 2026):
        idx.append(idx[-1] * (1 + d.loc[y, "tp_real_growth"] / 100))
    d["tp_real_idx"] = idx
    for c in ["tp_cons_month", "th_cons_year", "gdp_hh_exrent_nom", "gdp_hh_nom", "gdp_hh_exrent_real", "gdp_hh_real"]:
        d[c + "_idx"] = d[c] / d.loc[2000, c] * 100
    d["survey_agg_nom"] = d.th_cons_year * d.households / 1e9   # 10億円
    d["survey_agg_idx"] = d.survey_agg_nom / d.loc[2000, "survey_agg_nom"] * 100
    d["survey_agg_share_of_gdp_exrent"] = d.survey_agg_nom / d.gdp_hh_exrent_nom * 100
    d["gdp_exrent_real_per_person_idx"] = (d.gdp_hh_exrent_real / d.persons) / (d.loc[2000, "gdp_hh_exrent_real"] / d.loc[2000, "persons"]) * 100
    d["gdp_exrent_nom_per_household"] = d.gdp_hh_exrent_nom * 1e9 / d.households   # 円/年
    d.round(4).to_csv(RES / "annual_indicators.csv")
    dc = pd.DataFrame([decomp(d, 2000, 2025), decomp(d, 2005, 2025), decomp(d, 2010, 2025), decomp(d, 2000, 2019)])
    dc.round(4).to_csv(RES / "decomposition.csv", index=False)
    m = dc.iloc[0]
    g_s = d.tp_real_idx.pct_change() * 100; g_g = d.gdp_hh_exrent_real.pct_change() * 100
    ok = ~(g_s.isna() | g_g.isna())
    r_all = float(np.corrcoef(g_s[ok], g_g[ok])[0, 1])
    ok2 = ok & (~d.index.isin([2020, 2021]))
    r_ex = float(np.corrcoef(g_s[ok2], g_g[ok2])[0, 1])
    v = lambda y, c: float(d.loc[y, c])
    hyp = {
        "H1": dict(rule="二人以上の1世帯あたり（名目）が減り、GDP（除く帰属家賃、名目）が増えたら支持", two_plus_ratio=v(2025, "tp_cons_month") / v(2000, "tp_cons_month"),
                   gdp_ratio=v(2025, "gdp_hh_exrent_nom") / v(2000, "gdp_hh_exrent_nom"),
                   verdict="支持" if (v(2025, "tp_cons_month") < v(2000, "tp_cons_month") and v(2025, "gdp_hh_exrent_nom") > v(2000, "gdp_hh_exrent_nom")) else "外れ"),
        "H2": dict(rule="総世帯×世帯数でGDPとの差の半分以上が埋まれば支持", share=float(m.share_closed_by_households), verdict="支持" if m.share_closed_by_households >= 0.5 else "外れ"),
        "H3": dict(rule="二人以上の実質が10%以上減り、GDP実質（除く帰属家賃）1人あたりが±5%の中なら支持", tp_real=v(2025, "tp_real_idx"), gdp_real_pp=v(2025, "gdp_exrent_real_per_person_idx"),
                   verdict="支持" if (v(2025, "tp_real_idx") <= 90 and abs(v(2025, "gdp_exrent_real_per_person_idx") - 100) <= 5) else "外れ"),
        "H4": dict(rule="前年比の相関が0.5未満なら支持", corr=r_all, corr_excl_2020_21=r_ex, verdict="支持" if r_all < 0.5 else "外れ"),
    }
    # 頑健性
    rob = [dict(check="GDPに帰属家賃を含める（2000→2025年）", **{k: v_ for k, v_ in decomp(d, 2000, 2025, gdp_col="gdp_hh_nom").items() if k in ("gap", "share_closed_by_households")}),
           dict(check="世帯数を直線で補う（2000→2025年）", **{k: v_ for k, v_ in decomp(d, 2000, 2025, hh_col="households_linear").items() if k in ("gap", "share_closed_by_households")})]
    for _, r in dc.iloc[1:].iterrows():
        rob.append(dict(check=f"起点・終点を変える（{int(r.start)}→{int(r.end)}年）", gap=r.gap, share_closed_by_households=r.share_closed_by_households))
    rb = pd.DataFrame(rob)
    rb["corr_growth"] = np.nan
    rb = pd.concat([rb, pd.DataFrame([dict(check="前年比の相関（2020・2021年を除く）", corr_growth=r_ex)])], ignore_index=True)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)
    main_ = dict(hypotheses=hyp, decomposition=dc.round(4).to_dict(orient="records"), robustness=rb.round(4).to_dict(orient="records"),
                 tp_2000=v(2000, "tp_cons_month"), tp_2025=v(2025, "tp_cons_month"), th_2000=v(2000, "th_cons_year"), th_2025=v(2025, "th_cons_year"),
                 gdp_exrent_2000=v(2000, "gdp_hh_exrent_nom"), gdp_exrent_2025=v(2025, "gdp_hh_exrent_nom"), households_2000=v(2000, "households"), households_2025=v(2025, "households"),
                 persons_2000=v(2000, "persons"), persons_2025=v(2025, "persons"), th_persons_2000=v(2000, "th_persons"), th_persons_2025=v(2025, "th_persons"),
                 survey_share_2000=v(2000, "survey_agg_share_of_gdp_exrent"), survey_share_2025=v(2025, "survey_agg_share_of_gdp_exrent"),
                 tp_real_idx_2025=v(2025, "tp_real_idx"), tp_real_idx_min=float(d.tp_real_idx.min()), tp_real_idx_min_year=int(d.tp_real_idx.idxmin()),
                 gdp_real_exrent_idx_2025=v(2025, "gdp_hh_exrent_real_idx"), gdp_real_pp_idx_2025=v(2025, "gdp_exrent_real_per_person_idx"))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(dc.round(3).to_string()); print(json.dumps(hyp, ensure_ascii=False)); print(rb.round(3).to_string())
    print({k: round(v_, 2) for k, v_ in main_.items() if isinstance(v_, float)})


if __name__ == "__main__":
    main()
