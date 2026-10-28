"""03 分析：翌日のピーク需要の「上側の分位点」を3つの方法で出し、本当にその割合で収まるかを確かめる（東京エリア）

方法
- 点予測＋固定の上乗せ：LightGBM（二乗誤差）の予測に一定の％を足す（3%・5%・8%）
- 点予測＋残差の分位点（分割コンフォーマル）：学習期間の最後の1年を較正用に取り分け、外れの分位点を足す
- 線形の分位点回帰：statsmodels の QuantReg
- LightGBM の分位点損失：objective="quantile"
評価：年度ごとの拡張ウィンドウ（2020年度〜2026年度上期）。カバー率＝実績が分位点以下だった割合
"""
import json
import numpy as np
import pandas as pd
import lightgbm as lgb
import statsmodels.api as sm
from common import DATA, RES, SEED

RES.mkdir(exist_ok=True)
TAUS = [0.5, 0.8, 0.9, 0.95, 0.975, 0.99]
FOLDS = [("2020年度", "2020-04-01", "2021-03-31"), ("2021年度", "2021-04-01", "2022-03-31"),
         ("2022年度", "2022-04-01", "2023-03-31"), ("2023年度", "2023-04-01", "2024-03-31"),
         ("2024年度", "2024-04-01", "2025-03-31"), ("2025年度", "2025-04-01", "2026-03-31"),
         ("2026年度上期", "2026-04-01", "2026-09-30")]
FEATS = ["temp_mean", "temp_max", "temp_min", "humid", "cdd", "hdd", "cddmax", "temp_change", "dow", "offday",
         "sat", "obon", "nenmatsu", "gw", "doy_sin", "doy_cos", "trend", "lag1", "lag7", "lag1_off"]
P_PT = dict(n_estimators=600, learning_rate=0.03, num_leaves=15, min_child_samples=20, subsample=0.8,
            subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1, n_jobs=2)
P_Q = dict(n_estimators=500, learning_rate=0.03, num_leaves=15, min_child_samples=20, subsample=0.8,
           subsample_freq=1, colsample_bytree=0.8, random_state=SEED, verbose=-1, n_jobs=2)


def recompute(d):
    d = d.copy()
    d["cdd"] = (d.temp_mean - 22).clip(lower=0)
    d["hdd"] = (14 - d.temp_mean).clip(lower=0)
    d["cddmax"] = (d.temp_max - 30).clip(lower=0)
    return d


def lin_X(d):
    X = pd.DataFrame(index=d.index)
    for c in ["temp_mean", "cdd", "hdd", "cddmax", "temp_change", "humid", "offday", "sat", "obon", "nenmatsu",
              "gw", "doy_sin", "doy_cos", "trend", "lag7"]:
        X[c] = d[c]
    X["cdd2"], X["hdd2"] = d.cdd ** 2, d.hdd ** 2
    same = (d.offday == d.lag1_off).astype(float)
    X["lag1_same"], X["lag1_diff"] = d.lag1 * same, d.lag1 * (1 - same)
    X["cdd_off"], X["hdd_off"] = d.cdd * d.offday, d.hdd * d.offday
    return sm.add_constant(X, has_constant="add")


def predict_fold(tr, te, taus=TAUS, calib_days=365, season_conf=False):
    out = pd.DataFrame(index=te.index)
    out["date"], out["actual"], out["season"] = te.date, te.peak, te.season
    # 点予測
    pt = lgb.LGBMRegressor(**P_PT).fit(tr[FEATS], tr.peak)
    out["point"] = pt.predict(te[FEATS])
    for m in (0.03, 0.05, 0.08):
        out[f"fixed{int(m*100)}"] = out["point"] * (1 + m)
    # 分割コンフォーマル（較正＝学習期間の最後の calib_days 日）
    cut = tr.date.max() - pd.Timedelta(days=calib_days)
    sub, cal = tr[tr.date <= cut], tr[tr.date > cut]
    pt_sub = lgb.LGBMRegressor(**P_PT).fit(sub[FEATS], sub.peak)
    res = (cal.peak - pt_sub.predict(cal[FEATS])) / cal.peak.mean()
    n = len(res)
    for t in taus:
        if season_conf:
            qs = {s: np.quantile(r, min(1, np.ceil((len(r) + 1) * t) / len(r)))
                  for s, r in res.groupby(cal.season)}
            out[f"conf_{t}"] = out["point"] + te.season.map(qs).values * cal.peak.mean()
        else:
            q = np.quantile(res, min(1, np.ceil((n + 1) * t) / n))
            out[f"conf_{t}"] = out["point"] + q * cal.peak.mean()
    # 線形の分位点回帰
    Xtr, Xte = lin_X(tr), lin_X(te)
    for t in taus:
        m = sm.QuantReg(tr.peak, Xtr).fit(q=t, max_iter=5000)
        out[f"qr_{t}"] = m.predict(Xte)
    # LightGBM 分位点
    for t in taus:
        m = lgb.LGBMRegressor(objective="quantile", alpha=t, **P_Q).fit(tr[FEATS], tr.peak)
        out[f"lgbq_{t}"] = m.predict(te[FEATS])
    return out


