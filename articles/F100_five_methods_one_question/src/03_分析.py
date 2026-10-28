"""03 分析：同じ問いを5つの手法（回帰・固定効果・マッチング・DML・空間回帰）で推定し、答えがそろうかを比べる。

問い1：保育所等に通う子どもが多い（増えた）市区町村ほど、合計特殊出生率は高い（上がった）か
問い2：同じく、女性の労働力率は高い（上がった）か（F16 と同じ問い。手法の比較の確認用）
比べ方（設計）：水準（2015年の在所児 → 2018〜22年の出生率／2015年の労働力率）と、変化（2010→15年の在所児の変化 → 出生率・労働力率の変化）
効果の単位：0〜5歳100人あたりの在所児が 10人 多い（増えた）とき、結果が何だけ違うか
"""
import json, warnings, itertools, time
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMRegressor
import doubleml as dml
from libpysal.weights import W as PW, KNN
from spreg import ML_Error, ML_Lag
from common import DATA, RES, SEED, UNIT, pref_dummies
warnings.filterwarnings("ignore")

CACHE_F = RES / "_cache.json"
CACHE = json.load(open(CACHE_F)) if CACHE_F.exists() else {}


def cached(key, fn):
    if key in CACHE:
        return CACHE[key]
    t = time.time()
    out = fn()
    CACHE[key] = out
    json.dump(CACHE, open(CACHE_F, "w"), ensure_ascii=False)
    print(f"{key}: {out.get('coef', float('nan')):+.4f} [{out.get('lo', float('nan')):+.4f}, {out.get('hi', float('nan')):+.4f}] n={out.get('n')} ({time.time() - t:.0f}s)", flush=True)
    return out


def load(k):
    return pd.read_csv(DATA / f"{k}.csv", dtype={"code": str}).set_index("code")


DS = {k: load(k) for k in ["q1_level", "q1_change", "q2_level", "q2_change"]}
ADJ = pd.read_csv(DATA / "adjacency.csv", dtype=str)
CEN = pd.read_csv(DATA / "centroids_km.csv", dtype={"code": str}).set_index("code")
TV = ["女性65歳以上の割合の変化", "女性15〜64歳の割合の変化", "人口増減率", "0〜5歳の割合の変化"]  # 期間中に変わる条件（固定効果で使う）


def design(k, pref=True, sample="all", treat="D"):
    """Y・D と、その設計で使う条件の列を返す"""
    df = DS[k].copy()
    if sample == "pop1man":
        df = df[np.exp(df["log人口"]) >= 10000]
    if sample == "no_big":  # 政令市・東京23区を除く
        df = df[~((df.index.str[:2] == "13") & (df.index.str[2] == "1")) & ~(df.index.str[2:] == "100")]
    df["D"] = df[treat] / UNIT if treat == "D" else df[treat]
    X = df.drop(columns=["name", "Y", "D", "D_fac"])
    if pref:
        X = pd.concat([X, pref_dummies(X.index)], axis=1)
    return df.Y, df.D, X


def res(coef, se, n, **kw):
    return dict(coef=float(coef), se=float(se), lo=float(coef - 1.96 * se), hi=float(coef + 1.96 * se), n=int(n), **kw)


# ---------------- 1. 回帰（重回帰、頑健な標準誤差） ----------------
def m_ols(Y, D, X, ctrl=True):
    Z = pd.concat([D, X], axis=1) if ctrl else D.to_frame()
    r = sm.OLS(Y, sm.add_constant(Z)).fit(cov_type="HC3")
    return res(r.params["D"], r.bse["D"], len(Y), r2=float(r.rsquared))


# ---------------- 2. 固定効果（2期間の市区町村固定効果＝変化どうしの回帰） ----------------
def m_fe(Y, D, X, pref=True):
    """変わらない地域の性格は差をとって消える。残すのは期間中に変わる条件と、県ごとの傾向（県ダミー）だけ。
    標準誤差は都道府県でクラスタ"""
    cols = [c for c in X.columns if c in TV or (pref and c.startswith("県_"))]
    Z = pd.concat([D, X[cols]], axis=1)
    g = pd.Series([c[:2] for c in Y.index], index=Y.index).astype(int)
    r = sm.OLS(Y, sm.add_constant(Z)).fit(cov_type="cluster", cov_kwds={"groups": g})
    return res(r.params["D"], r.bse["D"], len(Y))


