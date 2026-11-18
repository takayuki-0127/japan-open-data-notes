"""問い直し：秋が暖かい期は、年内（7〜12月）にとれる板のりの割合が小さいのか（とれ始めが遅れるのか）。
板のりの枚数の「7〜12月 ÷ 養殖年」を、県の固定効果と年の直線、秋の水温・気温で説明する。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
P = pd.read_csv(R / "panel_major.csv")
P["h2share"] = 100 * P.ita_h2 / P.ita_season
d0 = P[P.ita_h2.notna() & P.ita_season.gt(0) & P.ita_h1n.notna()].reset_index(drop=True)


def fit(d, x):
    d = d.reset_index(drop=True)
    X = pd.concat([d[[x]], (d.season - 2013.5).rename("t"), pd.get_dummies(d.pref, prefix="p", dtype=float)], axis=1)
    r = sm.OLS(d.h2share, X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.season, sort=True)[0]})
    ci = r.conf_int().loc[x]
    return dict(b=float(r.params[x]), lo=float(ci[0]), hi=float(ci[1]), trend=float(r.params["t"]), n=int(r.nobs))


out = {"sst": fit(d0, "sst"), "air": fit(d0, "air"), "mean_share": float(d0.h2share.mean()),
       "national_share": {}}
# 有明海3県と瀬戸内海3県の年内の割合の推移（数量の重みつき）
for g, ps in {"有明海": ["福岡", "佐賀", "熊本"], "瀬戸内海": ["兵庫", "岡山", "香川"]}.items():
    x = d0[d0.pref.isin(ps)].groupby("season")[["ita_h2", "ita_season"]].sum()
    out["national_share"][g] = {int(s): float(100 * v.ita_h2 / v.ita_season) for s, v in x.iterrows()}
d0[["pref", "season", "h2share", "sst", "air"]].to_csv(R / "requestion_h2share.csv", index=False, float_format="%.4f")
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: out[k] for k in ["sst", "air", "mean_share"]}, ensure_ascii=False, indent=1))
for g in out["national_share"]: print(g, {k: round(v, 1) for k, v in out["national_share"][g].items()})
