"""03b 問い直し：冬（12〜3月）は天気の説明力が高かった。冬は気温だけでどこまで説明できるか。
冬の月だけで、値段のずれを「当月と前月の気温のずれの平均」に回帰し、1℃あたりの値段の変化（%）を品目ごとに出す。
出力：results/requestion.json, results/winter_temp.csv
"""
import json, pathlib, importlib.util
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
spec = importlib.util.spec_from_file_location("a3", ROOT / "src" / "03_analysis.py"); a3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(a3)
WINTER = [12, 1, 2, 3]


def main():
    c = pd.read_csv(D / "cpi_veg.csv").set_index("ym")
    W = pd.read_csv(D / "weather.csv", dtype={"st": str})
    wa = a3.weather_anom(W, a3.ALL7)
    t2 = (wa.temp + wa.temp.shift(1)) / 2
    rows = []
    for it in ["fresh_veg"] + a3.ITEMS:
        y = a3.price_anom(c, it)
        df = pd.concat([y.rename("y"), t2.rename("t")], axis=1).dropna()
        df = df[(df.index % 100).isin(WINTER) & (df.index >= 200001)]
        m = sm.OLS(df.y, sm.add_constant(df.t)).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        rows.append(dict(item=it, slope_pct_per_degC=float(m.params["t"]), se=float(m.bse["t"]), r2=float(m.rsquared), n=int(m.nobs)))
    t = pd.DataFrame(rows); t.round(4).to_csv(R / "winter_temp.csv", index=False)
    f = t.set_index("item")
    out = dict(fresh_slope=float(f.loc["fresh_veg", "slope_pct_per_degC"]), fresh_r2=float(f.loc["fresh_veg", "r2"]),
               cabbage_slope=float(f.loc["cabbage", "slope_pct_per_degC"]), cabbage_r2=float(f.loc["cabbage", "r2"]),
               chinese_cabbage_slope=float(f.loc["chinese_cabbage", "slope_pct_per_degC"]), radish_slope=float(f.loc["radish", "slope_pct_per_degC"]),
               lettuce_slope=float(f.loc["lettuce", "slope_pct_per_degC"]), n=int(f.loc["fresh_veg", "n"]))
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t.round(3)); print(out)


if __name__ == "__main__":
    main()
