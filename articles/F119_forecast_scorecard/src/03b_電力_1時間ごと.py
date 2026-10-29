"""F22 のモデル（2026年9月30日までで学習）で、記事のあとの2026年10月1〜28日の1時間ごとの需要を予測する

- 学習・特徴量・パラメータは F22 の src（feat.py・03_分析.py）をそのまま使う。n_jobs だけ1にする
- 比べるもの：F22 のバックテストの10月（2020〜2025年）の誤差
- 頑健性：気温に予報誤差を足す（σ=1・2℃、各5回）／2026年8月31日までで学習したモデル／学習を直近3年に限る
"""
import sys, importlib.util
import numpy as np, pandas as pd
from f119common import ART, ROOT, oct_hourly

F22 = ART / "F22_power_demand_forecast"
sys.path.insert(0, str(F22 / "src"))
from feat import make_features, LGB_FEATS  # noqa: E402
spec = importlib.util.spec_from_file_location("f22a", F22 / "src" / "03_分析.py")
f22 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f22)
f22.LGB_PARAMS["n_jobs"] = 1
RES = ROOT / "results"

raw = pd.concat([pd.read_csv(F22 / "data" / "hourly_tokyo.csv", index_col="ts", parse_dates=True), oct_hourly()])
raw = raw[~raw.index.duplicated()].sort_index()
d = make_features(raw)
valid = d["lag168"].notna()
te = valid & (d.index >= "2026-10-01")
cols = ["naive_week", "naive_day", "ridge", "lgbm"]

rows = []
p, model = f22.fit_predict(d, valid & (d.index < "2026-10-01"), te)
p.to_csv(RES / "power_oct2026_hourly_pred.csv")
for c, v in f22.scores(p, cols).items():
    rows.append({"設定": "基本（9月30日までで学習）", "model": c, **v})

# 過去の10月（F22 のバックテスト）
hist = pd.read_csv(F22 / "results" / "predictions.csv.gz", index_col=0, parse_dates=True)
hist = hist[hist.index.month == 10]
for y, g in hist.groupby(hist.index.year):
    for c, v in f22.scores(g, cols).items():
        rows.append({"設定": f"{y}年10月（F22 のバックテスト）", "model": c, **v})

# 頑健性1：気温の予報誤差
rng = np.random.default_rng(119)
dates = pd.Series(d.loc[te, "date"].unique())
for sig in (1.0, 2.0):
    vals = []
    for rep in range(5):
        shift = pd.Series(rng.normal(0, sig, len(dates)), index=dates)
        dn = make_features(raw, tmean_shift=shift)
        pn = pd.DataFrame({"actual": dn.loc[te, "demand"], "lgbm": model.predict(dn.loc[te, LGB_FEATS])})
        vals.append(f22.scores(pn, ["lgbm"])["lgbm"])
    rows.append({"設定": f"気温に予報誤差 σ={sig:.0f}℃（5回の平均）", "model": "lgbm",
                 **{k: np.mean([v[k] for v in vals]) for k in vals[0]}})
# 頑健性2：8月31日までで学習
p2, _ = f22.fit_predict(d, valid & (d.index < "2026-09-01"), te, models=("ridge", "lgbm"))
for c, v in f22.scores(p2, ["ridge", "lgbm"]).items():
    rows.append({"設定": "8月31日までで学習（1か月古いモデル）", "model": c, **v})
# 頑健性3：学習を直近3年に限る
tr3 = valid & (d.index < "2026-10-01") & (d.index >= "2023-10-01")
p3, _ = f22.fit_predict(d, tr3, te, models=("ridge", "lgbm"))
for c, v in f22.scores(p3, ["ridge", "lgbm"]).items():
    rows.append({"設定": "学習を直近3年に限る", "model": c, **v})

M = pd.DataFrame(rows)
M.to_csv(RES / "power_oct2026_hourly_metrics.csv", index=False)
print(M.pivot_table(index="設定", columns="model", values="MAPE(%)").round(2).to_string())

# 日ごとの誤差
a = p["actual"]; day = p.index.normalize()
dd = pd.DataFrame({"MAPE_lgbm": 100 * ((p["lgbm"] - a).abs() / a).groupby(day).mean(),
                   "bias_lgbm(%)": 100 * ((p["lgbm"] - a) / a).groupby(day).mean(),
                   "MAPE_week": 100 * ((p["naive_week"] - a).abs() / a).groupby(day).mean()})
dd.index.name = "date"
dd.to_csv(RES / "power_oct2026_daily_errors.csv")
print(dd.round(2).sort_values("MAPE_lgbm", ascending=False).head(6))
