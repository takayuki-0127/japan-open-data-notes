"""F110 探索の本体：グリッド・ランダム・TPE・ガウス過程（GP）のベイズ最適化で LightGBM の設定を選ぶ
使い方: python3 03_探索.py <task: land|power> <space: wide|narrow> <trials> <seeds カンマ区切り> <methods カンマ区切り> <出力名>
1回の探索（手法×乱数）ごとに results/trials_<出力名>.csv に追記するので、途中で止まっても続きから再開できる"""
import sys, csv, os
import optuna
from common import *
optuna.logging.set_verbosity(optuna.logging.WARNING)

task, space, n_trials = sys.argv[1], sys.argv[2], int(sys.argv[3])
seeds = [int(s) for s in sys.argv[4].split(",")]; methods = sys.argv[5].split(","); tag = sys.argv[6]
data = load_land() if task == "land" else load_power()
MAXR = 800 if task == "land" else 1000

SPACES = {  # 探索範囲（log=True は対数の目盛りで探す）
    "wide": dict(learning_rate=(0.02, 0.3, True), num_leaves=(4, 256, True), min_child_samples=(2, 200, True),
                 feature_fraction=(0.3, 1.0, False), bagging_fraction=(0.3, 1.0, False), lambda_l2=(1e-3, 30.0, True)),
    "narrow": dict(learning_rate=(0.05, 0.2, True), num_leaves=(16, 64, True), min_child_samples=(10, 50, True),
                   feature_fraction=(0.6, 1.0, False), bagging_fraction=(0.6, 1.0, False), lambda_l2=(0.01, 3.0, True)),
}
INTS = {"num_leaves", "min_child_samples"}
# グリッド：4つの設定を 3×3×2×2=36 通り（残りは既定値のまま）。範囲は探索範囲の中に収める
GRID = {"wide": dict(learning_rate=[0.03, 0.1, 0.3], num_leaves=[8, 32, 128], min_child_samples=[5, 50],
                     feature_fraction=[0.6, 1.0]),
        "narrow": dict(learning_rate=[0.05, 0.1, 0.2], num_leaves=[16, 32, 64], min_child_samples=[10, 40],
                       feature_fraction=[0.6, 1.0])}
GRID_FIXED = dict(bagging_fraction=1.0, lambda_l2=0.0)

out = RES / f"trials_{tag}.csv"
done = set()
if out.exists():
    o = pd.read_csv(out); done = set(zip(o.method, o.seed))
fields = ["task", "space", "method", "seed", "trial", "valid_rmse", "test_rmse", "best_iter", "sec"] + list(SPACES["wide"])


def objective_factory(method, seed, rows):
    def obj(trial):
        S = SPACES[space]
        if method == "grid":
            p = {k: trial.suggest_categorical(k, v) for k, v in GRID[space].items()}; p.update(GRID_FIXED)
        else:
            p = {}
            for k, (lo, hi, lg) in S.items():
                p[k] = trial.suggest_int(k, lo, hi, log=lg) if k in INTS else trial.suggest_float(k, lo, hi, log=lg)
        v, t, it, sec = fit_eval(data, p, MAXR)
        rows.append(dict(task=task, space=space, method=method, seed=seed, trial=trial.number, valid_rmse=v,
                         test_rmse=t, best_iter=it, sec=sec, **p))
        return v
    return obj


for seed in seeds:
    for method in methods:
        if (method, seed) in done:
            continue
        if method == "grid":
            sampler = optuna.samplers.GridSampler(GRID[space], seed=seed)
            n = min(n_trials, int(np.prod([len(v) for v in GRID[space].values()])))
        elif method == "random":
            sampler = optuna.samplers.RandomSampler(seed=seed); n = n_trials
        elif method == "tpe":
            sampler = optuna.samplers.TPESampler(seed=seed, n_startup_trials=10, multivariate=True); n = n_trials
        else:
            sampler = optuna.samplers.GPSampler(seed=seed, n_startup_trials=10); n = n_trials
        rows = []
        st = optuna.create_study(direction="minimize", sampler=sampler)
        st.optimize(objective_factory(method, seed, rows), n_trials=n)
        new = not out.exists()
        with open(out, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            if new: w.writeheader()
            w.writerows(rows)
        print(task, space, method, seed, "best", round(min(r["valid_rmse"] for r in rows), 5),
              "sec", round(sum(r["sec"] for r in rows)), flush=True)