# ---------------- 3. マッチング（傾向スコア、最近傍1対1・復元あり・キャリパー） ----------------
def _match_once(Y, D, X, rng=None, ratio=1, caliper=0.2):
    hi, lo = D.quantile(2 / 3), D.quantile(1 / 3)
    keep = (D >= hi) | (D <= lo)
    y, d, x = Y[keep].values, D[keep].values, X[keep].values
    t = (d >= hi).astype(int)
    if rng is not None:
        i = rng.integers(0, len(y), len(y)); y, d, x, t = y[i], d[i], x[i], t[i]
    xs = StandardScaler().fit_transform(x)
    ps = np.clip(LogisticRegression(C=1.0, max_iter=2000).fit(xs, t).predict_proba(xs)[:, 1], 1e-6, 1 - 1e-6)
    lg = np.log(ps / (1 - ps))
    cal = caliper * lg.std() if caliper else np.inf
    ti, ci = np.where(t == 1)[0], np.where(t == 0)[0]
    diffs, dd, used = [], [], []
    for i in ti:
        dist = np.abs(lg[ci] - lg[i])
        o = np.argsort(dist)[:ratio]
        o = o[dist[o] <= cal]
        if len(o) == 0:
            continue
        j = ci[o]
        diffs.append(y[i] - y[j].mean()); dd.append(d[i] - d[j].mean()); used.append((i, j))
    if not diffs:
        return np.nan, np.nan, 0, len(ti), (t, xs, used)
    att, gap = float(np.mean(diffs)), float(np.mean(dd))
    return att, gap, len(diffs), len(ti), (t, xs, used)


def m_match(Y, D, X, ratio=1, caliper=0.2, B=200):
    att, gap, nm, nt, (t, xs, used) = _match_once(Y, D, X, None, ratio, caliper)
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(B):
        a, g, *_ = _match_once(Y, D, X, rng, ratio, caliper)
        boots.append(a)  # ATT（出生率の差）を再標本化し、在所児の差（元のデータの値）で割って単位をそろえる
    # バランス（標準化平均差の絶対値の平均）：マッチング前と後
    smd_b = np.abs(xs[t == 1].mean(0) - xs[t == 0].mean(0))
    cj = np.concatenate([j for _, j in used]); tj = np.array([i for i, _ in used])
    smd_a = np.abs(xs[tj].mean(0) - xs[cj].mean(0))
    return res(att / gap, np.nanstd(boots, ddof=1) / gap, len(Y), att=att, gap=gap, matched=nm, treated=nt,
               smd_before=float(np.nanmean(smd_b)), smd_after=float(np.nanmean(smd_a)))


# ---------------- 4. ダブル機械学習（部分線形モデル） ----------------
def learner(kind):
    if kind == "rf":
        return RandomForestRegressor(n_estimators=200, min_samples_leaf=5, max_features=0.33, n_jobs=-1, random_state=SEED)
    if kind == "lgbm":
        return LGBMRegressor(n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=20, subsample=0.8, subsample_freq=1,
                             colsample_bytree=0.7, verbose=-1, random_state=SEED)
    return make_pipeline(StandardScaler(), LassoCV(cv=5, random_state=SEED, max_iter=20000))


def m_dml(Y, D, X, kind="rf", reps=3, folds=5, seed=SEED):
    df = pd.concat([Y.rename("Y"), D.rename("D"), X], axis=1)
    df.columns = ["Y", "D"] + [f"x{i}" for i in range(X.shape[1])]
    data = dml.DoubleMLData(df, y_col="Y", d_cols="D", x_cols=list(df.columns[2:]))
    np.random.seed(seed)
    m = dml.DoubleMLPLR(data, ml_l=learner(kind), ml_m=learner(kind), n_folds=folds, n_rep=reps, score="partialling out")
    m.fit()
    return res(m.coef[0], m.se[0], len(Y))


