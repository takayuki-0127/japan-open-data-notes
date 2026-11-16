"""名目・実質・デフレーターの期間ごとの年率、交易利得、仮説の判定、頑健性（オフライン、乱数なし）。年率は対数の差÷年数（%）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
PERIODS = [(1994, 2012), (2012, 2019), (2019, 2025), (1994, 2025)]


def rate(d, c, a, b, geo=False):
    if geo:
        return float(((d.loc[b, c] / d.loc[a, c]) ** (1 / (b - a)) - 1) * 100)
    return float(np.log(d.loc[b, c] / d.loc[a, c]) / (b - a) * 100)


def table(d, periods, geo=False):
    rows = []
    for a, b in periods:
        r = dict(start=a, end=b)
        for c in ["nominal_gdp", "real_gdp", "defl_gdp", "defl_domestic_demand", "defl_pce", "defl_exports", "defl_imports", "real_gdi", "real_gni", "real_domestic_demand", "nominal_gni"]:
            r[c] = rate(d, c, a, b, geo)
        r["nominal_minus_real"] = r["nominal_gdp"] - r["real_gdp"]
        r["gdi_minus_gdp"] = r["real_gdi"] - r["real_gdp"]
        r["defl_gdp_minus_dd"] = r["defl_gdp"] - r["defl_domestic_demand"]
        r["nominal_deflated_by_pce"] = r["nominal_gdp"] - r["defl_pce"]
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    RES.mkdir(exist_ok=True)
    d = pd.read_csv(ROOT / "data" / "annual.csv").set_index("year")
    d["trading_gains_pct_gdp"] = d.trading_gains / d.real_gdp * 100
    d["terms_of_trade"] = d.defl_exports / d.defl_imports * 100
    d["nominal_idx"] = d.nominal_gdp / d.loc[1994, "nominal_gdp"] * 100
    d["real_idx"] = d.real_gdp / d.loc[1994, "real_gdp"] * 100
    d["real_gdi_idx"] = d.real_gdi / d.loc[1994, "real_gdi"] * 100
    d.round(4).to_csv(RES / "annual_indicators.csv")
    t = table(d, PERIODS)
    t.round(4).to_csv(RES / "period_rates.csv", index=False)
    p = t.set_index(["start", "end"])
    a, b, c = p.loc[(1994, 2012)], p.loc[(2019, 2025)], p.loc[(1994, 2025)]
    hyp = {
        "H1": dict(rule="1994〜2012年、実質の年率 > 名目の年率なら支持", real=a.real_gdp, nominal=a.nominal_gdp, verdict="支持" if a.real_gdp > a.nominal_gdp else "外れ"),
        "H2": dict(rule="2019〜2025年、名目−実質が年率2ポイント以上なら支持", diff=b.nominal_minus_real, verdict="支持" if b.nominal_minus_real >= 2 else "外れ"),
        "H3": dict(rule="2019〜2025年、実質GDIの伸び < 実質GDPの伸びなら支持", gdi=b.real_gdi, gdp=b.real_gdp, verdict="支持" if b.real_gdi < b.real_gdp else "外れ"),
        "H4": dict(rule="2019〜2025年、GDPデフレーターの上がり < 国内需要デフレーターの上がりなら支持", gdp_defl=b.defl_gdp, dd_defl=b.defl_domestic_demand,
                   verdict="支持" if b.defl_gdp < b.defl_domestic_demand else "外れ"),
    }
    rob = table(d, [(1997, 2013), (2013, 2020), (2020, 2025)])
    rob["kind"] = "区切りを1年ずらす"
    geo = table(d, PERIODS, geo=True); geo["kind"] = "幾何平均の年率"
    rb = pd.concat([rob, geo], ignore_index=True)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)
    v = lambda y, col: float(d.loc[y, col])
    main_ = dict(hypotheses=hyp, periods=t.round(4).to_dict(orient="records"), robustness=rb.round(4).to_dict(orient="records"),
                 nominal_1994=v(1994, "nominal_gdp"), nominal_2025=v(2025, "nominal_gdp"), real_1994=v(1994, "real_gdp"), real_2025=v(2025, "real_gdp"),
                 nominal_ratio_2025_1994=v(2025, "nominal_gdp") / v(1994, "nominal_gdp"), real_ratio_2025_1994=v(2025, "real_gdp") / v(1994, "real_gdp"),
                 gdi_ratio_2025_1994=v(2025, "real_gdi") / v(1994, "real_gdi"),
                 defl_gdp_1994=v(1994, "defl_gdp"), defl_gdp_2025=v(2025, "defl_gdp"), defl_gdp_min_year=int(d.defl_gdp.idxmin()), defl_gdp_min=float(d.defl_gdp.min()),
                 defl_dd_1994=v(1994, "defl_domestic_demand"), defl_dd_2025=v(2025, "defl_domestic_demand"),
                 defl_imp_1994=v(1994, "defl_imports"), defl_imp_2025=v(2025, "defl_imports"), defl_exp_1994=v(1994, "defl_exports"), defl_exp_2025=v(2025, "defl_exports"),
                 tg_pct_1994=v(1994, "trading_gains_pct_gdp"), tg_pct_2019=v(2019, "trading_gains_pct_gdp"), tg_pct_2025=v(2025, "trading_gains_pct_gdp"),
                 tg_pct_min_year=int(d.trading_gains_pct_gdp.idxmin()), tg_pct_min=float(d.trading_gains_pct_gdp.min()),
                 nominal_peak_before_2012=float(d.loc[:2012, "nominal_gdp"].max()), nominal_peak_before_2012_year=int(d.loc[:2012, "nominal_gdp"].idxmax()),
                 nominal_2012=v(2012, "nominal_gdp"), real_2012=v(2012, "real_gdp"))
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(t.round(2).T.to_string()); print(json.dumps(hyp, ensure_ascii=False))
    print({k: round(v_, 3) if isinstance(v_, float) else v_ for k, v_ in main_.items() if k not in ("hypotheses", "periods", "robustness")})


if __name__ == "__main__":
    main()
