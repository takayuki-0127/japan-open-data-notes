"""合成指標の作り方と重みで、47都道府県の順位がどれだけ動くかを調べる。

1. 基準：z得点・指標を等ウエイト・算術平均
2. 作り方の比較：分野を等ウエイト、主成分（第1主成分の負荷量、寄与率で重みづけした主成分）、
   最小最大の正規化、順位の正規化、幾何平均、データ包絡（Benefit of the Doubt）
3. 重みをでたらめに変える（ディリクレ分布、指標20個・分野6個、各10,000回）→ 各県の順位の幅
4. データ包絡：各県に一番有利な重みを選ばせると、何県が「1位タイ」になるか（重みの下限を変えて）
5. 頑健性：指標を10個だけ選ぶ（1,000回）、1つずつ外す、向きの決めにくい指標の向きを逆にする、
   2015年版（約10年前）の14指標、ディリクレの集中度
県の名前は結果の表に残すが、記事では名前を出さない（順位の良し悪しを言う記事ではないため）。
"""
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.stats import kendalltau, spearmanr
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
X = pd.read_csv(DATA / "indicators_main.csv", index_col=0)
X15 = pd.read_csv(DATA / "indicators_2015ed.csv", index_col=0)
meta = pd.read_csv(DATA / "indicator_meta.csv", index_col=0)
sign = meta["sign"].values.astype(float)
dom = meta["domain"].values
DOMS = list(dict.fromkeys(dom))
n, k = X.shape

def oriented(df, s):
    return df.values * s  # 大きいほど暮らしやすい向きにそろえる

def zscore(a):
    return (a - a.mean(0)) / a.std(0, ddof=0)

def minmax(a):
    return (a - a.min(0)) / (a.max(0) - a.min(0))

def rnorm(a):
    return (pd.DataFrame(a).rank(axis=0).values - 1) / (a.shape[0] - 1)

def ranks(score):
    # 1位が一番高い得点。同点は平均順位
    return pd.Series(-score).rank(method="average").values

A_ = oriented(X, sign)
Z = zscore(A_)
M = minmax(A_)
R = rnorm(A_)

w_eq = np.ones(k) / k
dom_w = np.array([1 / len(DOMS) / (dom == d).sum() for d in dom])

# 主成分
C = np.corrcoef(Z, rowvar=False)
ev, evec = np.linalg.eigh(C)
order = np.argsort(ev)[::-1]
ev, evec = ev[order], evec[:, order]
pc1 = evec[:, 0] * np.sign(evec[:, 0].sum())
w_pc1 = np.abs(pc1) / np.abs(pc1).sum()
share = ev / ev.sum()
m = int((ev > 1).sum())  # 固有値1超の主成分
scores_pc = Z @ evec[:, :m]
# 各主成分の向きは「指標の合計」と正の相関になるようにそろえる
for j in range(m):
    if np.corrcoef(scores_pc[:, j], Z.sum(1))[0, 1] < 0:
        scores_pc[:, j] *= -1
pc_weighted = scores_pc @ (share[:m] / share[:m].sum())

# 幾何平均（最小最大を 0.01〜1 に寄せてから）
G = 0.01 + 0.99 * M
geo = np.exp(np.log(G) @ w_eq)

# データ包絡（Benefit of the Doubt）：max sum w x_j  s.t. sum w x_k <= 1, w >= alpha * sum w
def bod(Mat, alpha=0.0):
    out = np.zeros(Mat.shape[0])
    kk = Mat.shape[1]
    for j in range(Mat.shape[0]):
        A_ub = [Mat[i] for i in range(Mat.shape[0])]
        b_ub = [1.0] * Mat.shape[0]
        for i in range(kk):  # alpha*sum(w) - w_i <= 0
            row = np.full(kk, alpha); row[i] -= 1
            A_ub.append(row); b_ub.append(0.0)
        res = linprog(-Mat[j], A_ub=np.array(A_ub), b_ub=np.array(b_ub), bounds=[(0, None)] * kk, method="highs")
        out[j] = -res.fun
    return out

Mb = 0.01 + 0.99 * M
bod_03 = bod(Mb, 0.03)
schemes = {
    "基準（z得点・指標等ウエイト・算術平均）": Z @ w_eq,
    "分野を等ウエイト": Z @ dom_w,
    "第1主成分の負荷量で重み": Z @ w_pc1,
    f"主成分{m}個を寄与率で重み": pc_weighted,
    "最小最大で正規化": M @ w_eq,
    "順位で正規化": R @ w_eq,
    "幾何平均（最小最大）": geo,
    "データ包絡（各指標の重み3%以上・各県に有利に）": bod_03,
}
rank_tab = pd.DataFrame({s: ranks(v) for s, v in schemes.items()}, index=X.index)
base = rank_tab.iloc[:, 0].values
sch_rows = []
for s in rank_tab.columns:
    r = rank_tab[s].values
    sch_rows.append({
        "作り方": s,
        "基準とのケンドールτ": round(kendalltau(base, r)[0], 3),
        "順位の差の絶対値の平均": round(np.abs(base - r).mean(), 2),
        "順位の差の最大": round(np.abs(base - r).max(), 1),
        "5位以上動く県": int((np.abs(base - r) >= 5).sum()),
        "10位以上動く県": int((np.abs(base - r) >= 10).sum()),
    })
