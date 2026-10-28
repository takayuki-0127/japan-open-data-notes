"""03 分析：地価（F03）と電力需要（F22）の LightGBM を4つの手法で読み、答えがそろうかを比べる"""
import json, sys
import numpy as np, pandas as pd
import lightgbm as lgb
from scipy.stats import spearmanr, kendalltau
from common import (load_land, load_power, L_NUM, L_CAT, L_PARAMS, P_PARAMS, P_SPLIT, RES, SEED, METHODS)
from interp import all_importances, permutation_importance, shap_importance, curve_importance, pdp_curve, ale_curve

summary = {}


def rmse(a, b):
    return float(np.sqrt(np.mean((a - b) ** 2)))


def data_land():
    d = load_land()
    X, y = d[L_NUM + L_CAT], d["y"].values
    rng = np.random.default_rng(SEED)
    te = rng.random(len(d)) < 0.2
    return X[~te], y[~te], X[te], y[te]


def data_power():
    d, F = load_power()
    tr, te = d.index < P_SPLIT, d.index >= P_SPLIT
    Xte = d.loc[te, F].sample(20000, random_state=SEED)
    return d.loc[tr, F], d.loc[tr, "demand"].values, Xte, d.loc[Xte.index, "demand"].values


def compare(imp):
    m = {}
    for i, a in enumerate(METHODS):
        for b in METHODS[i + 1:]:
            m[f"{a}×{b}"] = dict(spearman=round(spearmanr(imp[a], imp[b])[0], 3),
                                 kendall=round(kendalltau(imp[a], imp[b])[0], 3),
                                 top5_overlap=len(set(imp[a].nlargest(5).index) & set(imp[b].nlargest(5).index)))
    return m


def share(imp):
    return imp / imp.sum()


DROP = {"地価": {"keep": "log_pass_3km", "drop": ["log_pass_1km", "log_pass_10km", "log_pass_nearest", "log_muni_density"]},
        "電力需要": {"keep": "temp_mean", "drop": ["temp_max", "temp_min", "cdd", "hdd", "cdd_max"]}}
GROUPS = {"地価": {"乗降客数（4つ）": ["log_pass_nearest", "log_pass_1km", "log_pass_3km", "log_pass_10km"],
                 "駅までの距離（2つ）": ["dist_station", "dist_nearest_st"],
                 "市区町村の人口（3つ）": ["log_muni_density", "log_muni_pop", "muni_pop_change"],
                 "容積率・建ぺい率": ["far", "coverage"], "緯度・経度": ["lat", "lon"]},
          "電力需要": {"気温（6つ）": ["temp_mean", "temp_max", "temp_min", "cdd", "hdd", "cdd_max"],
                   "過去の需要（3つ）": ["lag24", "lag168", "prevday_mean"],
                   "季節（3つ）": ["doy_sin", "doy_cos", "month"]}}

