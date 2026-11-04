"""03b 頑健性：標本・モデル・SAGE の計算設定を変えて、Shapley の取り分が動くか

1. 標本：地価は評価に回す地点の選び方（乱数）を変える／学習データを2,000地点に減らす。
   電力は学習期間を直近2年（2021年4月〜2023年3月）に縮める。
2. モデル：LightGBM をランダムフォレスト型に替えて SAGE を測る。
3. SAGE の計算設定：評価の点数（1,000・4,000）と置き換えの回数（K=4・16）。
グループのまとめ方の頑健性は 03_分析.py（regroup_*.csv）。
"""
import time
import numpy as np, pandas as pd
from common import RES, SEED, L_GROUPS, P_GROUPS, P_GROUPS7, data_land, data_power
from shapley import refit_values, sage_values, fit_lgbm, coarsen, shapley, r2_matrix

T0 = time.time()


def log(s):
    print(f"[{time.time() - T0:6.0f}s] {s}", flush=True)


def cached(name, fn):
    f = RES / f"_cache_{name}.npz"
    if f.exists():
        return np.load(f)["a"]
    a = fn()
    np.savez_compressed(f, a=a)
    return a


rows = []


def add(data, check, method, v, groups, base_groups=None):
    vv = coarsen(v, base_groups, groups) if base_groups else v
    phi = shapley(vv, len(groups))
    tot = vv[-1] - vv[0]
    for g, p in zip(groups, phi):
        rows.append({"データ": data, "確かめ方": check, "方法": method, "グループ": g, "shapley": p, "割合": p / tot,
                     "R2全変数": vv[-1]})


# ---- 地価 ----
Xtr, ytr, Xte, yte, _ = data_land()
add("地価", "基本", "学び直し", r2_matrix(yte, cached("地価_refit_lgbm", lambda: None)), L_GROUPS)
add("地価", "基本", "SAGE", cached("地価_sage_K32", lambda: None), L_GROUPS)
rng = np.random.default_rng(SEED)
sub = rng.choice(len(Xtr), 2000, replace=False)
log("地価：学習2,000地点")
P = cached("地価_refit_lgbm_n2000", lambda: refit_values(Xtr.iloc[sub].reset_index(drop=True), ytr[sub], Xte, yte,
                                                          L_GROUPS, "lgbm", log))
add("地価", "学習データを2,000地点に", "学び直し", r2_matrix(yte, P), L_GROUPS)
full = fit_lgbm(Xtr, ytr)
for n, K in ((1000, 32), (4000, 32), (2000, 8), (2000, 64)):
    log(f"地価：SAGE n={n} K={K}")
    v = cached(f"地価_sage_n{n}_K{K}", lambda: sage_values(full, Xte, yte, L_GROUPS, n=n, K=K, seed=1))
    add("地価", f"SAGE 点数{n}・置き換え{K}回", "SAGE", v, L_GROUPS)
log("地価：ランダムフォレスト型")
rf = fit_lgbm(Xtr, ytr, dict(boosting_type="rf", subsample=0.632, colsample_bytree=0.5, n_estimators=300,
                             learning_rate=1.0))
add("地価", "モデルをランダムフォレスト型に", "SAGE", cached("地価_sage_rf", lambda: sage_values(rf, Xte, yte, L_GROUPS, K=32)), L_GROUPS)
log("地価：評価地点の選び方（乱数7）")
Xtr2, ytr2, Xte2, yte2, _ = data_land(seed=7)
P2 = cached("地価_refit_lgbm_seed7", lambda: refit_values(Xtr2, ytr2, Xte2, yte2, L_GROUPS, "lgbm", log))
add("地価", "評価地点の選び方を変える", "学び直し", r2_matrix(yte2, P2), L_GROUPS)

# ---- 電力 ----
Xtr, ytr, Xte, yte, idx = data_power()
add("電力需要", "基本", "学び直し", r2_matrix(yte, cached("電力需要_refit_lgbm", lambda: None)), P_GROUPS, P_GROUPS7)
add("電力需要", "基本", "SAGE", cached("電力需要_sage_K32", lambda: None), P_GROUPS, P_GROUPS7)
log("電力：学習を直近2年に")
# 学習データの行は時間順。最後の約2年（17,520時間）
P = cached("電力需要_refit_lgbm_last2y", lambda: refit_values(Xtr.iloc[-17520:].reset_index(drop=True), ytr[-17520:],
                                                              Xte, yte, P_GROUPS7, "lgbm", log))
add("電力需要", "学習を直近2年に", "学び直し", r2_matrix(yte, P), P_GROUPS, P_GROUPS7)
full = fit_lgbm(Xtr, ytr)
for n, K in ((1000, 32), (4000, 32), (2000, 8), (2000, 64)):
    log(f"電力：SAGE n={n} K={K}")
    v = cached(f"電力需要_sage_n{n}_K{K}", lambda: sage_values(full, Xte, yte, P_GROUPS, n=n, K=K, seed=1))
    add("電力需要", f"SAGE 点数{n}・置き換え{K}回", "SAGE", v, P_GROUPS)
log("電力：ランダムフォレスト型")
rf = fit_lgbm(Xtr, ytr, dict(boosting_type="rf", subsample=0.632, colsample_bytree=0.5, n_estimators=300,
                             learning_rate=1.0))
add("電力需要", "モデルをランダムフォレスト型に", "SAGE", cached("電力需要_sage_rf", lambda: sage_values(rf, Xte, yte, P_GROUPS, K=32)),
    P_GROUPS)

pd.DataFrame(rows).to_csv(RES / "robustness.csv", index=False)
log("終了")