sch = pd.DataFrame(sch_rows)
sch.to_csv(RES / "schemes_comparison.csv", index=False)
spread = rank_tab.max(1) - rank_tab.min(1)

# 重みをでたらめに変える
def mc(Zm, kind, n_draw=10000, conc=1.0):
    if kind == "indicator":
        W = rng.dirichlet(np.full(k, conc), size=n_draw)
    else:
        Wd = rng.dirichlet(np.full(len(DOMS), conc), size=n_draw)
        W = np.zeros((n_draw, k))
        for di, d in enumerate(DOMS):
            idx = np.where(dom == d)[0]
            W[:, idx] = Wd[:, [di]] / len(idx)
    S = Zm @ W.T  # n x draws
    Rk = (-S).argsort(0).argsort(0) + 1
    return Rk, W

out_mc = {}
pref_rows = []
for kind in ["indicator", "domain"]:
    Rk, W = mc(Z, kind)
    lo, med, hi = np.percentile(Rk, [5, 50, 95], axis=1)
    taus = np.array([kendalltau(base, Rk[:, t])[0] for t in range(0, Rk.shape[1], 10)])
    width = hi - lo
    out_mc[kind] = {
        "幅（5〜95%点）の中央値": float(np.median(width)),
        "幅の最小・最大": [float(width.min()), float(width.max())],
        "幅が20位以上の県": int((width >= 20).sum()),
        "幅が10位以上の県": int((width >= 10).sum()),
        "5%以上の回で1位になる県": int(((Rk == 1).mean(1) >= 0.05).sum()),
        "1回でも1位になる県": int(((Rk == 1).mean(1) > 0).sum()),
        "5%以上の回で上位5位に入る県": int(((Rk <= 5).mean(1) >= 0.05).sum()),
        "5%以上の回で下位5位に入る県": int(((Rk >= 43).mean(1) >= 0.05).sum()),
        "上位5位にも下位5位にも5%以上入る県": int((((Rk <= 5).mean(1) >= 0.05) & ((Rk >= 43).mean(1) >= 0.05)).sum()),
        "基準とのτの中央値": float(np.median(taus)),
        "基準とのτの5%点": float(np.percentile(taus, 5)),
    }
    if kind == "domain":
        # どの分野の重みが順位を一番動かすか：各県で順位と分野の重みの順位相関の絶対値を平均
        Wd = np.array([W[:, np.where(dom == d)[0][0]] * (dom == d).sum() for d in DOMS]).T
        infl = {}
        for di, d in enumerate(DOMS):
            cs = [abs(spearmanr(Wd[:, di], Rk[j])[0]) for j in range(n)]
            infl[d] = float(np.mean(cs))
        out_mc["domain_influence"] = infl
    for j in range(n):
        pref_rows.append({"pref_code": X.index[j], "kind": kind, "base_rank": base[j],
                          "p05": lo[j], "p50": med[j], "p95": hi[j],
                          "share_top5": (Rk[j] <= 5).mean(), "share_bottom5": (Rk[j] >= 43).mean()})
pd.DataFrame(pref_rows).to_csv(RES / "rank_intervals_by_pref.csv", index=False)

# データ包絡：重みの下限を変える
bod_rows = []
for alpha in [0.0, 0.01, 0.02, 0.03, 0.04, 0.05]:
    s = bod(Mb, alpha)
    r = ranks(s)
    bod_rows.append({"重みの下限（合計に対する割合）": alpha, "得点1（最良）の県": int((s >= 0.9999).sum()),
                     "得点0.95以上の県": int((s >= 0.95).sum()), "得点の最小": round(s.min(), 3),
                     "基準とのτ": round(kendalltau(base, r)[0], 3)})
bodt = pd.DataFrame(bod_rows)
bodt.to_csv(RES / "bod_alpha.csv", index=False)

# 頑健性
rob = []
# (a) 指標を10個だけ選ぶ
taus10, maxmv = [], []
for t in range(1000):
    idx = rng.choice(k, 10, replace=False)
    r = ranks(Z[:, idx].mean(1))
    taus10.append(kendalltau(base, r)[0]); maxmv.append(np.abs(base - r).max())
rob.append({"確かめたこと": "20指標から10個をでたらめに選ぶ（1,000回）", "基準とのτ": f"中央値{np.median(taus10):.2f}（5%点{np.percentile(taus10,5):.2f}）",
            "順位の差の最大": f"中央値{np.median(maxmv):.0f}位"})