def run(d, folds=FOLDS, train_years=None, noise=None, **kw):
    ps = []
    rng = np.random.default_rng(SEED)
    for name, a, b in folds:
        te = d[(d.date >= a) & (d.date <= b)].copy()
        tr = d[d.date < a]
        if train_years:
            tr = tr[tr.date >= pd.Timestamp(a) - pd.DateOffset(years=train_years)]
        if noise:
            e = rng.normal(0, noise, len(te))
            for c in ("temp_mean", "temp_max", "temp_min"):
                te[c] = te[c] + e
            te = recompute(te)
        p = predict_fold(tr, te, **kw)
        p["fold"] = name
        ps.append(p)
    return pd.concat(ps)


METHODS = {"conf": "点予測＋残差の分位点", "qr": "線形の分位点回帰", "lgbq": "LightGBM の分位点"}


def pinball(y, q, t):
    u = y - q
    return np.mean(np.maximum(t * u, (t - 1) * u))


def evaluate(p, taus=TAUS):
    rows = []
    for k, lab in METHODS.items():
        for t in taus:
            q = p[f"{k}_{t}"]
            med = p[f"{k}_0.5"] if f"{k}_0.5" in p else p["point"]
            rows.append({"方法": lab, "tau": t, "カバー率(%)": 100 * (p.actual <= q).mean(),
                         "pinball(MW)": pinball(p.actual, q, t),
                         "中央値からの上乗せ(%)": 100 * ((q - med) / med).mean(),
                         "上乗せ(MW)": (q - med).mean(),
                         "超えた日の超過(MW,平均)": (p.actual - q)[p.actual > q].mean()})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    d = pd.read_csv(DATA / "tokyo.csv", parse_dates=["date"])
    p = run(d)
    p.to_csv(RES / "pred_tokyo.csv", index=False)
    ev = evaluate(p)
    ev.to_csv(RES / "coverage_tokyo.csv", index=False)
    print(ev.round(2).to_string())
    # 固定の上乗せ
    fx = pd.DataFrame([{"上乗せ": f"{m}%", "カバー率(%)": 100 * (p.actual <= p[f"fixed{m}"]).mean(),
                        "夏": 100 * (p.actual <= p[f"fixed{m}"])[p.season.str.startswith("夏")].mean(),
                        "冬": 100 * (p.actual <= p[f"fixed{m}"])[p.season.str.startswith("冬")].mean()}
                       for m in (3, 5, 8)])
    fx.to_csv(RES / "fixed_margin.csv", index=False)
    print(fx.round(1))
    # 点予測の精度
    mape = 100 * ((p.point - p.actual).abs() / p.actual).mean()
    # 季節別
    rows = []
    for s, g in p.groupby("season"):
        for k, lab in METHODS.items():
            for t in (0.9, 0.95, 0.99):
                rows.append({"季節": s, "方法": lab, "tau": t, "日数": len(g),
                             "カバー率(%)": 100 * (g.actual <= g[f"{k}_{t}"]).mean(),
                             "上乗せ(%)": 100 * ((g[f"{k}_{t}"] - g[f"{k}_0.5"]) / g[f"{k}_0.5"]).mean()})
    se = pd.DataFrame(rows)
    se.to_csv(RES / "coverage_by_season.csv", index=False)
    print(se.round(1).to_string())
    # 年度別
    rows = []
    for f, g in p.groupby("fold", sort=False):
        for k, lab in METHODS.items():
            rows.append({"年度": f, "方法": lab, "日数": len(g),
                         "95%カバー率": 100 * (g.actual <= g[f"{k}_0.95"]).mean(),
                         "99%カバー率": 100 * (g.actual <= g[f"{k}_0.99"]).mean()})
    fo = pd.DataFrame(rows)
    fo.to_csv(RES / "coverage_by_fold.csv", index=False)
    # 分位点の交差（上の分位点が下の分位点より小さくなった日）
    cross = {lab: int(sum((p[f"{k}_{a}"] > p[f"{k}_{b}"] + 1e-6).sum() for a, b in zip(TAUS[:-1], TAUS[1:])))
             for k, lab in METHODS.items()}
    # 猛暑日（最高35℃以上）
    hot = p.merge(d[["date", "temp_max"]], on="date")
    hot = hot[hot.temp_max >= 35]
    hotcov = {lab: {"日数": len(hot), "95%": 100 * (hot.actual <= hot[f"{k}_0.95"]).mean(),
                    "99%": 100 * (hot.actual <= hot[f"{k}_0.99"]).mean()} for k, lab in METHODS.items()}
    summ = {"days": len(p), "point_MAPE": mape, "crossing": cross, "hot_days": hotcov}
    json.dump(summ, open(RES / "summary_main.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(summ, ensure_ascii=False, default=float))
