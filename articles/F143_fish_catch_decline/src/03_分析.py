"""03 分析: 魚種別の漁獲量の「減り方の型」を時系列クラスタリングで分け、変化点を探す
入力 : data/species_wide.csv, data/gear_wide.csv
出力 : results/*.csv, results/results.json
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
SEED = 0
rng = np.random.default_rng(SEED)

W = pd.read_csv(ROOT / "data/species_wide.csv", index_col=0)
G = pd.read_csv(ROOT / "data/gear_wide.csv", index_col=0)
Y0, Y1 = 1960, 2024
EXCL = ["海産ほ乳類"]
full = [c for c in W.columns if c != "漁獲量計" and c not in EXCL and W.loc[Y0:Y1, c].notna().all()]
peak = W.loc[Y0:Y1, full].max()
SP = [c for c in full if peak[c] >= 10000]           # 主な分析の対象（期間中の最大が1万t以上）
TOP20 = list(peak[SP].sort_values(ascending=False).index[:20])
X = W.loc[Y0:Y1, SP]


def shape_peak(df, win=5):
    """5年の中心移動平均をとり、各魚種の最大を1とした形"""
    sm = df.rolling(win, center=True, min_periods=min(3, win)).mean()
    return (sm / sm.max()).T


def shape_zlog(df):
    lg = np.log(df.clip(lower=1))
    return ((lg - lg.mean()) / lg.std()).T


def kmeans(Z, k, seed=SEED):
    return KMeans(k, n_init=50, random_state=seed).fit_predict(Z.values)


Z = shape_peak(X)
sil = {k: float(silhouette_score(Z.values, kmeans(Z, k))) for k in range(2, 8)}
K = max(range(3, 7), key=lambda k: sil[k])           # 解釈できる3〜6の中でシルエット最大
lab = kmeans(Z, K)

# クラスタに名前をつけるための特徴：最大の年（中央値）と、直近5年÷最大
peak_year = X.rolling(5, center=True, min_periods=3).mean().idxmax()
recent_ratio = X.loc[2020:2024].mean() / X.rolling(5, center=True, min_periods=3).mean().max()
info = pd.DataFrame({"cluster": lab, "peak_year": peak_year, "recent_ratio": recent_ratio, "peak_t": peak[SP]}, index=SP)
order = info.groupby("cluster").peak_year.median().sort_values().index.tolist()
remap = {old: new for new, old in enumerate(order)}
info["cluster"] = info.cluster.map(remap)
lab = info.cluster.values

# ---------- 変化点（log 漁獲量の区分線形回帰、0〜3か所、BIC で選ぶ） ----------
yrs = np.arange(Y0, Y1 + 1)


def seg_rss_table(y, t):
    """全ての区間 [a,b) の直線当てはめの残差平方和を前計算する（閉じた式）"""
    n = len(y)
    R = np.full((n + 1, n + 1), np.inf)
    S = np.full((n + 1, n + 1), np.nan)
    for a in range(n):
        for b in range(a + 2, n + 1):
            tt, yy = t[a:b], y[a:b]
            tc = tt - tt.mean()
            sl = (tc * (yy - yy.mean())).sum() / (tc ** 2).sum()
            R[a, b] = ((yy - yy.mean() - sl * tc) ** 2).sum()
            S[a, b] = sl
    return R, S


def changepoints(y, maxm=3, minseg=8, t=None):
    """区分線形（各区間で切片と傾き）、変化点 0〜maxm 個、区間は minseg 年以上、BIC で選ぶ（動的計画法）"""
    t = yrs if t is None else t
    n = len(y)
    R, S = seg_rss_table(y, t)
    best = None
    # F[m][b] = 先頭から b までを m+1 区間に分けたときの最小 RSS
    F = [dict() for _ in range(maxm + 1)]
    for b in range(minseg, n + 1):
        F[0][b] = (R[0, b], [])
    for m in range(1, maxm + 1):
        for b in range((m + 1) * minseg, n + 1):
            cand = [(F[m - 1][a][0] + R[a, b], F[m - 1][a][1] + [a]) for a in range(m * minseg, b - minseg + 1) if a in F[m - 1]]
            if cand:
                F[m][b] = min(cand, key=lambda x: x[0])
    for m in range(maxm + 1):
        if n not in F[m]:
            continue
        rss, brks = F[m][n]
        p = 2 * (m + 1) + m
        bic = n * np.log(max(rss, 1e-12) / n) + p * np.log(n)
        if best is None or bic < best[0]:
            edges = [0] + brks + [n]
            sl = [float(S[a, b]) for a, b in zip(edges[:-1], edges[1:])]
            best = (bic, brks, sl)
    _, brks, sl = best
    return [int(t[b]) for b in brks], sl


cp_rows = []
for s in SP:
    y = np.log(X[s].clip(lower=1).values)
    b, sl = changepoints(y)
    b5, _ = changepoints(y, minseg=5)
    b10, _ = changepoints(y, minseg=10)
    cp_rows.append({"species": s, "cluster": int(info.loc[s, "cluster"]), "breaks": b,
                    "last_slope_pct": 100 * (np.exp(sl[-1]) - 1),
                    "breaks_min5": b5, "breaks_min10": b10})
cp = pd.DataFrame(cp_rows).set_index("species")
info = info.join(cp[["breaks", "last_slope_pct", "breaks_min5", "breaks_min10"]])

# 全体（漁獲量計）の変化点
yt = np.log(W.loc[Y0:Y1, "漁獲量計"].values)
tot_b, tot_sl = changepoints(yt)

# ---------- 型ごとの寄与：全体の最大の年から2024年までの減少 ----------
tot = W.loc[Y0:Y1, "漁獲量計"]
ty = int(tot.idxmax())
dec = {}
for c in range(K):
    mem = info.index[info.cluster == c]
    dec[c] = float(X.loc[ty, mem].sum() - X.loc[Y1, mem].sum())
dec["対象外の魚種など"] = float((tot[ty] - tot[Y1]) - sum(dec.values()))
cl_tot = pd.DataFrame({c: X[info.index[info.cluster == c]].sum(axis=1) for c in range(K)})
cl_tot["対象外の魚種など"] = tot - cl_tot.sum(axis=1)
cl_tot.to_csv(RES / "cluster_totals_by_year.csv")

# ---------- 頑健性 ----------
rob = {}
rob["k"] = {k: float(adjusted_rand_score(lab, kmeans(Z, k))) for k in range(2, 8)}
for (a, b) in [(1970, 2024), (1990, 2024), (1960, 2000)]:
    Za = shape_peak(W.loc[a:b, SP])
    rob[f"period_{a}_{b}"] = float(adjusted_rand_score(lab, kmeans(Za, K)))
Zz = shape_zlog(X)
rob["zscore_log"] = float(adjusted_rand_score(lab, kmeans(Zz, K)))
rob["no_smoothing"] = float(adjusted_rand_score(lab, kmeans(shape_peak(X, win=1), K)))
rob["ward"] = float(adjusted_rand_score(lab, AgglomerativeClustering(K, linkage="ward").fit_predict(Z.values)))
idx20 = [SP.index(s) for s in TOP20]
lab20 = kmeans(Z.loc[TOP20], K)
rob["top20"] = float(adjusted_rand_score(lab[idx20], lab20))
# 年の80%をランダムに使って何度も分け直す
aris = []
for i in range(200):
    cols = np.sort(rng.choice(Z.shape[1], int(Z.shape[1] * .8), replace=False))
    aris.append(adjusted_rand_score(lab, KMeans(K, n_init=10, random_state=i).fit_predict(Z.values[:, cols])))
rob["subsample_years_mean"] = float(np.mean(aris))
rob["subsample_years_p05"] = float(np.percentile(aris, 5))
# 魚種ごとに「同じ型に入る割合」（ブートストラップの共起）
co = np.zeros((len(SP), len(SP)))
for i in range(200):
    cols = np.sort(rng.choice(Z.shape[1], int(Z.shape[1] * .8), replace=False))
    l = KMeans(K, n_init=10, random_state=1000 + i).fit_predict(Z.values[:, cols])
    co += (l[:, None] == l[None, :])
co /= 200
stab = []
for j, s in enumerate(SP):
    same = lab == lab[j]
    same[j] = False
    stab.append(float(co[j, same].mean()) if same.any() else np.nan)
info["stability"] = stab

# 変化点の頑健性：最小の区間を5年・10年に変えたときに、最も近い変化点が±3年以内に残る割合
def near(b1, b2, tol=3):
    if not b1:
        return np.nan
    return np.mean([any(abs(x - y) <= tol for y in b2) for x in b1])
rob["cp_keep_min5"] = float(np.nanmean([near(r.breaks, r.breaks_min5) for r in info.itertuples()]))
rob["cp_keep_min10"] = float(np.nanmean([near(r.breaks, r.breaks_min10) for r in info.itertuples()]))

# ---------- 漁業種類で見た場合（1975〜2024年） ----------
GE = [c for c in G.columns if c not in ["漁獲量計", "中・小型まき網"]]
Gx = G.loc[1975:2024, GE]
Gz = shape_peak(Gx)
gk = 3
glab = kmeans(Gz, gk)
gpy = Gx.rolling(5, center=True, min_periods=3).mean().idxmax()
grr = Gx.loc[2020:2024].mean() / Gx.rolling(5, center=True, min_periods=3).mean().max()
gcp = {}
for c in GE:
    yy = np.log(Gx[c].clip(lower=1).values)
    b, sl = changepoints(yy, t=np.arange(1975, 2025))
    gcp[c] = {"breaks": b, "last_slope_pct": 100 * (np.exp(sl[-1]) - 1)}
ginfo = pd.DataFrame({"cluster": glab, "peak_year": gpy, "recent_ratio": grr,
                      "breaks": [gcp[c]["breaks"] for c in GE],
                      "last_slope_pct": [gcp[c]["last_slope_pct"] for c in GE]}, index=GE)
ginfo.to_csv(RES / "gear_types.csv")

# ---------- 書き出し ----------
info = info.sort_values(["cluster", "peak_year"])
info.to_csv(RES / "species_clusters.csv")
Z.T.to_csv(RES / "species_shapes.csv")
summ = info.groupby("cluster").agg(n=("peak_year", "size"), peak_year_median=("peak_year", "median"),
                                   recent_ratio_median=("recent_ratio", "median"),
                                   last_slope_median=("last_slope_pct", "median"),
                                   stability_mean=("stability", "mean"))
summ["members"] = info.groupby("cluster").apply(lambda d: "、".join(d.index))
summ.to_csv(RES / "cluster_summary.csv")
allb = [b for bs in info.breaks for b in bs]
R = {
    "n_species": len(SP), "period": [Y0, Y1], "K": K, "silhouette": sil,
    "total_peak_year": ty, "total_peak_t": float(tot[ty]), "total_2024_t": float(tot[Y1]),
    "total_breaks": tot_b, "total_slopes_pct": [100 * (np.exp(s) - 1) for s in tot_sl],
    "decline_by_cluster": {str(k): v for k, v in dec.items()},
    "cluster_summary": json.loads(summ.to_json(orient="index", force_ascii=False)),
    "n_species_with_break": int((info.breaks.str.len() > 0).sum()),
    "breaks_by_decade": pd.Series([b // 10 * 10 for b in allb]).value_counts().sort_index().to_dict(),
    "first_break_by_decade": pd.Series([bs[0] // 10 * 10 for bs in info.breaks if bs]).value_counts().sort_index().to_dict(),
    "robustness": rob, "top20": TOP20,
    "gear": json.loads(ginfo.to_json(orient="index", force_ascii=False)),
}
json.dump(R, open(RES / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=int)
pd.set_option("display.width", 250)
print("K", K, sil)
print(summ.drop(columns="members").round(2))
for c, m in summ.members.items():
    print(c, m)
print("total peak", ty, tot[ty], "->", tot[Y1], "breaks", tot_b, [round(x, 1) for x in R["total_slopes_pct"]])
print("decline", {k: round(v / 1e4) for k, v in dec.items()})
print(json.dumps(rob, ensure_ascii=False, indent=0))
print(info[["cluster", "peak_year", "recent_ratio", "breaks", "last_slope_pct", "stability"]].round(2).to_string())
print(R["breaks_by_decade"], R["first_break_by_decade"])
print(ginfo.round(2).to_string())
