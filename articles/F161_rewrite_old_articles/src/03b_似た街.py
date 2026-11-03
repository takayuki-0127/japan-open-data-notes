"""03b 元記事 019「1,740市区町村を似た街に分けてみた（k-means・k=5）」を今の手順で作り直す。
元の手順：k-means を全データで1回、乱数の種を変えた ARI。今の手順：①ブートストラップで標本を替えたときの安定性（グループごとの Jaccard）
②k の選び方（シルエット・ギャップ統計・安定性）③別の手法（Ward・混合正規）④前処理を変える ⑤都道府県で半分に分けて当てる。"""
from common import *
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, adjusted_rand_score

d = load_extra()
d["foreign_log"] = np.log(d.A1700 / d.A1101 * 100 + 0.1)
d["daynight_log"] = np.log(d.A6107 / d.A1101)
d["child"] = d.A1405 / d.A1101
COLS = ["log_inc", "old", "child", "univ", "log_density", "mfg", "primary", "single", "foreign_log", "daynight_log"]
def prep(df, how="clip"):
    Z = df[COLS]
    if how == "clip": Z = Z.apply(lambda s: s.clip(s.quantile(.01), s.quantile(.99)))
    if how == "rank": Z = Z.rank(pct=True)
    return StandardScaler().fit_transform(Z)
X = prep(d)
K = 5
base = KMeans(K, n_init=50, random_state=0).fit(X); lab0 = base.labels_
orig = pd.read_csv(ORIG / "019_c1_assignments.csv")
names = orig.set_index("code").group.reindex(d.code).values
# 元の割り当てを再現できたか
ari_repro = adjusted_rand_score(names, lab0); print("ARI reproduce", ari_repro)
cl2name = pd.crosstab(lab0, names).idxmax(axis=1).to_dict()
GROUPS = ["大都市と近郊", "郊外・工業のある都市", "家族世帯が多い地方の市町", "高齢化が進んだ市町", "農林漁業の町村"]

def jaccard_match(lab_full, idx, lab_sub):
    """全データのグループごとに、部分標本のグループで一番近いものとの Jaccard（Hennig 2007）"""
    out = {}
    for c in range(K):
        A = set(idx[lab_full[idx] == c]); best = 0
        for c2 in np.unique(lab_sub):
            B = set(idx[lab_sub == c2]); best = max(best, len(A & B) / max(len(A | B), 1))
        out[c] = best
    return out

# 1) ブートストラップ（復元抽出200回）：全データの結果をどれだけ取り戻せるか
rng = np.random.default_rng(SEED); B = 200
jac, aris = [], []
for b in range(B):
    idx = np.unique(rng.choice(len(X), len(X), replace=True))
    lab = KMeans(K, n_init=10, random_state=b).fit_predict(X[idx])
    aris.append(adjusted_rand_score(lab0[idx], lab)); jac.append(jaccard_match(lab0, idx, lab))
jac = pd.DataFrame(jac).rename(columns=cl2name)
stab = pd.DataFrame({"jaccard_mean": jac.mean(), "jaccard_p10": jac.quantile(.1), "share_below_0.5": (jac < .5).mean(),
                     "n": pd.Series(names).value_counts()}).loc[GROUPS]
stab.round(3).to_csv(RES / "b_bootstrap_jaccard.csv", encoding="utf-8-sig"); print(stab.round(3)); print("boot ARI median", np.median(aris), np.percentile(aris, [10, 90]))

# 2) k の選び方：シルエット・ギャップ統計・ブートストラップの ARI（k=2〜9）
def gap(X, k, nref=10):
    w = KMeans(k, n_init=10, random_state=0).fit(X).inertia_
    lo, hi = X.min(0), X.max(0); r = np.random.default_rng(k)
    wr = [np.log(KMeans(k, n_init=5, random_state=0).fit(r.uniform(lo, hi, X.shape)).inertia_) for _ in range(nref)]
    return np.mean(wr) - np.log(w), np.std(wr) * np.sqrt(1 + 1 / nref)
ks = []
for k in range(2, 10):
    full_k = KMeans(k, n_init=20, random_state=0).fit_predict(X)
    rr = np.random.default_rng(SEED + k); a = []
    for b in range(50):
        idx = np.unique(rr.choice(len(X), len(X), replace=True))
        a.append(adjusted_rand_score(full_k[idx], KMeans(k, n_init=5, random_state=b).fit_predict(X[idx])))
    g, s = gap(X, k)
    ks.append({"k": k, "silhouette": silhouette_score(X, full_k), "gap": g, "gap_sd": s, "boot_ari_median": np.median(a), "boot_ari_p10": np.percentile(a, 10)})
