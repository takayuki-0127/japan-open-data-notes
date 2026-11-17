"""03 分析：野菜の値段のずれを、天気のずれ（当月〜2か月前）に回帰。品目別、時期を分けた当てはめ、頑健性。
出力：results/main.json, results/panel.csv, results/coefs.csv, results/items.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
ITEMS = ["cabbage", "chinese_cabbage", "lettuce", "radish", "cucumber", "tomato", "spinach", "leek"]
ALL7 = ["47412", "47629", "47624", "47648", "47610", "47636", "47819"]
KANTO = ["47629", "47624", "47648"]


def price_anom(c, item, win=25):
    p = np.log(c[item] / c["core"]) * 100
    tr = p.rolling(win, center=True, min_periods=win).mean()
    x = (p - tr).to_frame("x")
    x["m"] = x.index % 100
    x["x"] = x.x - x.groupby("m").x.transform("mean")
    return x.x


def weather_anom(W, stations):
    W = W[W.st.astype(str).isin(stations)].copy()
    W["m"] = W.ym % 100
    base = W[(W.ym >= 199101) & (W.ym <= 202012)].groupby(["st", "element", "m"]).value.mean().rename("clim")
    W = W.join(base, on=["st", "element", "m"])
    t = W.element == "temp"
    W["anom"] = np.nan
    W.loc[t, "anom"] = W.loc[t, "value"] - W.loc[t, "clim"]
    W.loc[~t, "anom"] = np.log((W.loc[~t, "value"] + 1) / (W.loc[~t, "clim"] + 1)) * 100
    return W.groupby(["ym", "element"]).anom.mean().unstack()


def design(y, wa, lags=(0, 1, 2)):
    X = pd.concat({f"{e}_l{l}": wa[e].shift(l) for l in lags for e in ["temp", "precip", "sunshine"]}, axis=1)
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    return df


def fit(df, a=200001, b=202609):
    s = df.loc[a:b]
    m = sm.OLS(s.y, sm.add_constant(s.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return m, s


def main():
    c = pd.read_csv(D / "cpi_veg.csv").set_index("ym")
    W = pd.read_csv(D / "weather.csv", dtype={"st": str})
    wa = weather_anom(W, ALL7)
    y = price_anom(c, "fresh_veg")
    df = design(y, wa)
    m, s = fit(df)
    pan = s.copy(); pan["fitted"] = m.fittedvalues; pan.round(4).to_csv(R / "panel.csv")
    coef = pd.DataFrame({"coef": m.params, "se": m.bse, "p": m.pvalues}); coef.round(5).to_csv(R / "coefs.csv")
    sum_ = lambda e: float(sum(m.params[f"{e}_l{l}"] for l in (0, 1, 2)))
    m0, _ = fit(design(y, wa, (0,))); m1, _ = fit(design(y, wa, (1,))); m2, _ = fit(design(y, wa, (2,)))
    mtr, _ = fit(df, 200001, 201512)
    te = df.loc[201601:]
    pred = mtr.predict(sm.add_constant(te.drop(columns="y"), has_constant="add"))
    oos = float(np.corrcoef(pred, te.y)[0, 1])
    rows = []
    for it in ITEMS:
        mi, si = fit(design(price_anom(c, it), wa))
        rows.append(dict(item=it, adj_r2=float(mi.rsquared_adj), n=int(mi.nobs), sd_price=float(si.y.std()),
                         precip_sum=float(sum(mi.params[f"precip_l{l}"] for l in (0, 1, 2))), sun_sum=float(sum(mi.params[f"sunshine_l{l}"] for l in (0, 1, 2))),
                         temp_sum=float(sum(mi.params[f"temp_l{l}"] for l in (0, 1, 2)))))
    it = pd.DataFrame(rows); it.round(4).to_csv(R / "items.csv", index=False)
    main = dict(n=int(m.nobs), start=int(s.index[0]), end=int(s.index[-1]), adj_r2=float(m.rsquared_adj), r2=float(m.rsquared),
                sd_price=float(s.y.std()), temp_sum=sum_("temp"), precip_sum=sum_("precip"), sun_sum=sum_("sunshine"),
                adj_r2_lag0=float(m0.rsquared_adj), adj_r2_lag1=float(m1.rsquared_adj), adj_r2_lag2=float(m2.rsquared_adj),
                oos_corr_2016_on=oos, oos_n=int(len(te)),
                best_item=it.loc[it.adj_r2.idxmax(), "item"], best_item_r2=float(it.adj_r2.max()),
                worst_item=it.loc[it.adj_r2.idxmin(), "item"], worst_item_r2=float(it.adj_r2.min()))
    main["H1"] = "支持" if main["adj_r2"] >= 0.2 else "外れ"
    main["H2"] = "支持" if (main["precip_sum"] > 0 and main["sun_sum"] < 0) else "外れ"
    main["H3"] = "支持" if main["adj_r2_lag1"] > main["adj_r2_lag0"] else "外れ"
    main["H4"] = "支持" if oos >= 0.3 else "外れ"
    rob = [dict(check="本線（25か月の移動平均、7地点、2000年〜）", adj_r2=main["adj_r2"], precip_sum=main["precip_sum"], sun_sum=main["sun_sum"], temp_sum=main["temp_sum"])]
    for win in (13, 37):
        mm, _ = fit(design(price_anom(c, "fresh_veg", win), wa))
        rob.append(dict(check=f"{win}か月の移動平均", adj_r2=float(mm.rsquared_adj), precip_sum=float(sum(mm.params[f"precip_l{l}"] for l in (0, 1, 2))),
                        sun_sum=float(sum(mm.params[f"sunshine_l{l}"] for l in (0, 1, 2))), temp_sum=float(sum(mm.params[f"temp_l{l}"] for l in (0, 1, 2)))))
    mk, _ = fit(design(y, weather_anom(W, KANTO)))
    rob.append(dict(check="関東の3地点だけ", adj_r2=float(mk.rsquared_adj), precip_sum=float(sum(mk.params[f"precip_l{l}"] for l in (0, 1, 2))),
                    sun_sum=float(sum(mk.params[f"sunshine_l{l}"] for l in (0, 1, 2))), temp_sum=float(sum(mk.params[f"temp_l{l}"] for l in (0, 1, 2)))))
    m10, _ = fit(df, 201001, 202609)
    rob.append(dict(check="2010年以降", adj_r2=float(m10.rsquared_adj), precip_sum=float(sum(m10.params[f"precip_l{l}"] for l in (0, 1, 2))),
                    sun_sum=float(sum(m10.params[f"sunshine_l{l}"] for l in (0, 1, 2))), temp_sum=float(sum(m10.params[f"temp_l{l}"] for l in (0, 1, 2)))))
    for lab, months in [("夏（6〜9月）", [6, 7, 8, 9]), ("冬（12〜3月）", [12, 1, 2, 3])]:
        sub = df[(df.index % 100).isin(months) & (df.index >= 200001)]
        ms = sm.OLS(sub.y, sm.add_constant(sub.drop(columns="y"))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
        rob.append(dict(check=lab, adj_r2=float(ms.rsquared_adj), precip_sum=float(sum(ms.params[f"precip_l{l}"] for l in (0, 1, 2))),
                        sun_sum=float(sum(ms.params[f"sunshine_l{l}"] for l in (0, 1, 2))), temp_sum=float(sum(ms.params[f"temp_l{l}"] for l in (0, 1, 2)))))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(coef.round(3)); print(it.round(3)); print(pd.read_csv(R / "robustness.csv").to_string())


if __name__ == "__main__":
    main()
