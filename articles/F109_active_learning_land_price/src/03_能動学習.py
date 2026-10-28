"""F109 能動学習のシミュレーション。
地価公示の25,565地点を「まだ値段を知らない候補（プール）」と「評価用（テスト）」に分け、
少数の地点から始めて、選び方（ランダム／不確実性／多様性／不確実性＋多様性）ごとに200地点ずつ値段を「聞いて」足し、
テストの誤差がどう下がるかを比べる。
使い方: python3 src/03_能動学習.py main|robust|full
"""
import sys, time, json
import numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.cluster import MiniBatchKMeans
from sklearn.linear_model import Ridge
from common import load, NUM, CAT, DATA, RES, SEED

D = load()
Y = D["y"].values
X = D[NUM + CAT]
Z = np.load(DATA / "z_numeric.npy")
COMM = (D["land_use_class"] == "商業地").values
BLOCK = D["block20"].values
# リッジ用の行列（数値は欠損を中央値で埋めて標準化＋欠損フラグ、駅距離は log、カテゴリはダミー）
_n = D[NUM].copy(); _n["dist_station"] = np.log(_n["dist_station"].fillna(_n["dist_station"].median()) + 50)
_flag = _n.isna().astype(float).add_suffix("_na"); _flag = _flag.loc[:, _flag.sum() > 0]
_n = _n.fillna(_n.median()); _n = (_n - _n.mean()) / _n.std()
XR = pd.concat([_n, _flag, pd.get_dummies(D[CAT].astype(str), dtype=float)], axis=1).values.astype("float32")

LGB = dict(n_estimators=200, learning_rate=0.08, num_leaves=31, min_child_samples=10, subsample=0.8, subsample_freq=1,
           colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, n_jobs=1)
K_COMM = 4  # 委員会（ブートストラップで作る4つのモデル）


def committee(lab, idx_pred, model, rng):
    """ラベルつきの地点 lab で4つのモデルをブートストラップ学習し、idx_pred の予測を返す（4×len）"""
    P = np.empty((K_COMM, len(idx_pred)), dtype="float32")
    for k in range(K_COMM):
        b = rng.choice(lab, size=len(lab), replace=True)
        if model == "lgb":
            m = lgb.LGBMRegressor(**LGB, random_state=int(rng.integers(1e9))).fit(X.iloc[b], Y[b])
            P[k] = m.predict(X.iloc[idx_pred])
        else:
            m = Ridge(alpha=1.0).fit(XR[b], Y[b])
            P[k] = m.predict(XR[idx_pred])
    return P


def nearest_to_centers(cand, k, rng):
    km = MiniBatchKMeans(n_clusters=k, n_init=1, batch_size=2048, random_state=int(rng.integers(1e9))).fit(Z[cand])
    dist = ((Z[cand][:, None, :] - km.cluster_centers_[None, :, :]) ** 2).sum(-1) if len(cand) * k < 4e6 else None
    chosen = []
    if dist is None:
        lab = km.labels_
        for c in range(k):
            mem = np.where(lab == c)[0]
            if len(mem) == 0: continue
            dd = ((Z[cand[mem]] - km.cluster_centers_[c]) ** 2).sum(1)
            chosen.append(cand[mem[np.argmin(dd)]])
    else:
        for c in np.argsort(dist.min(0)):
            o = np.argsort(dist[:, c])
            for j in o:
                if cand[j] not in chosen:
                    chosen.append(cand[j]); break
    chosen = list(dict.fromkeys(chosen))
    if len(chosen) < k:  # 足りない分はランダム
        rest = np.setdiff1d(cand, chosen)
        chosen += list(rng.choice(rest, k - len(chosen), replace=False))
    return np.array(chosen[:k])


def split(seed, test_kind):
    rng = np.random.default_rng(SEED + seed)
    if test_kind == "random":
        test = rng.choice(len(D), int(0.2 * len(D)), replace=False)
    else:  # 20km四方のブロック単位で約2割を評価用に
        ub = np.unique(BLOCK); rng.shuffle(ub)
        cnt = pd.Series(BLOCK).value_counts()
        tb, s = [], 0
        for b in ub:
            if s >= 0.2 * len(D): break
            tb.append(b); s += cnt[b]
        test = np.where(np.isin(BLOCK, tb))[0]
    pool = np.setdiff1d(np.arange(len(D)), test)
    return pool, test


