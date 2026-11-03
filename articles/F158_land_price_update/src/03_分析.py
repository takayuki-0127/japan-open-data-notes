"""(1) 更新のしかたごとの、翌年の当たり方（20km四方のブロックで分けた5分割）
   (2) 年ごとのモデルの特徴量の重要度（SHAP）の移り変わり"""
import sys, json, time
import numpy as np, pandas as pd
import lightgbm as lgb, shap
from common import load_points, load_panel, FEAT, GROUPS, PARAMS, YEARS, RES, SEED
from stratlib import run

t0 = time.time()
pts, pan = load_points(), load_panel()
if "imp" not in sys.argv:
    tab, out = run(pts, pan, "block20", "lgbm", window=True, log=lambda s: print(s, round(time.time() - t0), flush=True))
    tab.to_csv(RES / "strategy_by_year.csv", index=False)
    out.to_csv(RES / "strategy_predictions.csv.gz", index=False, compression="gzip")
    print(tab[tab.year == "2018-2026"].to_string(), flush=True)

# (2) 重要度：各年の全地点で学習 → 全年にそろっている地点から 3,000 地点の SHAP
P = pan.merge(pts, on="code")
for c in ("use_district", "planning_area", "fire_area", "road_type", "land_use_class"):
    P[c] = P[c].astype(pd.CategoricalDtype(pts[c].cat.categories))
P["y"] = np.log(P["price"])
cnt = pan.groupby("code").size()
common_codes = cnt[cnt == len(YEARS)].index
rng = np.random.default_rng(SEED)
sample = rng.choice(np.array(common_codes), 3000, replace=False)
Xs = pts.set_index("code").loc[sample, FEAT]
rows, dep = [], []
for s in YEARS:
    Ps = P[P["year"] == s].reset_index(drop=True)
    for b in range(3):  # b=0 は全地点、1・2 は地点のブートストラップ（ぶれの目安）
        idx = np.arange(len(Ps)) if b == 0 else np.random.default_rng(SEED + 100 * b + s).integers(0, len(Ps), len(Ps))
        m = lgb.LGBMRegressor(**PARAMS).fit(Ps[FEAT].iloc[idx], Ps["y"].iloc[idx])
        sv = shap.TreeExplainer(m).shap_values(Xs)
        imp = np.abs(sv).mean(0)
        for f, v in zip(FEAT, imp):
            rows.append(dict(year=s, boot=b, feature=f, mean_abs_shap=v))
        if b == 0:
            for f in ("dist_metro", "dist_station", "muni_pop_change", "log_pass_10km", "log_muni_density"):
                j = FEAT.index(f)
                dep.append(pd.DataFrame({"year": s, "feature": f, "x": Xs[f].values, "shap": sv[:, j]}))
    print("imp", s, round(time.time() - t0), flush=True)
imp = pd.DataFrame(rows)
imp.to_csv(RES / "importance_by_year.csv", index=False)
pd.concat(dep).to_csv(RES / "shap_dependence.csv.gz", index=False, compression="gzip")
inv = {f: g for g, fs in GROUPS.items() for f in fs}
imp["group"] = imp["feature"].map(inv)
gs = imp.groupby(["year", "boot", "group"])["mean_abs_shap"].sum().reset_index()
gs["share"] = gs["mean_abs_shap"] / gs.groupby(["year", "boot"])["mean_abs_shap"].transform("sum")
gs.to_csv(RES / "importance_group_share.csv", index=False)
print(gs[gs.boot == 0].pivot(index="year", columns="group", values="share").round(3).to_string())
print("done", round(time.time() - t0))
