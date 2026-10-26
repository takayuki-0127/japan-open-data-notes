"""03 分析：ベースライン → 線形回帰 → LightGBM を、年度ごとの拡張ウィンドウで比べる（東京エリア）"""
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from common import DATA, RES, SEED, MODEL_NAMES
from feat import make_features, ridge_matrix, LGB_FEATS

RES.mkdir(exist_ok=True)
LGB_PARAMS = dict(n_estimators=900, learning_rate=0.04, num_leaves=63, min_child_samples=40,
                  subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                  random_state=SEED, verbose=-1, n_jobs=4)
FOLDS = [("2020年度", "2020-04-01", "2021-03-31"), ("2021年度", "2021-04-01", "2022-03-31"),
         ("2022年度", "2022-04-01", "2023-03-31"), ("2023年度", "2023-04-01", "2024-03-31"),
         ("2024年度", "2024-04-01", "2025-03-31"), ("2025年度", "2025-04-01", "2026-03-31"),
         ("2026年度上期", "2026-04-01", "2026-09-30")]


def load(name="hourly_tokyo.csv"):
    d = pd.read_csv(DATA / name, index_col="ts", parse_dates=True)
    return make_features(d)


def fit_predict(d, tr, te, feats=LGB_FEATS, models=("naive_week", "naive_day", "ridge", "lgbm")):
    out = pd.DataFrame(index=d.index[te])
    out["actual"] = d.loc[te, "demand"]
    if "naive_week" in models:
        out["naive_week"] = d.loc[te, "lag168"]
    if "naive_day" in models:
        out["naive_day"] = d.loc[te, "lag24"]
    if "ridge" in models:
        Xr = ridge_matrix(d)
        m = make_pipeline(StandardScaler(), Ridge(alpha=3.0)).fit(Xr[tr], d.loc[tr, "demand"])
        out["ridge"] = m.predict(Xr[te])
    model = None
    if "lgbm" in models:
        model = lgb.LGBMRegressor(**LGB_PARAMS).fit(d.loc[tr, feats], d.loc[tr, "demand"])
        out["lgbm"] = model.predict(d.loc[te, feats])
    return out, model


def scores(p, cols):
    r = {}
    a = p["actual"]
    day = p.index.normalize()
    peak_a = a.groupby(day).max()
    for c in cols:
        ape = (p[c] - a).abs() / a
        peak_p = p[c].groupby(day).max()
        r[c] = {"MAPE(%)": 100 * ape.mean(), "MAE(MW)": (p[c] - a).abs().mean(),
                "ピークのMAPE(%)": 100 * ((peak_p - peak_a).abs() / peak_a).mean(),
                "誤差5%超の時間(%)": 100 * (ape > 0.05).mean()}
    return r


if __name__ == "__main__":
    d = load()
    valid = d["lag168"].notna()
    preds, rows = [], []
    cols = ["naive_week", "naive_day", "ridge", "lgbm"]
    for name, s, e in FOLDS:
        tr = valid & (d.index < s)
        te = valid & (d.index >= s) & (d.index <= e + " 23:00")
        p, model = fit_predict(d, tr, te)
        p["fold"] = name
        preds.append(p)
        for c, v in scores(p, cols).items():
            rows.append({"期間": name, "model": c, **v})
        print(name, {c: round(v["MAPE(%)"], 2) for c, v in scores(p, cols).items()})
    P = pd.concat(preds)
    P.to_csv(RES / "predictions.csv.gz", compression="gzip")
    allsc = scores(P, cols)
    for c, v in allsc.items():
        rows.append({"期間": "全期間（2020年4月〜2026年9月）", "model": c, **v})
    noc = P[P.fold != "2020年度"]
    for c, v in scores(noc, cols).items():
        rows.append({"期間": "2020年度を除く", "model": c, **v})
    M = pd.DataFrame(rows)
    M.to_csv(RES / "metrics.csv", index=False)
    print(M[M.期間.str.startswith("全期間")].round(2))

    # 日ごとの誤差と、外れた日
    a = P["actual"]
    day = P.index.normalize()
    dd = pd.DataFrame({"MAPE_lgbm": 100 * ((P["lgbm"] - a).abs() / a).groupby(day).mean(),
                       "誤差の向き(MW)": (P["lgbm"] - a).groupby(day).mean(),
                       "MAPE_week": 100 * ((P["naive_week"] - a).abs() / a).groupby(day).mean(),
                       "実績の日平均(MW)": a.groupby(day).mean()})
    info = d[d.hour == 12].set_index("date")[["temp_max", "temp_min", "precip_mm", "holiday", "holiday_name", "dow", "nenmatsu", "obon", "gw", "temp_change"]]
    dd = dd.join(info)
    dd.index.name = "date"
    dd.to_csv(RES / "daily_errors.csv")

    hol = set(d.loc[d.holiday == 1, "date"].dt.normalize())
    def near_holiday(x):
        return any((x + pd.Timedelta(days=k)) in hol for k in (-1, 0, 1))
    def label(r):
        x = r.name
        md = (x.month, x.day)
        if (x.month == 12 and x.day >= 26) or (x.month == 1 and x.day <= 5): return "年末年始（12/26〜1/5）"
        if x.month == 8 and 10 <= x.day <= 20: return "お盆の時期（8/10〜8/20）"
        if (x.month == 4 and x.day >= 27) or (x.month == 5 and x.day <= 7): return "大型連休（4/27〜5/7）"
        if near_holiday(x): return "祝日とその前後1日"
        if r.temp_max >= 33: return "猛暑（最高33℃以上）"
        if abs(r.temp_change) >= 5: return "前日から日平均気温が5℃以上変化"
        if r.precip_mm >= 30: return "大雨（日降水量30mm以上）"
        return "その他の日"
    dd["分類"] = dd.apply(label, axis=1)
    worst = dd.sort_values("MAPE_lgbm", ascending=False).head(30)
    worst.to_csv(RES / "worst_days.csv")
    cat = dd.groupby("分類").agg(日数=("MAPE_lgbm", "size"), 平均MAPE=("MAPE_lgbm", "mean"))
    top = dd.sort_values("MAPE_lgbm", ascending=False).head(100)["分類"].value_counts().rename("外れた100日に入った日数")
    cat = cat.join(top).fillna(0)
    cat["全体での割合(%)"] = 100 * cat["日数"] / cat["日数"].sum()
    cat["外れた100日での割合(%)"] = cat["外れた100日に入った日数"]
    cat.sort_values("平均MAPE", ascending=False).to_csv(RES / "error_by_category.csv")
    print(worst.head(15)[["MAPE_lgbm", "誤差の向き(MW)", "temp_max", "temp_change", "分類"]].round(1))
    print(cat.round(2))

    # SHAP（最後の期間のモデル）
    tr = valid & (d.index < "2026-04-01")
    te = valid & (d.index >= "2026-04-01")
    _, model = fit_predict(d, tr, te, models=("lgbm",))
    X = d.loc[te, LGB_FEATS].sample(4000, random_state=SEED)
    sv = shap.TreeExplainer(model).shap_values(X)
    imp = pd.DataFrame({"mean_abs_shap": np.abs(sv).mean(0)}, index=LGB_FEATS).sort_values("mean_abs_shap", ascending=False)
    imp.to_csv(RES / "shap_importance.csv")
    np.save(RES / "_shap_values.npy", sv); X.to_csv(RES / "_shap_X.csv")
    print(imp.round(0).head(12))
