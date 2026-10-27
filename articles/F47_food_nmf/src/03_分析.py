"""NMF で「品目×都市」の表を分解する。
X（都市×品目）＝ 全国比（全国=1）を、都市ごとの平均で割ったもの（都市全体の支出の多さをそろえる）。
X ≈ W H、W：都市ごとの「パターンの重み」、H：パターンごとの品目の重み（どちらも0以上）。"""
import json
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.decomposition import NMF, PCA
from common import DATA, RES, SEED, CITIES, CITY_REGION

K_MAIN = 6
N_INIT = 20


def load(tag="2023_2025", other=False, level=True):
    r = pd.read_csv(DATA / f"ratio_{tag}.csv", index_col=0, encoding="utf-8-sig")
    if not other:
        r = r[~r.index.str.startswith("他の")]
    X = r[CITIES].T
    if level:
        X = X.div(X.mean(axis=1), axis=0)
    return X, r["分類"]


def fit(X, k, seed=SEED, init="nndsvda"):
    m = NMF(k, init=init, max_iter=5000, tol=1e-6, random_state=seed)
    W = m.fit_transform(X.values)
    H = m.components_
    # 尺度をそろえる：H の各行の平均を1に（その分を W に）
    s = H.mean(axis=1)
    return W * s, H / s[:, None]


def rel_err(X, W, H):
    v = X.values
    return float(np.linalg.norm(v - W @ H) / np.linalg.norm(v - v.mean(axis=0)))


def cos_match(H1, H2):
    """H の行どうしのコサイン類似度で、パターンを1対1に対応させる（ハンガリー法）"""
    a = H1 / np.linalg.norm(H1, axis=1, keepdims=True)
    b = H2 / np.linalg.norm(H2, axis=1, keepdims=True)
    C = a @ b.T
    i, j = linear_sum_assignment(-C)
    return C[i, j], j


def top_items(H, cols, n=8):
    """パターンらしさ＝その品目の重みのうち、このパターンが占める割合（品目全体の重み平均以上の品目に限る）"""
    Hd = pd.DataFrame(H, columns=cols)
    share = Hd / Hd.sum(axis=0)
    out = []
    for i in range(len(Hd)):
        cand = share.iloc[i][Hd.iloc[i] >= 1.0]
        out.append(list(cand.sort_values(ascending=False).head(n).index))
    return out