# ---------------- 5. 空間回帰（空間誤差モデル・空間ラグモデル、最尤法） ----------------
def weights(codes, kind="queen"):
    codes = list(codes)
    if kind == "queen":
        s = set(codes)
        nb = {c: [] for c in codes}
        for a, b in ADJ[ADJ.code.isin(s) & ADJ.neighbor.isin(s)].itertuples(index=False):
            nb[a].append(b)
        if all(nb.values()):
            w = PW(nb, silence_warnings=True)
            w.transform = "r"
            return w, codes
    w = KNN.from_array(CEN.loc[codes].values, k=6, ids=codes)  # 隣がない区域が出るときと、頑健性で使う
    w.transform = "r"
    return w, codes


def m_spatial(Y, D, X, kind="error", wkind="queen"):
    w, codes = weights(Y.index, wkind)
    Z = pd.concat([D, X], axis=1).loc[codes]
    Z = Z.loc[:, Z.std() > 0]
    y = Y.loc[codes].values.reshape(-1, 1)
    if kind == "error":
        m = ML_Error(y, Z.values, w=w, name_x=list(Z.columns))
        return res(m.betas[1, 0], m.std_err[1], len(y), lam=float(m.lam))
    m = ML_Lag(y, Z.values, w=w, name_x=list(Z.columns))
    rho = float(m.rho)
    # 直接効果＝β×(I−ρW)^{-1} の対角の平均。区間は β の標準誤差に同じ倍率をかけた近似
    Wd = w.full()[0]
    mult = float(np.mean(np.diag(np.linalg.inv(np.eye(len(y)) - rho * Wd))))
    tot = 1 / (1 - rho)
    return res(m.betas[1, 0] * mult, m.std_err[1] * mult, len(y), rho=rho, total=float(m.betas[1, 0] * tot))


METHODS = {
    "回帰": lambda Y, D, X, **k: m_ols(Y, D, X),
    "固定効果": lambda Y, D, X, pref=True, **k: m_fe(Y, D, X, pref),
    "マッチング": lambda Y, D, X, **k: m_match(Y, D, X),
    "DML（RF）": lambda Y, D, X, **k: m_dml(Y, D, X, "rf"),
    "DML（LightGBM）": lambda Y, D, X, **k: m_dml(Y, D, X, "lgbm"),
    "DML（Lasso）": lambda Y, D, X, **k: m_dml(Y, D, X, "lasso"),
    "空間誤差モデル": lambda Y, D, X, **k: m_spatial(Y, D, X, "error"),
    "空間ラグモデル（直接効果）": lambda Y, D, X, **k: m_spatial(Y, D, X, "lag"),
}