def metrics(y, p):
    ape = np.abs(np.exp(p - y) - 1)
    hi = y >= np.quantile(Y, 0.9); lo = y <= np.quantile(Y, 0.1)
    return dict(rmse=float(np.sqrt(np.mean((p - y) ** 2))), median_ape=float(np.median(ape)),
                within20=float(np.mean(ape <= 0.2)),
                rmse_top10=float(np.sqrt(np.mean((p[hi] - y[hi]) ** 2))) if hi.any() else np.nan,
                rmse_bottom10=float(np.sqrt(np.mean((p[lo] - y[lo]) ** 2))) if lo.any() else np.nan)


def run(seed, strategy, init=200, batch=200, max_n=3000, model="lgb", test_kind="random", keep_sel=False):
    rng = np.random.default_rng(10_000 * seed + hash(strategy) % 997)
    pool, test = split(seed, test_kind)
    lab = np.random.default_rng(SEED + 100 + seed).choice(pool, init, replace=False)  # 初期は選び方によらず同じ
    rows = []
    while True:
        unl = np.setdiff1d(pool, lab)
        need = min(batch, max_n - len(lab)) if len(lab) < max_n else 0
        idx_pred = np.concatenate([test, unl]) if need > 0 and strategy in ("uncertainty", "hybrid") else test
        P = committee(lab, idx_pred, model, rng)
        pt = P[:, :len(test)].mean(0)
        r = dict(seed=seed, strategy=strategy, model=model, test=test_kind, init=init, batch=batch, n=len(lab),
                 share_comm_labeled=float(COMM[lab].mean()), y_sd_labeled=float(Y[lab].std()),
                 **metrics(Y[test], pt))
        rows.append(r)
        if need <= 0:
            break
        if strategy == "random":
            new = rng.choice(unl, need, replace=False)
        elif strategy == "uncertainty":
            v = P[:, len(test):].var(0)
            new = unl[np.argsort(-v)[:need]]
        elif strategy == "diversity":
            new = nearest_to_centers(unl, need, rng)
        elif strategy == "hybrid":
            v = P[:, len(test):].var(0)
            cand = unl[np.argsort(-v)[:5 * need]]
            new = nearest_to_centers(cand, need, rng)
        lab = np.concatenate([lab, new])
    sel = lab if keep_sel else None
    return rows, sel


STRATS = ["random", "uncertainty", "diversity", "hybrid"]


def main_part():
    rows, sels = [], {}
    for seed in range(8):
        for s in STRATS:
            t = time.time()
            r, sel = run(seed, s, keep_sel=(seed == 0))
            rows += r
            if seed == 0: sels[s] = sel.tolist()
            print(seed, s, round(time.time() - t, 1), r[-1]["rmse"], flush=True)
            pd.DataFrame(rows).to_csv(RES / "al_main.csv", index=False)
    json.dump(sels, open(RES / "selected_seed0.json", "w"))


def robust_part():
    rows = []
    confs = {
        "初期50地点": dict(init=50, batch=200, max_n=2050),
        "初期1,000地点": dict(init=1000, batch=200, max_n=3000),
        "1回に50地点": dict(init=200, batch=50, max_n=1000),
        "1回に1,000地点": dict(init=200, batch=1000, max_n=3200),
        "評価用を20kmブロックで分ける": dict(test_kind="block"),
        "リッジ回帰（線形）": dict(model="ridge"),
    }
    for name, c in confs.items():
        for seed in range(4):
            for s in STRATS:
                t = time.time()
                r, _ = run(seed, s, **c)
                for x in r: x["setting"] = name
                rows += r
                print(name, seed, s, round(time.time() - t, 1), r[-1]["rmse"], flush=True)
                pd.DataFrame(rows).to_csv(RES / "al_robust.csv", index=False)


def full_part():
    """参考：プールを全部（約2万地点）使ったときの誤差"""
    rows = []
    for test_kind, model in (("random", "lgb"), ("block", "lgb"), ("random", "ridge")):
        for seed in range(4):
            pool, test = split(seed, test_kind)
            P = committee(pool, test, model, np.random.default_rng(seed))
            rows.append(dict(seed=seed, test=test_kind, model=model, n=len(pool), **metrics(Y[test], P.mean(0))))
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(RES / "al_full_pool.csv", index=False)


if __name__ == "__main__":
    {"main": main_part, "robust": robust_part, "full": full_part}[sys.argv[1]]()
