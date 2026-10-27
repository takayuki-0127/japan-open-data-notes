"""地価の LightGBM に予測区間を付け、本当に目標の割合が区間に入るかを、データの分け方を変えて確かめる。

外側の CV（ランダム5分割／20km 四方のブロック5分割）で「まだ見ていない地点」を作り、
学習側をさらに「学習用 75%」と「較正用 25%」に分けて区間を作る。
- 分割コンフォーマル：較正用の |残差| の分位点 q で 予測±q
- 正規化コンフォーマル：較正用の半分で残差の大きさを別の LightGBM で学習し、残り半分で較正。、|残差|/予測幅 の分位点で幅を地点ごとに変える
- CQR：分位点回帰の LightGBM（下側・上側）で区間を作り、較正用で補正する（目標 90% だけ）
較正用の取り方は「ランダム」と「20km ブロック」の2通り。
結果：results/conformal_points.csv.gz（地点ごと）、results/coverage_main.csv（集計）"""
import numpy as np, pandas as pd, time
import lightgbm as lgb
from sklearn.model_selection import KFold, GroupKFold
from common import load, FEAT, PARAMS, SEED, RES

ALPHAS = [0.2, 0.1, 0.05]          # 目標 80・90・95%
CQR_ALPHAS = [0.1]                 # CQR は計算が重いので 90% だけ


def outer_splits(d, kind, k=5):
    if kind == "random":
        return list(KFold(k, shuffle=True, random_state=SEED).split(d))
    rng = np.random.default_rng(SEED)
    u = d["block20"].unique(); perm = dict(zip(u, rng.permutation(len(u))))
    return list(GroupKFold(k).split(d, groups=d["block20"].map(perm)))


def cal_split(tr, kind, frac=0.25, seed=SEED):
    rng = np.random.default_rng(seed)
    if kind == "random":
        m = rng.random(len(tr)) < frac
    else:
        b = tr["block20"].unique(); pick = set(rng.choice(b, int(round(len(b) * frac)), replace=False))
        m = tr["block20"].isin(pick).values
    return tr[~m], tr[m]


def qhat(scores, alpha):
    n = len(scores); lev = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return np.quantile(scores, lev, method="higher")


def fit(X, y, **kw):
    return lgb.LGBMRegressor(**{**PARAMS, **kw}).fit(X, y)


def run(d, outer, calk, methods=("split", "norm", "cqr"), frac=0.25, seed=SEED, alphas=ALPHAS):
    rows = []
    for f, (tri, tei) in enumerate(outer_splits(d, outer)):
        tr, te = d.iloc[tri], d.iloc[tei]
        pt, ca = cal_split(tr, calk, frac, seed + f)
        m = fit(pt[FEAT], pt["y"])
        pc, pe = m.predict(ca[FEAT]), m.predict(te[FEAT])
        out = pd.DataFrame({"code": te["code"].values, "y": te["y"].values, "pred": pe, "fold": f})
        rc = np.abs(ca["y"].values - pc)
        if "norm" in methods:
            # 残差の大きさのモデル：較正用を半分に分け、前半で「|残差|の大きさ」を学習、後半で較正する
            h = np.random.default_rng(seed + 100 + f).random(len(ca)) < 0.5
            s = fit(ca[h][FEAT], np.log(rc[h] + 1e-3))
            sc_b, se = np.exp(s.predict(ca[~h][FEAT])), np.exp(s.predict(te[FEAT]))
            rc_b = rc[~h]
        for al in alphas:
            t = int(round((1 - al) * 100))
            if "split" in methods:
                q = qhat(rc, al); out[f"split_lo{t}"], out[f"split_hi{t}"] = pe - q, pe + q
            if "norm" in methods:
                q = qhat(rc_b / sc_b, al); out[f"norm_lo{t}"], out[f"norm_hi{t}"] = pe - q * se, pe + q * se
            if "cqr" in methods and al in CQR_ALPHAS:
                lo = fit(pt[FEAT], pt["y"], objective="quantile", alpha=al / 2)
                hi = fit(pt[FEAT], pt["y"], objective="quantile", alpha=1 - al / 2)
                lc, hc = lo.predict(ca[FEAT]), hi.predict(ca[FEAT])
                q = qhat(np.maximum(lc - ca["y"].values, ca["y"].values - hc), al)
                out[f"cqr_lo{t}"], out[f"cqr_hi{t}"] = lo.predict(te[FEAT]) - q, hi.predict(te[FEAT]) + q
        rows.append(out)
    return pd.concat(rows, ignore_index=True)


def summarize(p, d, tag):
    meta = d.set_index("code")[["land_use_class", "pref"]]
    p = p.join(meta, on="code")
    res = []
    for c in [c for c in p.columns if c.endswith(("lo80", "lo90", "lo95"))]:
        meth, t = c.split("_lo"); hi = p[f"{meth}_hi{t}"]
        inside = (p["y"] >= p[c]) & (p["y"] <= hi)
        width = np.exp(hi - p[c])           # 上限÷下限（倍）
        res.append(dict(setting=tag, method=meth, target=int(t), coverage=inside.mean(),
                        width_ratio_median=np.median(width), n=len(p)))
    return pd.DataFrame(res)


if __name__ == "__main__":
    d = load(); t0 = time.time()
    allp, summ = [], []
    for outer, calk in [("random", "random"), ("block20", "random"), ("block20", "block20")]:
        p = run(d, outer, calk)
        tag = f"外側:{outer}／較正:{calk}"
        p["setting"] = tag; allp.append(p); summ.append(summarize(p, d, tag))
        print(tag, f"{time.time()-t0:.0f}s"); print(summ[-1].round(3).to_string())
    pd.concat(allp).to_csv(RES / "conformal_points.csv.gz", index=False, float_format="%.5f")
    pd.concat(summ).to_csv(RES / "coverage_main.csv", index=False, float_format="%.4f")