if __name__ == "__main__":
    R = {"describe": {}, "spec": [], "robust": {}}
    for k, df in DS.items():
        R["describe"][k] = dict(n=len(df), Y_mean=float(df.Y.mean()), Y_sd=float(df.Y.std()), D_mean=float(df.D.mean()), D_sd=float(df.D.std()),
                                corr=float(np.corrcoef(df.Y, df.D)[0, 1]), n_x=int(df.shape[1] - 4))
    # 単純な回帰（条件なし）
    R["naive"] = {k: cached(f"naive|{k}", lambda k=k: m_ols(*design(k), ctrl=False)) for k in DS}
    # 手法×比べ方×県の扱い×対象 のすべての組み合わせ（仕様の曲線）
    for q in ["q1", "q2"]:
        for des in ["level", "change"]:
            k = f"{q}_{des}"
            for pref, sample, meth in itertools.product([True, False], ["all", "pop1man"], METHODS):
                if meth == "固定効果" and des == "level":
                    continue
                key = f"{k}|{meth}|pref={pref}|{sample}"
                Y, D, X = design(k, pref, sample)
                out = cached(key, lambda: METHODS[meth](Y, D, X, pref=pref))
                R["spec"].append(dict(q=q, design=des, method=meth, pref=pref, sample=sample, **{a: b for a, b in out.items()}))
    # 頑健性（問い1、県あり・全体）
    rob = {}
    for des in ["level", "change"]:
        k = f"q1_{des}"
        Y, D, X = design(k)
        rob[f"{des}|DML（RF）乱数・10回"] = cached(f"rob|{k}|dml_rf_rep10", lambda: m_dml(Y, D, X, "rf", reps=10, seed=SEED + 1))
        rob[f"{des}|マッチング 1対3"] = cached(f"rob|{k}|match13", lambda: m_match(Y, D, X, ratio=3))
        rob[f"{des}|マッチング キャリパーなし"] = cached(f"rob|{k}|match_nocal", lambda: m_match(Y, D, X, caliper=None))
        rob[f"{des}|空間誤差モデル 近い6区域"] = cached(f"rob|{k}|sem_knn6", lambda: m_spatial(Y, D, X, "error", "knn6"))
        Yb, Db, Xb = design(k, sample="no_big")
        for meth in ["回帰", "マッチング", "DML（RF）", "空間誤差モデル"] + (["固定効果"] if des == "change" else []):
            rob[f"{des}|政令市・23区を除く|{meth}"] = cached(f"rob|{k}|nobig|{meth}", lambda: METHODS[meth](Yb, Db, Xb))
        # 処置を「保育所等の数（0〜5歳千人あたり）」に変える（単位が違うので、1標準偏差あたりに直す）
        Yf, Df, Xf = design(k, treat="D_fac")
        sd = float(Df.std())
        for meth in ["回帰", "マッチング", "DML（RF）", "空間誤差モデル"] + (["固定効果"] if des == "change" else []):
            o = cached(f"rob|{k}|fac|{meth}", lambda: METHODS[meth](Yf, Df, Xf))
            rob[f"{des}|処置を保育所の数に（1SDあたり）|{meth}"] = {a: (b * sd if a in ("coef", "se", "lo", "hi") else b) for a, b in o.items()}
        # 比べるため、在所児も1SDあたりに直した値（県あり・全体）
        sdd = float(D.std())
        for meth in ["回帰", "マッチング", "DML（RF）", "空間誤差モデル"] + (["固定効果"] if des == "change" else []):
            o = cached(f"{k}|{meth}|pref=True|all", None)
            rob[f"{des}|在所児（1SDあたり）|{meth}"] = {a: (b * sdd if a in ("coef", "se", "lo", "hi") else b) for a, b in o.items()}
    R["robust"] = rob
    # 条件を1段ずつ足すと、回帰の答えはどう動くか（問い1）
    steps = {}
    for des in ["level", "change"]:
        k = f"q1_{des}"
        Y, D, X = design(k, pref=False)
        base = [c for c in X.columns if c in DS["q1_level"].columns]  # 2010年の地域の性格
        groups = [("条件なし", []),
                  ("人口・密度", ["log人口", "log人口密度"]),
                  ("＋年齢・世帯", ["女性65歳以上の割合", "女性15〜64歳の割合", "核家族世帯の割合", "単独世帯の割合", "核家族以外の世帯の割合", "母子世帯の割合"]),
                  ("＋産業・通勤・所得", ["第1次産業の割合", "第2次産業の割合", "第3次産業の割合", "女性の市外への通勤の割合", "昼夜間人口比率", "納税者1人あたり所得", "納税者の割合"]),
                  ("＋財政・学歴・雇用", [c for c in base if c not in ["log人口", "log人口密度"]]),
                  ]
        if des == "change":
            groups.append(("＋前の出生率・在所児", [c for c in X.columns if c not in base]))
        cols = []
        steps[des] = []
        for lab, add in groups:
            cols = list(dict.fromkeys(cols + add))
            o = cached(f"steps|{k}|{lab}", lambda: m_ols(Y, D, X[cols], ctrl=bool(cols)))
            steps[des].append(dict(step=lab, **o))
        o = cached(f"steps|{k}|＋県", lambda: m_ols(*design(k, pref=True)))
        steps[des].append(dict(step="＋県", **o))
        o = cached(f"steps|{k}|＋空間（誤差）", lambda: m_spatial(*design(k, pref=True), "error"))
        steps[des].append(dict(step="＋隣との似かた（空間誤差）", **o))
    R["steps"] = steps
    json.dump(R, open(RES / "results.json", "w"), ensure_ascii=False, indent=1)
    S = pd.DataFrame(R["spec"])
    S.to_csv(RES / "specifications.csv", index=False, encoding="utf-8")
    pd.DataFrame([dict(item=k, **v) for k, v in rob.items()]).to_csv(RES / "robustness.csv", index=False, encoding="utf-8")
    main = S[(S.pref) & (S["sample"] == "all")]
    print(main[["q", "design", "method", "coef", "lo", "hi"]].round(4).to_string())
