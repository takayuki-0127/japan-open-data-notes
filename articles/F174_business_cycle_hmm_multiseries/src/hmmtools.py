"""隠れマルコフモデルの推定と評価の道具"""
import warnings
import numpy as np, pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.special import logsumexp

warnings.filterwarnings("ignore")

def fit_best(X, K, cov="diag", n_init=20, seed=42, n_iter=500, init_model=None):
    """初期値を変えて n_init 回推定し、対数尤度がいちばん高いモデルを返す"""
    best, best_ll = None, -np.inf
    rng = np.random.RandomState(seed)
    trials = []
    if init_model is not None:
        trials.append(("prev", None))
    trials += [("rand", int(rng.randint(1e9))) for _ in range(n_init)]
    for kind, s in trials:
        if kind == "prev":
            m = GaussianHMM(n_components=K, covariance_type=cov, n_iter=n_iter, tol=1e-4,
                            random_state=0, init_params="", params="stmc")
            m.startprob_ = init_model.startprob_.copy()
            m.transmat_ = init_model.transmat_.copy()
            m.means_ = init_model.means_.copy()
            try:
                m.covars_ = _covars_param(init_model, cov)
            except ValueError:
                continue
        else:
            m = GaussianHMM(n_components=K, covariance_type=cov, n_iter=n_iter, tol=1e-4,
                            random_state=s, min_covar=1e-3)
        try:
            m.fit(X)
            ll = m.score(X)
        except Exception:
            continue
        if not np.isfinite(ll):
            continue
        # 1か月しか続かないような退化した解（とどまる確率がほぼ0の状態）は除く
        if np.min(np.diag(m.transmat_)) < 0.05:
            continue
        if ll > best_ll:
            best, best_ll = m, ll
    return best, best_ll

def _covars_param(m, cov):
    c = m.covars_
    if cov == "diag":
        return np.array([np.diag(ci) for ci in c])
    c = (c + np.transpose(c, (0, 2, 1))) / 2          # 数値誤差で非対称になるのを直す
    return c + 1e-6 * np.eye(c.shape[1])[None]

def n_params(m, cov, d):
    K = m.n_components
    p = (K - 1) + K * (K - 1) + K * d
    p += K * d if cov == "diag" else K * d * (d + 1) // 2
    return p

def recession_states(m):
    """平均（系列の平均、標準化した単位）がマイナスの状態を「後退」とみなす"""
    return [k for k in range(m.n_components) if m.means_[k].mean() < 0]

def filtered_probs(m, X):
    """その月までのデータだけを使う確率（前向きアルゴリズム）"""
    logB = m._compute_log_likelihood(X)
    logA = np.log(np.maximum(m.transmat_, 1e-300))
    la = np.log(np.maximum(m.startprob_, 1e-300)) + logB[0]
    out = np.empty_like(logB)
    out[0] = la - logsumexp(la)
    for t in range(1, len(X)):
        la = logsumexp(out[t - 1][:, None] + logA, axis=0) + logB[t]
        out[t] = la - logsumexp(la)
    return np.exp(out)

def episodes(flag, index, min_len=3):
    """1 が min_len か月以上続いた区間（始まり, 終わり）"""
    eps, start = [], None
    v = np.asarray(flag)
    for i, f in enumerate(v):
        if f and start is None:
            start = i
        if (not f or i == len(v) - 1) and start is not None:
            end = i if f else i - 1
            if end - start + 1 >= min_len:
                eps.append((index[start], index[end]))
            start = None
    return eps

def dated_flag(prob, index, min_len=3):
    flag = pd.Series(0, index=index)
    for s, e in episodes(prob > 0.5, index, min_len):
        flag[s:e] = 1
    return flag

def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)

def evaluate(flag, rec, cyc, start=None):
    """公式の景気基準日付との一致"""
    f = flag.copy(); r = rec.reindex(f.index)
    if start is not None:
        f = f[start:]; r = r[start:]
    acc = (f == r).mean()
    sens = f[r == 1].mean()
    spec = 1 - f[r == 0].mean()
    eps = episodes(f.values, f.index, 1)
    peaks = cyc[cyc.type == "peak"].month.tolist()
    troughs = cyc[cyc.type == "trough"].month.tolist()
    rows, used = [], set()
    for p in peaks:
        t = min([x for x in troughs if x > p])
        if p < f.index[0]:
            continue
        s0 = p + pd.DateOffset(months=1)
        match = [(i, e) for i, e in enumerate(eps)
                 if e[1] >= s0 - pd.DateOffset(months=6) and e[0] <= t + pd.DateOffset(months=6)]
        if match:
            for i, _ in match:
                used.add(i)
            es = min(e[0] for _, e in match); ee = max(e[1] for _, e in match)
            rows.append(dict(peak=p.strftime("%Y-%m"), trough=t.strftime("%Y-%m"),
                             est_start=es.strftime("%Y-%m"), est_end=ee.strftime("%Y-%m"),
                             gap_start=months_between(s0, es), gap_end=months_between(t, ee)))
        else:
            rows.append(dict(peak=p.strftime("%Y-%m"), trough=t.strftime("%Y-%m"),
                             est_start="", est_end="", gap_start=np.nan, gap_end=np.nan))
    false_eps = [(e[0].strftime("%Y-%m"), e[1].strftime("%Y-%m")) for i, e in enumerate(eps) if i not in used]
    tp = pd.DataFrame(rows)
    return dict(acc=acc, sens=sens, spec=spec, n_rec=len(tp),
                missed=int(tp.est_start.eq("").sum()), false=len(false_eps),
                false_list=";".join(f"{a}〜{b}" for a, b in false_eps),
                mae_start=float(np.nanmean(np.abs(tp.gap_start))) if tp.gap_start.notna().any() else np.nan,
                mae_end=float(np.nanmean(np.abs(tp.gap_end))) if tp.gap_end.notna().any() else np.nan), tp