if __name__ == "__main__":
    X, grp = load()
    res = {"n_cities": X.shape[0], "n_items": X.shape[1]}

    # 1) 因子の数を変えたときの誤差と安定性（初期値を20通り）
    rows = []
    for k in range(2, 11):
        Wb, Hb = fit(X, k)
        errs, sims = [], []
        for s in range(N_INIT):
            W, H = fit(X, k, seed=s, init="random")
            errs.append(rel_err(X, W, H))
            c, _ = cos_match(Hb, H)
            sims.append(c.mean())
        rows.append(dict(k=k, err_nndsvda=rel_err(X, Wb, Hb), err_random_med=float(np.median(errs)),
                         stab_mean_cos=float(np.mean(sims)), stab_min_cos=float(np.min(sims))))
    ks = pd.DataFrame(rows)
    ks.to_csv(RES / "k_selection.csv", index=False)
    print(ks.round(3))

    # 2) 本体（k=6）
    W, H = fit(X, K_MAIN)
    res["k"] = K_MAIN
    res["rel_err"] = rel_err(X, W, H)
    Hd = pd.DataFrame(H, index=[f"P{i+1}" for i in range(K_MAIN)], columns=X.columns)
    Hd.T.assign(分類=grp.loc[X.columns].values).to_csv(RES / "H_item_weights.csv", encoding="utf-8-sig")
    tops = top_items(H, X.columns, 10)
    Wd = pd.DataFrame(W, index=X.index, columns=Hd.index)
    share = Wd.div(Wd.sum(axis=1), axis=0)
    share.insert(0, "地方", [CITY_REGION[c] for c in share.index])
    share["主なパターン"] = Wd.idxmax(axis=1)
    share.to_csv(RES / "W_city_share.csv", encoding="utf-8-sig")
    pats = []
    for i, p in enumerate(Hd.index):
        cities = share[p].sort_values(ascending=False).head(8)
        pats.append(dict(pattern=p, top_items=tops[i], top_cities=list(cities.index),
                         top_city_share=[round(float(v), 3) for v in cities.values],
                         n_dominant=int((share["主なパターン"] == p).sum())))
    res["patterns"] = pats
    for q in pats:
        print(q["pattern"], q["n_dominant"], "|", " ".join(q["top_items"]), "||", " ".join(q["top_cities"]))

    # 地方ごとの平均の構成
    reg = share.groupby("地方", sort=False)[list(Hd.index)].mean()
    reg.to_csv(RES / "region_share.csv", encoding="utf-8-sig")

    # 3) 安定性：初期値を20通りにして本体と対応させたときの類似度（パターンごと）
    stab = []
    for s in range(N_INIT):
        W2, H2 = fit(X, K_MAIN, seed=s, init="random")
        c, j = cos_match(H, H2)
        share2 = pd.DataFrame(W2[:, j], index=X.index)
        share2 = share2.div(share2.sum(axis=1), axis=0)
        same_dom = float((share2.values.argmax(axis=1) == Wd.values.argmax(axis=1)).mean())
        stab.append(dict(seed=s, **{f"cos_P{i+1}": float(c[i]) for i in range(K_MAIN)},
                         err=rel_err(X, W2, H2), same_dominant=same_dom))
    st = pd.DataFrame(stab)
    st.to_csv(RES / "stability_seeds.csv", index=False)
    res["stability"] = {f"P{i+1}": dict(min=float(st[f'cos_P{i+1}'].min()), median=float(st[f'cos_P{i+1}'].median()))
                        for i in range(K_MAIN)}
    res["stability_same_dominant_median"] = float(st.same_dominant.median())
    res["stability_same_dominant_min"] = float(st.same_dominant.min())

    # 4) 頑健性
    rob = []
    def compare(name, Xr, k=K_MAIN, base_items=None):
        W2, H2 = fit(Xr, k)
        common = [c for c in X.columns if c in Xr.columns]
        Hb = Hd[common].values
        H2d = pd.DataFrame(H2, columns=Xr.columns)[common].values
        if k == K_MAIN:
            c, j = cos_match(Hb, H2d)
            s2 = pd.DataFrame(W2[:, j], index=Xr.index)
            s2 = s2.div(s2.sum(axis=1), axis=0)
            corr = [float(np.corrcoef(share[f"P{i+1}"].loc[s2.index], s2[i])[0, 1]) for i in range(K_MAIN)]
            same = float((s2.values.argmax(axis=1) == Wd.loc[s2.index].values.argmax(axis=1)).mean())
            rob.append(dict(name=name, k=k, n_items=Xr.shape[1], err=rel_err(Xr, W2, H2),
                            cos_min=float(c.min()), cos_med=float(np.median(c)),
                            city_corr_min=min(corr), city_corr_med=float(np.median(corr)), same_dominant=same))
        else:
            a = Hb / np.linalg.norm(Hb, axis=1, keepdims=True)
            b = H2d / np.linalg.norm(H2d, axis=1, keepdims=True)
            best = (a @ b.T).max(axis=1)  # 本体の各パターンに最も近い相手
            rob.append(dict(name=name, k=k, n_items=Xr.shape[1], err=rel_err(Xr, W2, H2),
                            cos_min=float(best.min()), cos_med=float(np.median(best))))
    compare("因子5", X, 5)
    compare("因子7", X, 7)
    compare("因子8", X, 8)
    Xo, _ = load(other=True)
    compare("「他の〜」も含める", Xo)
    Xl, _ = load(level=False)
    compare("都市の支出水準をそろえない", Xl)
    X0, _ = load("2013_2015")
    X0 = X0[[c for c in X.columns if c in X0.columns]]
    compare("10年前（2013〜15年平均）", X0)
    rb = pd.DataFrame(rob)
    rb.to_csv(RES / "robustness.csv", index=False)
    print(rb.round(3))
    res["robustness"] = rob

    # 10年前との都市の構成の変化（本体の H を固定して、10年前の X の W を非負最小二乗で求める）
    from scipy.optimize import nnls
    Hc = Hd[X0.columns].values
    W0 = np.array([nnls(Hc.T, X0.loc[c].values)[0] for c in X.index])
    s0 = pd.DataFrame(W0, index=X.index, columns=Hd.index)
    s0 = s0.div(s0.sum(axis=1), axis=0)
    chg = (share[list(Hd.index)] - s0)
    chg.to_csv(RES / "share_change_vs_2013_15.csv", encoding="utf-8-sig")
    res["change_10y"] = {p: dict(mean_abs=float(chg[p].abs().mean()), corr=float(np.corrcoef(share[p], s0[p])[0, 1]))
                         for p in Hd.index}
    res["same_dominant_10y"] = float((s0.values.argmax(axis=1) == Wd.values.argmax(axis=1)).mean())

    # 5) PCA との比較（標準化した X）
    Z = (X - X.mean()) / X.std()
    pca = PCA(K_MAIN, random_state=SEED).fit(Z)
    res["pca_evr"] = [float(v) for v in pca.explained_variance_ratio_]
    L = pd.DataFrame(pca.components_, columns=X.columns, index=[f"PC{i+1}" for i in range(K_MAIN)])
    L.T.to_csv(RES / "pca_loadings.csv", encoding="utf-8-sig")
    sc = pd.DataFrame(pca.transform(Z), index=X.index, columns=L.index)
    sc.to_csv(RES / "pca_scores.csv", encoding="utf-8-sig")
    # PC のスコアと NMF の構成の相関
    cc = pd.DataFrame([[float(np.corrcoef(sc[pc], share[p])[0, 1]) for p in Hd.index] for pc in L.index],
                      index=L.index, columns=Hd.index)
    cc.to_csv(RES / "pca_vs_nmf_corr.csv", encoding="utf-8-sig")
    res["pca_top"] = {pc: dict(pos=list(L.loc[pc].sort_values(ascending=False).head(6).index),
                               neg=list(L.loc[pc].sort_values().head(6).index)) for pc in L.index[:3]}
    json.dump(res, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: res[k] for k in ["rel_err", "stability", "stability_same_dominant_median",
                                           "stability_same_dominant_min", "change_10y", "same_dominant_10y", "pca_evr"]},
                     ensure_ascii=False, indent=0))
    print(cc.round(2))
