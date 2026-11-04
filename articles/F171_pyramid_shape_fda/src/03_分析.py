"""03 分析：人口ピラミッドの「形」を関数データとして扱い、関数主成分（FPCA）とクラスタリングで型に分ける。

手順
1. 市区町村ごとに、年齢 a（0〜94歳）の人口割合 p(a)（合計1）を作る
2. 2階差分の罰則つき平滑化（Whittaker 平滑化、λ=10）で、小さな町村の1歳ごとのでこぼこをならす
3. 平滑化した曲線の主成分（等間隔の格子なので、ふつうの主成分分析が関数主成分にあたる）
4. 主成分得点（累積寄与95%まで）を k-means で k=2〜10 に分け、シルエット・GMM の BIC・
   復元抽出での安定性（ARI）を比べて「いくつの型か」を判断する
5. 頑健性：λ／年齢の範囲／年（2015年）／男女別／人口の小さい町村を除く／都道府県単位

乱数の種はすべて 171。
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
SEED = 171
CODE_15_TO_20 = {"04423": "04216", "40305": "40231"}  # 町→市で番号が変わった2つ

units = pd.read_csv(DATA / "units.csv", dtype={"code": str}).set_index("code")


def load(year, sex, pref=False):
    f = DATA / (f"pref_counts_{year}_{sex}.csv" if pref else f"counts_{year}_{sex}.csv")
    m = pd.read_csv(f, dtype={"code": str}).set_index("code")
    m.columns = m.columns.astype(int)
    if year == 2015 and not pref:
        m = m.rename(index=CODE_15_TO_20)
    return m


def whittaker(Y, lam):
    """各行を2階差分の罰則で平滑化（lam=0 はそのまま）。"""
    if lam == 0:
        return Y.copy()
    n = Y.shape[1]
    D = np.diff(np.eye(n), 2, axis=0)
    A = np.eye(n) + lam * D.T @ D
    return np.linalg.solve(A, Y.T).T


def curves(counts, amax=94, lam=10.0):
    X = counts.loc[:, 0:amax].to_numpy(float)
    X = X / X.sum(1, keepdims=True)
    S = whittaker(X, lam)
    S = np.clip(S, 0, None)
    S = S / S.sum(1, keepdims=True)
    return S


def fpca(S, var=0.95):
    mu = S.mean(0)
    U, s, Vt = np.linalg.svd(S - mu, full_matrices=False)
    ev = s ** 2 / (len(S) - 1)
    ratio = ev / ev.sum()
    q = int(np.searchsorted(np.cumsum(ratio), var) + 1)
    scores = (S - mu) @ Vt[:q].T
    return mu, Vt, ratio, scores, q


def km(Z, k):
    return KMeans(k, n_init=20, random_state=SEED).fit(Z)


def choose_k(Z, ks=range(2, 11), nboot=50):
    rng = np.random.default_rng(SEED)
    rows = []
    for k in ks:
        lab = km(Z, k).labels_
        sil = silhouette_score(Z, lab)
        bic = GaussianMixture(k, covariance_type="full", random_state=SEED, n_init=3).fit(Z).bic(Z)
        aris = []
        for _ in range(nboot):
            idx = rng.choice(len(Z), len(Z), replace=True)
            lb = KMeans(k, n_init=5, random_state=int(rng.integers(1e9))).fit(Z[idx]).predict(Z)
            aris.append(adjusted_rand_score(lab, lb))
        rows.append(dict(k=k, silhouette=sil, gmm_bic=bic, boot_ari_mean=np.mean(aris),
                         boot_ari_p10=np.percentile(aris, 10)))
    return pd.DataFrame(rows)


def main():
    out = {}
    pop = units["pop2020"]
    keep = pop[pop > 0].index  # 2020年に人口0の町を除く
    c20 = load(2020, 0).loc[keep]
    S = curves(c20)
    mu, Vt, ratio, Z, q = fpca(S)
    out["n_units"] = int(len(S))
    out["n_dropped_zero_pop"] = int((pop <= 0).sum())
    out["fpc_ratio"] = [float(r) for r in ratio[:6]]
    out["q_95"] = q

    kt = choose_k(Z)
    kt.to_csv(RES / "choose_k.csv", index=False)
    print(kt.round(3).to_string())

    # 主な k（シルエットとBIC、安定性で決める。後で上書きできるように results に残す）
    K = int(kt.loc[kt.silhouette.idxmax(), "k"])
    out["k_silhouette"] = K
    out["k_bic"] = int(kt.loc[kt.gmm_bic.idxmin(), "k"])
    stable = kt[kt.boot_ari_p10 >= 0.8]
    out["k_stable_max"] = int(stable.k.max()) if len(stable) else None

    pd.DataFrame(Z[:, :4], index=keep, columns=[f"fpc{i+1}" for i in range(4)]).to_csv(RES / "fpc_scores.csv")
    comp = pd.DataFrame(Vt[:4].T, columns=[f"phi{i+1}" for i in range(4)])
    comp.insert(0, "age", np.arange(S.shape[1]))
    comp["mean"] = mu
    comp.to_csv(RES / "fpc_components.csv", index=False)
    json.dump(out, open(RES / "_stage1.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))




# ---------------------------------------------------------------- 第2段：型の中身と頑健性
def features(counts):
    X = counts.loc[:, 0:100].to_numpy(float)
    tot = X.sum(1)
    age = np.arange(101)
    f = pd.DataFrame(index=counts.index)
    f["pop"] = tot
    f["mean_age"] = (X * age).sum(1) / tot
    cum = np.cumsum(X, 1) / tot[:, None]
    f["median_age"] = (cum < 0.5).sum(1)
    f["sh0_14"] = X[:, 0:15].sum(1) / tot
    f["sh15_64"] = X[:, 15:65].sum(1) / tot
    f["sh65"] = X[:, 65:].sum(1) / tot
    f["sh20_29"] = X[:, 20:30].sum(1) / tot
    f["r2029_1019"] = X[:, 20:30].sum(1) / np.maximum(X[:, 10:20].sum(1), 1)
    f["r0004_3034"] = X[:, 0:5].sum(1) / np.maximum(X[:, 30:35].sum(1), 1)
    return f


def match_labels(ref, lab, k):
    """lab の番号を ref にいちばん重なるよう付け替える（ハンガリー法）。"""
    from scipy.optimize import linear_sum_assignment
    C = pd.crosstab(lab, ref).reindex(index=range(k), columns=range(k), fill_value=0).to_numpy()
    r, c = linear_sum_assignment(-C)
    mp = dict(zip(r, c))
    return np.array([mp[x] for x in lab])


def order_by_mean_age(lab, fe):
    o = pd.Series(fe["mean_age"].to_numpy()).groupby(lab).mean().sort_values().index
    mp = {old: new for new, old in enumerate(o)}
    return np.array([mp[x] for x in lab])


def pipeline(counts, amax=94, lam=10.0, k=3):
    S = curves(counts, amax, lam)
    mu, Vt, ratio, Z, q = fpca(S)
    lab = km(Z, k).labels_
    return S, Z, lab, ratio


def stage2():
    out = json.load(open(RES / "_stage1.json"))
    pop = units["pop2020"]
    keep = pop[pop > 0].index
    c20 = load(2020, 0).loc[keep]
    fe = features(c20)
    S, Z, _, ratio = pipeline(c20)
    corr = pd.DataFrame({f"fpc{j+1}": [np.corrcoef(Z[:, j], fe[c])[0, 1] for c in fe.columns[1:]] for j in range(4)},
                        index=fe.columns[1:])
    corr["log_pop"] = np.nan
    for j in range(4):
        corr.loc["log_pop", f"fpc{j+1}"] = np.corrcoef(Z[:, j], np.log(fe["pop"]))[0, 1]
    corr = corr.drop(columns="log_pop")
    corr.to_csv(RES / "fpc_feature_corr.csv")

    summ, labs = [], {}
    for k in (2, 3, 5):
        lab = order_by_mean_age(km(Z, k).labels_, fe)
        labs[k] = lab
        g = fe.assign(type=lab + 1).groupby("type")
        t = g.agg(n=("pop", "size"), pop_total=("pop", "sum"), pop_median=("pop", "median"),
                  mean_age=("mean_age", "median"), sh0_14=("sh0_14", "median"), sh65=("sh65", "median"),
                  sh20_29=("sh20_29", "median"), r2029_1019=("r2029_1019", "median"),
                  r0004_3034=("r0004_3034", "median"))
        t["pop_share"] = t.pop_total / t.pop_total.sum()
        t.insert(0, "k", k)
        summ.append(t.reset_index())
        mc = pd.DataFrame({f"type{i+1}": S[lab == i].mean(0) for i in range(k)})
        mc.insert(0, "age", np.arange(S.shape[1]))
        mc.to_csv(RES / f"type_mean_curves_k{k}.csv", index=False)
    summ = pd.concat(summ)
    summ.to_csv(RES / "type_summary.csv", index=False)
    lab_df = pd.DataFrame({f"type_k{k}": labs[k] + 1 for k in labs}, index=keep)
    lab_df.join(units[["name", "pref"]]).join(fe[["pop", "mean_age"]]).to_csv(RES / "types_by_unit.csv")

    # 型の間に「谷」があるか：主成分得点の境目付近にいる市区町村の割合（k=2）
    from sklearn.metrics import silhouette_samples
    for k in (2, 3, 5):
        ss = silhouette_samples(Z, labs[k])
        out[f"k{k}_sil_lt0.1_share"] = float((ss < 0.1).mean())
    # 1本目の主成分の分布が「山2つ」か：1次元 GMM の BIC
    x = Z[:, :1]
    out["fpc1_gmm_bic_1_2_3"] = [float(GaussianMixture(m, random_state=SEED, n_init=3).fit(x).bic(x)) for m in (1, 2, 3)]

    # 1本目の主成分（平均年齢の軸）を除いた残りだけで分けると、まとまりはあるか
    R = Z[:, 1:]
    out["resid_silhouette_k2_6"] = [float(silhouette_score(R, km(R, k).labels_)) for k in range(2, 7)]
    out["n_r2029_1019_gt1.5"] = int((fe["r2029_1019"] > 1.5).sum())

    # ---- 頑健性：主の分け方との ARI
    rows = []
    def add(name, lab_alt, idx, k):
        ref = pd.Series(labs[k], index=keep).loc[idx].to_numpy()
        rows.append(dict(check=name, k=k, n=len(idx), ari=adjusted_rand_score(ref, lab_alt)))
    for k in (2, 3, 5):
        for lam in (0, 1, 100, 1000):
            _, _, l, _ = pipeline(c20, lam=lam, k=k)
            add(f"平滑化 λ={lam}", l, keep, k)
        for amax in (84, 99):
            _, _, l, _ = pipeline(c20, amax=amax, k=k)
            add(f"年齢 0〜{amax}歳", l, keep, k)
        for sx, nm in ((1, "男性だけ"), (2, "女性だけ")):
            _, _, l, _ = pipeline(load(2020, sx).loc[keep], k=k)
            add(nm, l, keep, k)
        for th in (1000, 5000):
            idx = fe.index[fe["pop"] >= th]
            _, _, l, _ = pipeline(c20.loc[idx], k=k)
            add(f"人口{th:,}人以上だけ", l, idx, k)
        Zw = Z
        l = AgglomerativeClustering(k, linkage="ward").fit(Zw).labels_
        add("ウォード法（階層）", l, keep, k)
        l = GaussianMixture(k, random_state=SEED, n_init=3).fit(Zw).predict(Zw)
        add("混合正規分布", l, keep, k)
        c15 = load(2015, 0)
        idx = keep.intersection(c15.index[c15.sum(1) > 0])
        _, _, l, _ = pipeline(c15.loc[idx], k=k)
        add("2015年（同じ手順で分け直し）", l, idx, k)
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness_ari.csv", index=False)
    print(rob.pivot_table(index="check", columns="k", values="ari").round(2).to_string())

    # ---- 2015年→2020年：2020年の軸と中心で2015年を分類し、型の移り変わりを数える
    c15 = load(2015, 0)
    idx = keep.intersection(c15.index[c15.sum(1) > 0])
    S20 = curves(c20)
    mu, Vt, _, Z20, q = fpca(S20)
    S15 = curves(c15.loc[idx])
    Z15 = (S15 - mu) @ Vt[:q].T
    trans = {}
    for k in (2, 3):
        m = km(Z20, k)
        l20 = order_by_mean_age(m.labels_, fe)
        perm = {old: new for old, new in zip(m.labels_, l20)}
        l15 = np.array([perm[x] for x in m.predict(Z15)])
        l20s = pd.Series(l20, index=keep).loc[idx].to_numpy()
        ct = pd.crosstab(pd.Series(l15 + 1, name="2015"), pd.Series(l20s + 1, name="2020"))
        ct.to_csv(RES / f"transition_2015_2020_k{k}.csv")
        trans[k] = ct
        out[f"k{k}_moved_share"] = float((l15 != l20s).mean())
        out[f"k{k}_2015_counts"] = [int(x) for x in np.bincount(l15, minlength=k)]
        out[f"k{k}_2020_counts"] = [int(x) for x in np.bincount(l20s, minlength=k)]
    # 2015→2020 の1本目の主成分得点の動き
    out["fpc1_shift_median"] = float(np.median(Z20[[keep.get_loc(c) for c in idx], 0] - Z15[:, 0]))
    out["fpc1_sd_2020"] = float(Z20[:, 0].std())

    # ---- 都道府県（代替案）
    pc = load(2020, 0, pref=True)
    Sp = curves(pc)
    _, _, rp, Zp, qp = fpca(Sp)
    ktp = choose_k(Zp, ks=range(2, 8), nboot=50)
    ktp.to_csv(RES / "choose_k_pref.csv", index=False)
    out["pref_fpc_ratio"] = [float(r) for r in rp[:3]]
    out["pref_k_silhouette"] = int(ktp.loc[ktp.silhouette.idxmax(), "k"])
    print(ktp.round(3).to_string())
    json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))
    print(summ.round(3).to_string())
    print(corr.round(2).to_string())
    for k in trans:
        print(trans[k])


if __name__ == "__main__":
    import sys
    if "--stage2" not in sys.argv:
        main()
    stage2()
