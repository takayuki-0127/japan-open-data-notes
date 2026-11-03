"""2017年のモデルのまま使うとき、「都道府県×用途ごとの変化」で補正すればどこまで戻るか。
あわせて参考として、同じ地点の前年の価格をそのまま使った場合の外れ"""
import numpy as np, pandas as pd
from common import load_points, load_panel, folds, score, RES, YEARS

pts, pan = load_points(), load_panel()
fo = folds(pts, "block20")
pts["fold"] = pts["code"].map(fo).values
wide = np.log(pan.pivot(index="code", columns="year", values="price"))
info = pts.set_index("code")[["pref", "land_use_class", "fold"]]
out = pd.read_csv(RES / "strategy_predictions.csv.gz", dtype={"code": str})
fz = out[out["strategy"] == "2017年のまま"].copy()
fz = fz.join(info[["pref", "land_use_class"]].astype(str), on="code")
rows = []
for k in range(5):
    tr = info.index[info["fold"] != k]
    W = wide.reindex(tr).join(info[["pref", "land_use_class"]].astype(str))
    for T in YEARS[1:]:
        d = (W[T - 1] - W[YEARS[0]]).rename("chg")
        g = pd.concat([d, W[["pref", "land_use_class"]]], axis=1).dropna()
        m_pc = g.groupby(["pref", "land_use_class"])["chg"].median()
        m_p = g.groupby("pref")["chg"].median()
        sel = (fz["fold"] == k) & (fz["year"] == T)
        key = list(zip(fz.loc[sel, "pref"], fz.loc[sel, "land_use_class"]))
        adj = np.array([m_pc.get(kk, m_p.get(kk[0], g["chg"].median())) for kk in key])
        fz.loc[sel, "pred_pc"] = fz.loc[sel, "pred"] + adj
        fz.loc[sel, "pred_p"] = fz.loc[sel, "pred"] + fz.loc[sel, "pref"].map(m_p).fillna(g["chg"].median()).values
for T, g in fz.groupby("year"):
    rows.append(dict(year=T, strategy="2017年のまま＋都道府県ごとの変化で補正", **score(g["y"], g["pred_p"])))
    rows.append(dict(year=T, strategy="2017年のまま＋都道府県×用途ごとの変化で補正", **score(g["y"], g["pred_pc"])))
rows.append(dict(year="2018-2026", strategy="2017年のまま＋都道府県ごとの変化で補正", **score(fz["y"], fz["pred_p"])))
rows.append(dict(year="2018-2026", strategy="2017年のまま＋都道府県×用途ごとの変化で補正", **score(fz["y"], fz["pred_pc"])))
# 参考：同じ地点の前年の価格（見ていない場所の予測ではないので、比べる相手が違う）
ref = []
for T in YEARS[1:]:
    w = wide[[T - 1, T]].dropna()
    ref.append(dict(year=T, strategy="参考：同じ地点の前年の価格", **score(w[T], w[T - 1])))
w = pd.concat([wide[[T - 1, T]].dropna().set_axis(["a", "b"], axis=1) for T in YEARS[1:]])
ref.append(dict(year="2018-2026", strategy="参考：同じ地点の前年の価格", **score(w["b"], w["a"])))
# 地価のばらつき（log の標準偏差）の推移
disp = [dict(year=T, sd_log=wide[T].dropna().std(), p90_p10=np.exp(wide[T].dropna().quantile(.9) - wide[T].dropna().quantile(.1))) for T in YEARS]
tab = pd.DataFrame(rows + ref)
tab.to_csv(RES / "strategy_extra.csv", index=False)
pd.DataFrame(disp).to_csv(RES / "price_dispersion.csv", index=False)
print(tab[tab.year == "2018-2026"].round(4).to_string())
print(tab[tab.year.isin([2018, 2022, 2026])].round(4).to_string())
print(pd.DataFrame(disp).round(3).to_string())
