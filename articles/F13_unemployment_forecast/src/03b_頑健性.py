"""03b 頑健性チェック
1. 学習期間を「直近15年だけ」にする（ElasticNet・LightGBM）
2. 求人・景気の情報を除き、失業率の過去の動きだけで学習する
3. 公表タイミングを無視して、まだ公表されていない T+1 月の求人・景気の値を使う（＝使えない情報。どれだけ良く見えてしまうか）
4. 季節調整前（原数値）で予測する：前月の値・季節ナイーブ・SARIMA(1,1,0)(0,1,1)12・ElasticNet（月ダミーつき）
（評価期間を変える・コロナ期を除く は 03_分析.py の metrics.csv）
"""
import importlib.util, warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from common import RES

warnings.filterwarnings("ignore")
spec = importlib.util.spec_from_file_location("a", __file__.replace("03b_頑健性.py", "03_分析.py"))
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
df, H = a.df, a.H
u = df["u_sa"]
rows = []


def add(fc, label, models):
    for h in H:
        sub = fc.dropna(subset=[f"actual_chg_{h}"])
        act = sub[f"actual_chg_{h}"].values
        nv = np.mean(np.abs(act))
        for m in models:
            e = sub[f"{m}_{h}"].values - act
            ok = ~np.isnan(e)
            dm, p = a.dm_test(e, sub[f"naive_{h}"].values - act, h)
            rows.append({"チェック": label, "h": h, "model": a.NAMES.get(m, m), "MAE": np.mean(np.abs(e[ok])),
                         "ナイーブのMAE": nv, "MAE_ナイーブ比": np.mean(np.abs(e[ok])) / nv,
                         "方向一致率": np.mean(a.cls(sub[f"{m}_{h}"].values[ok]) == a.cls(act[ok])), "DM_p値": p})


base = pd.read_csv(RES / "forecasts.csv", index_col=0, parse_dates=True)
add(base, "基本", ["ElasticNet", "LightGBM"])

feats = a.make_features(df)
fc = a.rolling(df, feats, u, window=15, models=("ElasticNet", "LightGBM"), label="win15")
add(fc, "学習を直近15年に", ["ElasticNet", "LightGBM"])

own = feats[[c for c in feats.columns if c.startswith("失業率")]]
fc = a.rolling(df, own, u, models=("ElasticNet", "LightGBM"), label="own")
add(fc, "失業率の過去だけ", ["ElasticNet", "LightGBM"])

leak = a.make_features(df, lag_ci=-1, lag_job=-1)
fc = a.rolling(df, leak, u, models=("ElasticNet", "LightGBM"), label="leak")
add(fc, "未公表の値を使う（リーク）", ["ElasticNet", "LightGBM"])

# 原数値
un = df["u_nsa"]
fn = feats.copy()
du = un.diff()
for l in range(6):
    fn[f"失業率の変化_{l+1}か月前"] = du.shift(l)
fn["失業率の水準"] = un
fn["失業率_12か月平均との差"] = un - un.rolling(12).mean()
fn["前年同月差"] = un - un.shift(12)
for k in range(1, 12):
    fn[f"月_{k}"] = (fn.index.month == k).astype(float)
# 目的月の季節性を入れるため、T+h 月の月ダミーは h ごとに変わる → 前年同月の変化（u(T+h-12)-u(T-12)）を特徴量に入れる
recs = []
for h in H:
    fh = fn.copy()
    fh["前年の同じ期間の変化"] = un.shift(12 - h) - un.shift(12)
    fc_h = a.rolling(df, fh, un, models=("ElasticNet",), label="nsa")
    fc_h = fc_h[[f"ElasticNet_{h}", f"actual_chg_{h}", f"naive_{h}", "u_T"]]
    recs.append(fc_h)
nsa = pd.concat(recs, axis=1)
nsa = nsa.loc[:, ~nsa.columns.duplicated()]
for T in nsa.index:
    hist = un[(un.index >= a.TRAIN_START) & (un.index <= T)]
    f = SARIMAX(hist.values, order=(1, 1, 0), seasonal_order=(0, 1, 1, 12)).fit(disp=False).forecast(3)
    for h in H:
        nsa.loc[T, f"SARIMA_{h}"] = f[h - 1] - hist.iloc[-1]
        nsa.loc[T, f"季節ナイーブ_{h}"] = un.shift(12 - h).loc[T] - un.loc[T]
        nsa.loc[T, f"季節ナイーブ＋直近の差_{h}"] = un.shift(12 - h).loc[T] - un.shift(12).loc[T]
add(nsa, "原数値で予測", ["季節ナイーブ", "季節ナイーブ＋直近の差", "SARIMA", "ElasticNet"])

out = pd.DataFrame(rows)
out.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")
print(out.round(3).to_string())