for name, loader, params in [("地価", data_land, L_PARAMS), ("電力需要", data_power, P_PARAMS)]:
    Xtr, ytr, Xte, yte = loader()
    print(name, "学習", len(Xtr), "評価", len(Xte), flush=True)
    m = lgb.LGBMRegressor(**params).fit(Xtr, ytr)
    p = m.predict(Xte)
    acc = dict(rmse=rmse(p, yte), n_train=len(Xtr), n_test=len(Xte))
    if name == "地価":
        acc["median_abs_pct"] = float(np.median(np.abs(np.exp(p - yte) - 1)) * 100)
    else:
        acc["mape"] = float(np.mean(np.abs(p / yte - 1)) * 100)
    imp, extra = all_importances(m, Xte, yte, seed=SEED)
    imp["gain（参考）"] = pd.Series(m.booster_.feature_importance("gain"), index=Xte.columns)
    imp.to_csv(RES / f"importance_{name}.csv")
    S = {"accuracy": acc, "compare": compare(imp[METHODS]),
         "top5": {k: list(imp[k].nlargest(5).index) for k in METHODS}}
    # 曲線を保存（図用）
    keep = ["temp_mean", "temp_max", "lag24", "hour", "cdd"] if name == "電力需要" else ["log_pass_3km", "dist_station", "far", "coverage", "lat"]
    rows = []
    for f in keep:
        for kind in ("pdp", "ale"):
            c = extra[kind][f]
            for x, v in zip(c.iloc[:, 0], c.iloc[:, 1]):
                rows.append(dict(feature=f, kind=kind, x=x, value=v))
    pd.DataFrame(rows).to_csv(RES / f"curves_{name}.csv", index=False)
    # 相関する変数を外すと、重要度はどこへ移るか
    dk = DROP[name]
    m2 = lgb.LGBMRegressor(**params).fit(Xtr.drop(columns=dk["drop"]), ytr)
    imp2, _ = all_importances(m2, Xte.drop(columns=dk["drop"]), yte, seed=SEED)
    s1, s2 = share(imp[METHODS]), share(imp2[METHODS])
    grp = [dk["keep"]] + dk["drop"]
    S["drop"] = {"keep": dk["keep"], "dropped": dk["drop"],
                 "rmse_after": rmse(m2.predict(Xte.drop(columns=dk["drop"])), yte),
                 "keep_share_before": {k: round(float(s1.loc[dk["keep"], k]), 4) for k in METHODS},
                 "group_share_before": {k: round(float(s1.loc[grp, k].sum()), 4) for k in METHODS},
                 "keep_share_after": {k: round(float(s2.loc[dk["keep"], k]), 4) for k in METHODS},
                 "keep_ratio_after_before": {k: round(float(imp2.loc[dk["keep"], k] / imp.loc[dk["keep"], k]), 2) for k in METHODS}}
    pd.DataFrame({"before": s1.loc[grp].stack(), "after": s2.reindex(grp).stack()}).to_csv(RES / f"drop_{name}.csv")
    # まとまりごとに並べ替える（相関する変数を一緒に崩す）
    gp = permutation_importance(m, Xte, yte, 5, SEED, groups=GROUPS[name])
    S["group_perm"] = {g: dict(group=round(float(gp[g]), 4), sum_individual=round(float(imp.loc[cs, "並べ替え重要度"].sum()), 4),
                               max_individual=round(float(imp.loc[cs, "並べ替え重要度"].max()), 4))
                       for g, cs in GROUPS[name].items()}
    # 並べ替えで「ありえない点」がどれだけできるか
    if name == "電力需要":
        rng = np.random.default_rng(SEED)
        tm = Xte["temp_mean"].values[rng.permutation(len(Xte))]
        out = (tm > Xte["temp_max"].values + 0.5) | (tm < Xte["temp_min"].values - 0.5)
        g = np.quantile(Xte["temp_mean"], np.linspace(0.05, 0.95, 20))
        pdp_out = np.mean([((v > Xte["temp_max"]) | (v < Xte["temp_min"])).mean() for v in g])
        S["unrealistic"] = dict(perm_out_of_range=round(float(out.mean()), 4), pdp_grid_out_of_range=round(float(pdp_out), 4))
    else:
        rng = np.random.default_rng(SEED)
        cov = Xte["coverage"].values[rng.permutation(len(Xte))]
        far = Xte["far"].values
        S["unrealistic"] = dict(perm_far_below_coverage=round(float((far < cov).mean()), 4),
                                original_far_below_coverage=round(float((far < Xte["coverage"].values).mean()), 4))
    # 頑健性：モデル・乱数・計算の設定を変えて、手法ごとの順位がどれだけ動くか
    rob = []
    variants = {
        "葉の数15・学習率0.1・別の乱数": dict(params, num_leaves=15, learning_rate=0.1, random_state=SEED + 1),
        "ランダムフォレスト型（LightGBM rf）": dict(params, boosting_type="rf", bagging_fraction=0.7, bagging_freq=1,
                                             feature_fraction=0.7, n_estimators=300, learning_rate=1.0),
    }
    for vname, vp in variants.items():
        mv = lgb.LGBMRegressor(**vp).fit(Xtr, ytr)
        iv, _ = all_importances(mv, Xte, yte, seed=SEED + 7)
        for k in METHODS:
            rob.append(dict(setting=vname, method=k, spearman_vs_base=round(spearmanr(imp[k], iv[k])[0], 3),
                            top5_overlap=len(set(imp[k].nlargest(5).index) & set(iv[k].nlargest(5).index))))
        cm = compare(iv[METHODS])
        rob.append(dict(setting=vname, method="手法どうし（平均）",
                        spearman_vs_base=round(np.mean([v["spearman"] for v in cm.values()]), 3), top5_overlap=np.nan))
    # 計算の設定だけ変える（同じモデル）
    sh2 = shap_importance(m, Xte, 1000, SEED + 3)[0]
    pi2 = permutation_importance(m, Xte, yte, 20, SEED + 3)
    Xs = Xtr.sample(min(len(Xtr), 20000), random_state=SEED)
    pi3 = permutation_importance(m, Xs, pd.Series(ytr, index=Xtr.index).loc[Xs.index].values, 5, SEED)
    Xc = Xte.sample(1000, random_state=SEED + 5)
    yc = pd.Series(yte, index=Xte.index).loc[Xc.index].values
    pdp2 = curve_importance(m, Xc, yc, "pdp", 10)[0]
    ale2 = curve_importance(m, Xc, yc, "ale", 10)[0]
    for vname, k, v in [("SHAP の点数1000", "SHAP", sh2), ("並べ替え20回", "並べ替え重要度", pi2),
                        ("並べ替えを学習データで", "並べ替え重要度", pi3), ("PDP の点数1000・区切り10", "部分依存（PDP）", pdp2),
                        ("ALE の点数1000・区切り10", "ALE", ale2)]:
        rob.append(dict(setting=vname, method=k, spearman_vs_base=round(spearmanr(imp[k], v)[0], 3),
                        top5_overlap=len(set(imp[k].nlargest(5).index) & set(v.nlargest(5).index))))
    pd.DataFrame(rob).to_csv(RES / f"robust_{name}.csv", index=False)
    S["robust"] = rob
    summary[name] = S
    print(json.dumps(S, ensure_ascii=False, default=float)[:3000], flush=True)

json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print("done")
