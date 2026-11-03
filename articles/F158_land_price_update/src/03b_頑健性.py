"""頑健性：地点・分け方・モデルを変えて、更新のしかたの並びが変わるか"""
import time
import pandas as pd
from common import load_points, load_panel, PARAMS, RES
from stratlib import run

t0 = time.time()
pts, pan = load_points(), load_panel()
small = dict(PARAMS); small.update(num_leaves=15, n_estimators=200)
variants = {
    "属性が10年変わらなかった地点だけ": dict(points=pts[pts["attr_changed"] == 0], fold_kind="block20", model_kind="lgbm"),
    "地点単位のランダム5分割": dict(points=pts, fold_kind="random", model_kind="lgbm"),
    "住宅地だけ": dict(points=pts[pts["land_use_class"] == "住宅地"], fold_kind="block20", model_kind="lgbm"),
    "小さいモデル（葉15・200本）": dict(points=pts, fold_kind="block20", model_kind="lgbm", params=small),
    "リッジ回帰": dict(points=pts, fold_kind="block20", model_kind="ridge"),
}
allt = []
for name, kw in variants.items():
    tab, _ = run(panel=pan, window=False, log=lambda s: None, **kw)
    tab.insert(0, "variant", name); allt.append(tab)
    print(name, round(time.time() - t0), flush=True)
    print(tab[tab.year == "2018-2026"][["strategy", "n", "median_ape", "rmse_log", "bias"]].round(4).to_string(), flush=True)
    pd.concat(allt).to_csv(RES / "robust_by_variant.csv", index=False)
print("done", round(time.time() - t0))
