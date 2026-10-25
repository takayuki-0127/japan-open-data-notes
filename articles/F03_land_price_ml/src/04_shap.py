"""全地点で学習した LightGBM を SHAP で読む。部分依存（駅距離・人口密度）と、外れる地点も"""
import numpy as np, pandas as pd
import lightgbm as lgb, shap
from common import load, NUM, CAT, RES, LABEL, SEED
import importlib
PARAMS = importlib.import_module("03_lgbm_cv").PARAMS

d = load(); FEAT = NUM + CAT
m = lgb.LGBMRegressor(**PARAMS).fit(d[FEAT], d["y"])
m.booster_.save_model(str(RES / "lgbm_full.txt"))
ex = shap.TreeExplainer(m)
sv = ex.shap_values(d[FEAT])
np.save(RES / "shap_values.npy", sv.astype("float32"))
base = float(ex.expected_value)
imp = pd.DataFrame({"feature": FEAT, "label": [LABEL[f] for f in FEAT], "mean_abs_shap": np.abs(sv).mean(0)}).sort_values("mean_abs_shap", ascending=False)
# 方向：数値の特徴量について、値と SHAP の順位相関
from scipy.stats import spearmanr
imp["direction_rho"] = [spearmanr(d[f], sv[:, FEAT.index(f)], nan_policy="omit")[0] if f in NUM else np.nan for f in imp["feature"]]
imp.to_csv(RES / "shap_importance.csv", index=False); print(imp.round(3).to_string())
GROUP = {"立地（駅・人口・都市圏）": ["dist_station", "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km", "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"],
         "規制（用途地域・容積率など）": ["use_district", "planning_area", "fire_area", "far", "coverage", "land_use_class"],
         "土地と建物の属性": ["log_acreage", "road_width", "gas", "water", "sewage", "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square", "road_type"]}
g = pd.DataFrame([(k, imp.set_index("feature").loc[v, "mean_abs_shap"].sum()) for k, v in GROUP.items()], columns=["group", "mean_abs_shap"])
g["share"] = g["mean_abs_shap"] / g["mean_abs_shap"].sum(); g.to_csv(RES / "shap_groups.csv", index=False); print(g.round(3))

# 部分依存（ほかの特徴量はそのまま、対象の値だけ動かして予測の平均をとる）
rng = np.random.default_rng(SEED); samp = d.iloc[rng.choice(len(d), 4000, replace=False)][FEAT].copy()
pd_rows = []
grids = {"dist_station": [50, 100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000, 2500, 3000, 4000, 5000, 7000, 10000],
         "log_pass_3km": list(np.log1p([0, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 1e7])),
         "log_muni_density": list(np.log([20, 50, 100, 200, 500, 1000, 2000, 3000, 5000, 8000, 12000, 16000, 20000]))}
for res_cls in ("全体", "住宅地", "商業地"):
    s = samp if res_cls == "全体" else samp[samp["land_use_class"] == res_cls]
    for f, grid in grids.items():
        for v in grid:
            x = s.copy(); x[f] = v
            pd_rows.append(dict(cls=res_cls, feature=f, value=v, mean_pred=m.predict(x).mean()))
pdp = pd.DataFrame(pd_rows)
pdp["rel"] = pdp.groupby(["cls", "feature"])["mean_pred"].transform(lambda s: np.exp(s - s.iloc[0]))
pdp.to_csv(RES / "partial_dependence.csv", index=False); print(pdp[pdp.feature == "dist_station"].round(3).to_string())

# 外れる地点（20km四方ブロックCV の予測）
o = pd.read_csv(RES / "oof_lgbm.csv", dtype={"code": str})
d["pred_block"] = o["lgb_block20"].values; d["resid"] = d["y"] - d["pred_block"]
d["ratio"] = np.exp(d["resid"])
d[["code", "city", "land_use_class", "use_district", "price", "pred_block", "resid", "ratio", "lat", "lon", "pref"]].to_csv(RES / "residuals_block20.csv", index=False)
pref_err = d.groupby("pref").agg(n=("resid", "size"), mean_resid=("resid", "mean"), mae=("resid", lambda s: s.abs().mean())).reset_index()
pref_err.to_csv(RES / "residual_by_pref.csv", index=False)
print(pref_err.sort_values("mae", ascending=False).head(8).round(3))
cls_err = d.groupby("land_use_class").agg(n=("resid", "size"), mae=("resid", lambda s: s.abs().mean()), within20=("ratio", lambda s: ((s - 1).abs() <= 0.2).mean())).reset_index()
cls_err.to_csv(RES / "residual_by_class.csv", index=False); print(cls_err.round(3))
print("実際が予測の2倍超:", (d.ratio > 2).sum(), " 半分未満:", (d.ratio < 0.5).sum())
print(d.sort_values("resid").head(6)[["city", "land_use_class", "price", "ratio"]])
print(d.sort_values("resid").tail(6)[["city", "land_use_class", "price", "ratio"]])

# 個別地点の SHAP（2地点）：最も高い地点と、中央値付近の住宅地
i1 = int(d["price"].idxmax())
res = d[d["land_use_class"] == "住宅地"]; i2 = int((res["price"] - res["price"].median()).abs().idxmin())
wf = []
for tag, i in (("最高価格の地点", i1), ("中央値付近の住宅地", i2)):
    for f in FEAT:
        wf.append(dict(point=tag, code=d.loc[i, "code"], city=d.loc[i, "city"], price=d.loc[i, "price"], base=base,
                       pred=float(m.predict(d.loc[[i], FEAT])[0]), feature=f, label=LABEL[f],
                       value=str(d.loc[i, f]), shap=float(sv[i, FEAT.index(f)])))
pd.DataFrame(wf).to_csv(RES / "shap_two_points.csv", index=False)
print("base", base, np.exp(base))
