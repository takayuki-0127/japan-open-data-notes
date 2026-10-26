"""03b 頑健性：学習の窓・気温の予報誤差・特徴量を抜く・特別な期間の特徴・関西エリア"""
import numpy as np
import pandas as pd
import lightgbm as lgb
from common import DATA, RES, SEED
from feat import make_features, LGB_FEATS, LAG_FEATS, TEMP_FEATS
import importlib
main = importlib.import_module("03_分析")
FOLDS, LGB_PARAMS, scores, fit_predict = main.FOLDS, main.LGB_PARAMS, main.scores, main.fit_predict

raw = pd.read_csv(DATA / "hourly_tokyo.csv", index_col="ts", parse_dates=True)
d = make_features(raw)
valid = d["lag168"].notna()


def add_wide(dd):
    dd = dd.copy()
    m, day = dd.index.month, dd.index.day
    dd["obon_wide"] = ((m == 8) & (day >= 10) & (day <= 20)).astype(int)
    dd["nenmatsu_wide"] = (((m == 12) & (day >= 26)) | ((m == 1) & (day <= 5))).astype(int)
    hol = pd.Series(((dd["holiday"] == 1) | (dd["dow"] >= 5)).groupby(dd["date"]).max())
    nxt = hol.shift(-1).fillna(False).astype(int); prv = hol.shift(1).fillna(False).astype(int)
    dd["next_off"] = dd["date"].map(nxt); dd["prev_off"] = dd["date"].map(prv)
    return dd


WIDE = LGB_FEATS + ["obon_wide", "nenmatsu_wide", "next_off", "prev_off"]
variants = {
    "基本（拡張ウィンドウ）": dict(feats=LGB_FEATS),
    "学習を直近3年に限る": dict(feats=LGB_FEATS, window=3),
    "ラグ（過去の需要）を使わない": dict(feats=[f for f in LGB_FEATS if f not in LAG_FEATS]),
    "気温・湿度を使わない": dict(feats=[f for f in LGB_FEATS if f not in TEMP_FEATS]),
    "お盆・年末年始を広め＋休みの前後の特徴を足す": dict(feats=WIDE, wide=True),
}
rows, noise_rows = [], []
rng = np.random.default_rng(SEED)
dw = add_wide(d)
P_by = {}
for vname, cfg in variants.items():
    dd = dw if cfg.get("wide") else d
    preds = []
    for name, s, e in FOLDS:
        tr = valid & (dd.index < s)
        if cfg.get("window"):
            tr &= dd.index >= pd.Timestamp(s) - pd.DateOffset(years=cfg["window"])
        te = valid & (dd.index >= s) & (dd.index <= e + " 23:00")
        m = lgb.LGBMRegressor(**LGB_PARAMS).fit(dd.loc[tr, cfg["feats"]], dd.loc[tr, "demand"])
        p = pd.DataFrame({"actual": dd.loc[te, "demand"], "lgbm": m.predict(dd.loc[te, cfg["feats"]])}, index=dd.index[te])
        p["fold"] = name
        preds.append(p)
        if vname.startswith("基本"):
            # 気温に予報誤差を足す（学習はそのまま、予測に使う気温だけずらす）
            dates = pd.Series(dd.loc[te, "date"].unique())
            for sig in (1.0, 2.0, 3.0):
                for rep in range(3):
                    shift = pd.Series(rng.normal(0, sig, len(dates)), index=dates)
                    dn = make_features(raw, tmean_shift=shift)
                    pn = pd.DataFrame({"actual": dn.loc[te, "demand"], "lgbm": m.predict(dn.loc[te, LGB_FEATS])})
                    noise_rows.append({"期間": name, "σ(℃)": sig, "rep": rep, "MAPE(%)": scores(pn, ["lgbm"])["lgbm"]["MAPE(%)"]})
    P = pd.concat(preds)
    P_by[vname] = P
    sc = scores(P, ["lgbm"])["lgbm"]
    sc2 = scores(P[P.fold != "2020年度"], ["lgbm"])["lgbm"]
    per = {f: scores(P[P.fold == f], ["lgbm"])["lgbm"]["MAPE(%)"] for f, _, _ in FOLDS}
    rows.append({"設定": vname, "MAPE(%)": sc["MAPE(%)"], "ピークのMAPE(%)": sc["ピークのMAPE(%)"],
                 "2020年度を除くMAPE(%)": sc2["MAPE(%)"], **{f"MAPE_{k}": v for k, v in per.items()}})
    print(vname, round(sc["MAPE(%)"], 3), {k: round(v, 2) for k, v in per.items()})

# お盆・年末年始の日だけの誤差（基本と広めの比較）
for vname in ("基本（拡張ウィンドウ）", "お盆・年末年始を広め＋休みの前後の特徴を足す"):
    P = P_by[vname]
    m_, day_ = P.index.month, P.index.day
    sp = ((m_ == 8) & (day_ >= 10) & (day_ <= 20)) | ((m_ == 12) & (day_ >= 26)) | ((m_ == 1) & (day_ <= 5))
    rows.append({"設定": vname + "（お盆・年末年始の日だけ）", "MAPE(%)": scores(P[sp], ["lgbm"])["lgbm"]["MAPE(%)"]})

R = pd.DataFrame(rows)
N = pd.DataFrame(noise_rows)
nz = N.groupby("σ(℃)")["MAPE(%)"].agg(["mean", "min", "max"]).reset_index()
nz.to_csv(RES / "robustness_temp_noise.csv", index=False)
print(nz.round(3))

# 関西エリア：2024年4月〜2025年9月で学習、2025年10月〜2026年9月で評価
k = make_features(pd.read_csv(DATA / "hourly_kansai.csv", index_col="ts", parse_dates=True))
kv = k["lag168"].notna()
tr = kv & (k.index < "2025-10-01"); te = kv & (k.index >= "2025-10-01")
pk, _ = fit_predict(k, tr, te)
cols = ["naive_week", "naive_day", "ridge", "lgbm"]
ks = scores(pk, cols)
pd.DataFrame(ks).T.to_csv(RES / "robustness_kansai.csv")
# 東京も同じ学習期間（2024年4月〜）にそろえて比べる
tt = valid & (d.index >= "2024-04-08") & (d.index < "2025-10-01"); te2 = valid & (d.index >= "2025-10-01")
pt, _ = fit_predict(d, tt, te2)
ts_ = scores(pt, cols)
pd.DataFrame(ts_).T.to_csv(RES / "robustness_tokyo_same_window.csv")
print("関西", {c: round(v["MAPE(%)"], 2) for c, v in ks.items()})
print("東京（同じ短い学習期間）", {c: round(v["MAPE(%)"], 2) for c, v in ts_.items()})
for c in cols:
    R.loc[len(R)] = {"設定": f"関西エリア：{main.MODEL_NAMES[c] if hasattr(main,'MODEL_NAMES') else c}", "MAPE(%)": ks[c]["MAPE(%)"], "ピークのMAPE(%)": ks[c]["ピークのMAPE(%)"]}
R.to_csv(RES / "robustness.csv", index=False)
