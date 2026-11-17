"""03 分析：残高の伸び、GDP 比、対外との比、増加の内訳（流れとそれ以外）、地域、頑健性。
出力：results/main.json, results/annual_table.csv, results/region_shares.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    r = pd.read_csv(D / "region.csv").set_index("year")
    a["gdp_ratio"] = a.inward / a.gdp * 100
    a["in_out_ratio"] = a.inward / a.outward * 100
    a["gdp_ratio_mv"] = a.inward_mv / a.gdp * 100
    a.round(4).to_csv(R / "annual_table.csv")
    sh = r.div(r["合計"], axis=0) * 100
    sh.round(3).to_csv(R / "region_shares.csv")

    def dec(y0, y1):
        inc = a.loc[y1, "inward"] - a.loc[y0, "inward"]
        fl = a.loc[y0 + 1:y1, "flow"].sum()
        return dict(y0=y0, y1=y1, increase=float(inc), flows=float(fl), other=float(inc - fl), flow_share=float(fl / inc * 100),
                    flow_equity=float(a.loc[y0 + 1:y1, "flow_equity"].sum()), flow_reinv=float(a.loc[y0 + 1:y1, "flow_reinv"].sum()),
                    flow_debt=float(a.loc[y0 + 1:y1, "flow_debt"].sum()))
    d = dec(2014, 2025)
    cagr = lambda c, y0, y1: float(((a.loc[y1, c] / a.loc[y0, c]) ** (1 / (y1 - y0)) - 1) * 100)
    need = float(((120 / a.loc[2025, "inward"]) ** (1 / 5) - 1) * 100)
    main = dict(inward_1996=float(a.loc[1996, "inward"]), inward_2014=float(a.loc[2014, "inward"]), inward_2025=float(a.loc[2025, "inward"]),
                inward_mult_2014_2025=float(a.loc[2025, "inward"] / a.loc[2014, "inward"]), inward_cagr_2014_2025=cagr("inward", 2014, 2025),
                outward_2025=float(a.loc[2025, "outward"]), outward_mult_2014_2025=float(a.loc[2025, "outward"] / a.loc[2014, "outward"]),
                gdp_ratio_2014=float(a.loc[2014, "gdp_ratio"]), gdp_ratio_2024=float(a.loc[2024, "gdp_ratio"]), gdp_ratio_1996=float(a.loc[1996, "gdp_ratio"]),
                in_out_2014=float(a.loc[2014, "in_out_ratio"]), in_out_2025=float(a.loc[2025, "in_out_ratio"]), in_out_1996=float(a.loc[1996, "in_out_ratio"]),
                **{f"dec_{k}": v for k, v in d.items() if k not in ("y0", "y1")},
                reinv_stock_2025=float(a.loc[2025, "inward_reinv"]), equity_stock_2025=float(a.loc[2025, "inward_equity"]), debt_stock_2025=float(a.loc[2025, "inward_debt"]),
                inward_mv_2025=float(a.loc[2025, "inward_mv"]), inward_mv_2014=float(a.loc[2014, "inward_mv"]), gdp_ratio_mv_2024=float(a.loc[2024, "gdp_ratio_mv"]),
                need_cagr_to_120_2030=need, flow_2025=float(a.loc[2025, "flow"]),
                region_eu_2014=float(sh.loc[2014, "欧州"]), region_eu_2025=float(sh.loc[2025, "欧州"]), region_na_2014=float(sh.loc[2014, "北米"]), region_na_2025=float(sh.loc[2025, "北米"]),
                region_asia_2014=float(sh.loc[2014, "アジア"]), region_asia_2025=float(sh.loc[2025, "アジア"]), region_us_2025=float(sh.loc[2025, "米国"]),
                region_sg_2025=float(sh.loc[2025, "シンガポール"]), region_sg_2014=float(sh.loc[2014, "シンガポール"]), region_cn_2025=float(sh.loc[2025, "中国"]),
                region_nl_2025=float(sh.loc[2025, "オランダ"]), region_gb_2025=float(sh.loc[2025, "英国"]), region_total_check_2025=float(r.loc[2025, "合計"]))
    main["H1"] = "支持" if main["inward_mult_2014_2025"] >= 2 else "外れ"
    main["H2"] = "支持" if main["gdp_ratio_2024"] < 10 else "外れ"
    main["H3"] = "支持" if d["flow_share"] >= 50 else "外れ"
    main["H4"] = "支持" if main["in_out_2025"] < 20 else "外れ"
    rob = []
    for y0 in (1996, 2005, 2014):
        dd = dec(y0, 2025)
        rob.append(dict(check=f"{y0}→2025年", increase=dd["increase"], flows=dd["flows"], flow_share=dd["flow_share"], cagr=cagr("inward", y0, 2025)))
    rob.append(dict(check="時価の推計値 2014→2025年", increase=float(a.loc[2025, "inward_mv"] - a.loc[2014, "inward_mv"]), flows=np.nan, flow_share=np.nan, cagr=cagr("inward_mv", 2014, 2025)))
    rob.append(dict(check="2030年に120兆円に届く年率（2025年から、目安）", increase=np.nan, flows=np.nan, flow_share=np.nan, cagr=need))
    pd.DataFrame(rob).round(3).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print(sh.loc[[2014, 2025]].round(1).T.to_string())


if __name__ == "__main__":
    main()
