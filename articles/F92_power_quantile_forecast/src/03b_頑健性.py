"""03b 頑健性：設定を変えても「どの方法がどれだけ外れるか」は同じかを確かめる"""
import numpy as np
import pandas as pd
from common import DATA, RES
import importlib
A = importlib.import_module("03_分析")

T = [0.9, 0.95, 0.99]
d = pd.read_csv(DATA / "tokyo.csv", parse_dates=["date"])
dk = pd.read_csv(DATA / "kansai.csv", parse_dates=["date"])


def summ(p, label):
    rows = []
    for k, lab in A.METHODS.items():
        r = {"設定": label, "方法": lab, "日数": len(p)}
        for t in T:
            r[f"{int(t*100)}%カバー率"] = 100 * (p.actual <= p[f"{k}_{t}"]).mean()
            r[f"{int(t*100)}%上乗せ(%)"] = 100 * ((p[f"{k}_{t}"] - p[f"{k}_0.5"]) / p[f"{k}_0.5"]).mean()
        rows.append(r)
    return rows


rows = []
base = pd.read_csv(RES / "pred_tokyo.csv", parse_dates=["date"])
rows += summ(base, "基本（東京・全期間で学習）")
# 1 分位点の並べ替え（交差の修正）
s = base.copy()
for k in ("qr", "lgbq"):
    cols = [f"{k}_{t}" for t in A.TAUS]
    s[cols] = np.sort(s[cols].values, axis=1)
rows += summ(s, "交差を並べ替えで直す")
# 2 季節ごとの残差で較正
p = A.run(d, taus=[0.5] + T, season_conf=True)
rows += [r for r in summ(p, "較正を季節別にする") if r["方法"].startswith("点予測")]
# 3 学習を直近3年に
p = A.run(d, taus=[0.5] + T, train_years=3)
rows += summ(p, "学習を直近3年に限る")
# 4 気温に予報の誤差（σ=2℃）を足す
p = A.run(d, taus=[0.5] + T, noise=2.0)
rows += summ(p, "気温に誤差σ=2℃を足す")
# 5 2020年度（コロナの年）を評価から除く
rows += summ(base[base.fold != "2020年度"], "2020年度を評価から除く")
# 6 関西エリア（2024年4月〜。学習2年・評価は2026年度上期のみ、較正は半年）
p = A.run(dk, folds=[("2026年度上期", "2026-04-01", "2026-09-30")], taus=[0.5] + T, calib_days=182)
rows += summ(p, "関西（評価183日・学習2年）")
out = pd.DataFrame(rows)
out.to_csv(RES / "robustness.csv", index=False)
pd.set_option("display.width", 250)
print(out.round(1).to_string())
