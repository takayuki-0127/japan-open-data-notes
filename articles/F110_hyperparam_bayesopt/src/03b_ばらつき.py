"""F110 選んだ設定は本当に良いのか：学習の乱数とデータの分け方を変えて、既定値と各手法の最良設定を学習し直す"""
from common import *
P = ["learning_rate", "num_leaves", "min_child_samples", "feature_fraction", "bagging_fraction", "lambda_l2"]
rows = []
for task, tag in [("power", "power_main"), ("land", "land_main")]:
    t = pd.read_csv(RES / f"trials_{tag}.csv")
    cands = {"default": DEFAULT}
    for m in METHODS:
        b = t[(t.method == m) & (t.seed == 0)].sort_values("valid_rmse").iloc[0]
        cands[m] = {k: b[k] for k in P}
    splits = [SEED, SEED + 1, SEED + 2] if task == "land" else [None]
    for sp in splits:
        data = load_land(sp) if task == "land" else load_power()
        for name, p in cands.items():
            for ms in range(5 if sp in (SEED, None) else 2):
                v, te, it, sec = fit_eval(data, p, 800 if task == "land" else 1000, seed=ms)
                rows.append(dict(task=task, split=sp, config=name, model_seed=ms, valid_rmse=v, test_rmse=te, best_iter=it))
        print(task, sp, "done", flush=True)
pd.DataFrame(rows).to_csv(RES / "refit_noise.csv", index=False)
