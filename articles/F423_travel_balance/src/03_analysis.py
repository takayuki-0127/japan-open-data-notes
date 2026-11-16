"""03 分析：旅行収支の大きさ、受取の分解（人数×1人あたり、円・ドル）、サービス収支の中での位置、頑健性。
出力：results/main.json, results/annual_table.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def decomp(a, y0, y1, rec="travel_rec"):
    g = np.log(a.loc[y1, rec] / a.loc[y0, rec])
    gv = np.log(a.loc[y1, "visitors"] / a.loc[y0, "visitors"])
    pp0 = a.loc[y0, rec] / a.loc[y0, "visitors"]; pp1 = a.loc[y1, rec] / a.loc[y1, "visitors"]
    gp = np.log(pp1 / pp0)
    ppu0 = a.loc[y0, "travel_rec_usd"] / a.loc[y0, "visitors"]; ppu1 = a.loc[y1, "travel_rec_usd"] / a.loc[y1, "visitors"]
    return dict(y0=y0, y1=y1, rec_growth_pct=float((np.exp(g) - 1) * 100), visitors_growth_pct=float((np.exp(gv) - 1) * 100),
                per_visitor_yen_growth_pct=float((np.exp(gp) - 1) * 100), share_visitors=float(gv / g * 100), share_per_visitor=float(gp / g * 100),
                per_visitor_yen0=float(pp0 * 1e8), per_visitor_yen1=float(pp1 * 1e8),
                per_visitor_usd0=float(ppu0 * 1e8), per_visitor_usd1=float(ppu1 * 1e8),
                per_visitor_usd_growth_pct=float((ppu1 / ppu0 - 1) * 100))


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    m = pd.read_csv(D / "monthly.csv").set_index("ym")
    t = a[["travel_rec", "travel_pay", "travel", "transport", "other_services", "services"]] / 1e4
    t["services_ex_travel"] = t.services - t.travel
    t["visitors_man"] = a.visitors / 1e4
    t["rec_per_visitor_yen"] = a.travel_rec / a.visitors * 1e8
    t["rec_per_visitor_usd"] = a.travel_rec_usd / a.visitors * 1e8
    t.round(4).to_csv(R / "annual_table.csv")
    d = decomp(a, 2019, 2025)
    y = t.loc[2025]
    main = dict(travel_2025=float(y.travel), travel_rec_2025=float(y.travel_rec), travel_pay_2025=float(y.travel_pay),
                travel_2019=float(t.loc[2019, "travel"]), travel_ratio_2025_2019=float(y.travel / t.loc[2019, "travel"]),
                first_surplus_year=int(t.index[(t.travel > 0)][0]), travel_1996=float(t.loc[1996, "travel"]),
                services_2025=float(y.services), services_ex_travel_2025=float(y.services_ex_travel),
                transport_2025=float(y.transport), other_services_2025=float(y.other_services),
                visitors_2019=float(a.loc[2019, "visitors"]), visitors_2025=float(a.loc[2025, "visitors"]),
                **{"d_" + k: v for k, v in d.items() if k not in ("y0", "y1")},
                usdjpy_2019=float(a.loc[2019, "usdjpy"]), usdjpy_2025=float(a.loc[2025, "usdjpy"]),
                travel_max_year=int(t.travel.idxmax()))
    main["H1"] = "支持" if main["travel_ratio_2025_2019"] >= 1.5 else "外れ"
    main["H2"] = "支持" if d["share_per_visitor"] > d["share_visitors"] else "外れ"
    main["H3"] = "支持" if d["per_visitor_usd_growth_pct"] < 10 else "外れ"
    main["H4"] = "支持" if -main["services_ex_travel_2025"] > main["travel_2025"] else "外れ"
    # 頑健性
    rob = []
    for y0 in (2019, 2018, 2015):
        dd = decomp(a, y0, 2025); rob.append(dict(check=f"基準 {y0}年→2025年", **{k: dd[k] for k in ["rec_growth_pct", "visitors_growth_pct", "per_visitor_yen_growth_pct", "share_per_visitor", "per_visitor_usd_growth_pct"]}))
    dd = decomp(a, 2019, 2025, rec="travel_rec_personal")
    rob.append(dict(check="業務外の受取だけ 2019→2025年", **{k: dd[k] for k in ["rec_growth_pct", "visitors_growth_pct", "per_visitor_yen_growth_pct", "share_per_visitor"]}, per_visitor_usd_growth_pct=np.nan))
    roll = m[["travel", "services", "travel_rec", "visitors"]].rolling(12).sum().dropna()
    last = roll.iloc[-1]
    rob.append(dict(check=f"最新の12か月（{int(roll.index[-1])}まで）", rec_growth_pct=np.nan, visitors_growth_pct=np.nan,
                    per_visitor_yen_growth_pct=np.nan, share_per_visitor=np.nan, per_visitor_usd_growth_pct=np.nan,
                    travel=float(last.travel / 1e4), services_ex_travel=float((last.services - last.travel) / 1e4)))
    pd.DataFrame(rob).round(3).to_csv(R / "robustness.csv", index=False)
    main["latest_12m_end"] = int(roll.index[-1]); main["latest_12m_travel"] = float(last.travel / 1e4)
    main["latest_12m_services_ex_travel"] = float((last.services - last.travel) / 1e4)
    # 月ごとの1人あたり（2025年）
    mm = m[(m.year == 2025)]
    ppm = mm.travel_rec / mm.visitors * 1e8
    main["per_visitor_month_min"] = float(ppm.min()); main["per_visitor_month_max"] = float(ppm.max())
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print(t.loc[[1996, 2003, 2010, 2014, 2015, 2019, 2023, 2024, 2025]].round(2).to_string())


if __name__ == "__main__":
    main()