ks = pd.DataFrame(ks)
# ギャップ統計の規則：gap(k) >= gap(k+1) - sd(k+1) を満たす最小の k
ok = [ks.k[i] for i in range(len(ks) - 1) if ks.gap[i] >= ks.gap[i + 1] - ks.gap_sd[i + 1]]
k_gap = ok[0] if ok else None
ks.round(3).to_csv(RES / "b_k_choice.csv", index=False); print(ks.round(3), "k_gap", k_gap)

# 3) 別の手法・4) 前処理を変える：元の5グループとの一致（ARI）
alts = {}
alts["k-means（元と同じ）"] = lab0
alts["Ward 法"] = AgglomerativeClustering(K, linkage="ward").fit_predict(X)
alts["混合正規分布"] = GaussianMixture(K, covariance_type="full", n_init=5, random_state=0).fit(X).predict(X)
alts["上下1%を丸めない"] = KMeans(K, n_init=50, random_state=0).fit_predict(prep(d, "none"))
alts["順位に変換"] = KMeans(K, n_init=50, random_state=0).fit_predict(prep(d, "rank"))
for drop in ["foreign_log", "daynight_log", "child"]:
    keep = [i for i, c in enumerate(COLS) if c != drop]
    alts[f"指標を1つ外す（{ {'foreign_log':'外国人','daynight_log':'昼夜間','child':'0〜5歳'}[drop]}）"] = KMeans(K, n_init=50, random_state=0).fit_predict(X[:, keep])
ar = []
for name, lab in alts.items():
    # 元のグループごとに、いちばん重なる相手との Jaccard
    jj = jaccard_match(lab0, np.arange(len(X)), lab)
    rec = {"variant": name, "ari_vs_original": adjusted_rand_score(lab0, lab)}
    for c, v in jj.items(): rec[cl2name[c]] = v
    ar.append(rec)
ar = pd.DataFrame(ar); ar.round(3).to_csv(RES / "b_alternatives.csv", index=False, encoding="utf-8-sig"); print(ar.round(3))

# 5) 都道府県で半分に分ける：奇数の県で作ったグループの中心で、偶数の県を割り当てる（と逆）
half = []
for s in range(20):
    rr = np.random.default_rng(SEED + 100 + s); prefs = d.pref_code.unique(); rr.shuffle(prefs)
    m = d.pref_code.isin(prefs[: len(prefs) // 2]).values
    km = KMeans(K, n_init=20, random_state=s).fit(X[m])
    half.append(adjusted_rand_score(lab0[~m], km.predict(X[~m])))
print("half ARI", np.median(half), np.min(half))

# 境目の町：いちばん近い中心と2番目に近い中心の距離の差が小さい町の割合
D = base.transform(X); Ds = np.sort(D, 1); margin = (Ds[:, 1] - Ds[:, 0]) / Ds[:, 1]
summ = {"ari_reproduce": ari_repro, "boot_ari_median": np.median(aris), "boot_ari_p10": np.percentile(aris, 10),
        "k_best_silhouette": int(ks.loc[ks.silhouette.idxmax(), "k"]), "k_gap": k_gap,
        "k_best_stability": int(ks.loc[ks.boot_ari_median.idxmax(), "k"]), "k5_boot_ari_median": ks.set_index("k").loc[5, "boot_ari_median"],
        "ward_ari": ar.set_index("variant").loc["Ward 法", "ari_vs_original"], "gmm_ari": ar.set_index("variant").loc["混合正規分布", "ari_vs_original"],
        "rank_ari": ar.set_index("variant").loc["順位に変換", "ari_vs_original"], "noclip_ari": ar.set_index("variant").loc["上下1%を丸めない", "ari_vs_original"],
        "alt_ari_min": ar.ari_vs_original[1:].min(), "alt_ari_max": ar.ari_vs_original[1:].max(),
        "half_ari_median": np.median(half), "half_ari_min": np.min(half), "share_margin_lt10": (margin < .10).mean(), "share_margin_lt5": (margin < .05).mean()}
for g in GROUPS:
    summ["jac_" + g] = stab.loc[g, "jaccard_mean"]; summ["altjac_min_" + g] = ar[g][1:].min(); summ["altjac_med_" + g] = ar[g][1:].median()
pd.Series(summ).to_csv(RES / "b_summary.csv", header=["value"], encoding="utf-8-sig"); print(pd.Series(summ))
pd.DataFrame({"code": d.code, "group": names, "margin": margin}).to_csv(RES / "b_margin.csv", index=False, encoding="utf-8-sig")