# (b) 1つずつ外す
drop = []
for i in range(k):
    idx = [j for j in range(k) if j != i]
    r = ranks(Z[:, idx].mean(1))
    drop.append({"外した指標": meta["short"].iloc[i], "τ": kendalltau(base, r)[0], "最大の差": np.abs(base - r).max()})
drop = pd.DataFrame(drop).sort_values("τ")
drop.to_csv(RES / "drop_one.csv", index=False)
rob.append({"確かめたこと": "指標を1つずつ外す（20通り）", "基準とのτ": f"{drop['τ'].min():.2f}〜{drop['τ'].max():.2f}",
            "順位の差の最大": f"{drop['最大の差'].min():.0f}〜{drop['最大の差'].max():.0f}位（τが最も下がるのは「{drop['外した指標'].iloc[0]}」）"})
# (c) 向きの決めにくい指標を逆にする
for names_ in [["持ち家比率"], ["有効求人倍率"], ["持ち家比率", "月間実労働時間（男）", "有効求人倍率"]]:
    s2 = sign.copy()
    for nm in names_:
        s2[list(meta["short"]).index(nm)] *= -1
    r = ranks(zscore(oriented(X, s2)).mean(1))
    rob.append({"確かめたこと": "向きを逆にする：" + "・".join(names_), "基準とのτ": f"{kendalltau(base, r)[0]:.2f}",
                "順位の差の最大": f"{np.abs(base - r).max():.0f}位"})
# (d) 約10年前（2015年版）の14指標
c15 = list(X15.columns)
s15 = meta.loc[c15, "sign"].values
r_old = ranks(zscore(X15.values * s15).mean(1))
r_new14 = ranks(zscore(X[c15].values * s15).mean(1))
rob.append({"確かめたこと": "2015年版（2008〜2013年ごろ）の14指標と、同じ14指標の最新年", "基準とのτ": f"新旧のτ {kendalltau(r_old, r_new14)[0]:.2f}（最新14指標と基準20指標のτ {kendalltau(base, r_new14)[0]:.2f}）",
            "順位の差の最大": f"新旧で{np.abs(r_old - r_new14).max():.0f}位"})
# (e) ディリクレの集中度
for conc in [0.5, 1.0, 5.0, 20.0]:
    Rk, _ = mc(Z, "indicator", 5000, conc)
    lo, hi = np.percentile(Rk, [5, 95], axis=1)
    rob.append({"確かめたこと": f"重みのばらつき（ディリクレの集中度 {conc}）", "基準とのτ": "—",
                "順位の差の最大": f"5〜95%点の幅の中央値 {np.median(hi-lo):.0f}位、20位以上の県 {int(((hi-lo)>=20).sum())}"})
# (f) 指標どうしの相関
cz = np.corrcoef(Z, rowvar=False)
iu = np.triu_indices(k, 1)
robt = pd.DataFrame(rob)
robt.to_csv(RES / "robustness.csv", index=False)
pd.DataFrame({"指標": meta["short"], "分野": dom, "第1主成分の負荷量": pc1.round(3), "第1主成分の重み": w_pc1.round(3)}).to_csv(RES / "pca_loadings.csv", index=False)
rank_tab.to_csv(RES / "ranks_by_scheme.csv")

# 人口密度（可住地面積当たり、2026年版の最新年）との関係：得点が「都市か地方か」をどれだけ映すか
_raw = pd.read_csv(DATA / "raw" / "ssds_pref_indicators.csv")
_d = _raw[(_raw.code == "A01202") & (_raw.edition == 2026)].sort_values("year").iloc[-1]
logd = np.log(_d[[f"p{i:02d}" for i in range(1, 48)]].astype(float).values)
dens_corr = {meta["short"].iloc[i]: round(float(np.corrcoef(Z[:, i], logd)[0, 1]), 2) for i in range(k)}
summary = {
    "corr_base_logdensity": round(float(np.corrcoef(Z @ w_eq, logd)[0, 1]), 3),
    "corr_pc1_logdensity": round(float(np.corrcoef(Z @ pc1, logd)[0, 1]), 3),
    "n_ind_neg_with_density": int(sum(v < 0 for v in dens_corr.values())),
    "dens_corr": dens_corr,
    "n_pref": n, "n_ind": k, "domains": DOMS,
    "pca_share": [round(float(s), 3) for s in share[:6]], "pca_m": m,
    "pc1_neg_loadings": [meta["short"].iloc[i] for i in range(k) if pc1[i] < 0],
    "corr_mean_abs": round(float(np.abs(cz[iu]).mean()), 3),
    "corr_share_negative": round(float((cz[iu] < 0).mean()), 3),
    "schemes": sch.to_dict("records"),
    "spread_across_schemes": {"median": float(spread.median()), "max": float(spread.max()), "ge10": int((spread >= 10).sum()), "ge20": int((spread >= 20).sum())},
    "mc": out_mc,
    "bod": bodt.to_dict("records"),
    "robust": robt.to_dict("records"),
}
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))
