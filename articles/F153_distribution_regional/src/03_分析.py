"""03 分析：都道府県の世帯の年間収入の分布を、平均でなく分布（分位関数）で比べる
- 分位関数の差、Wasserstein 距離の位置・広がり・形への分解
- 分布のクラスタリング（Ward＝分位関数の L2、平均だけ・平均＋標準偏差だけとの比較）
- 世帯人員・住宅の所有の関係の構成を全国にそろえた反実仮想の分布（DFL 型）
- 分布の回帰（分位関数を単身世帯割合・持ち家割合に回帰）
- 2018→2023 の変化
頑健性：階級内一様、上の裾の扱い、対数、等価（世帯人員の平方根で割る）、不詳の割り振り、2018年、クラスタ数
"""
import json
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.metrics import silhouette_score, adjusted_rand_score
from common import ROOT, P, YG, SIZE_N, load, bins_of, quantiles, w2_decomp, mix_quantiles
from scipy.interpolate import PchipInterpolator

np.random.seed(153)
RES = ROOT / "results"
BLOCK = {**{c: "北海道・東北" for c in ["01", "02", "03", "04", "05", "06", "07"]},
         **{c: "関東" for c in ["08", "09", "10", "11", "12", "13", "14"]},
         **{c: "中部" for c in ["15", "16", "17", "18", "19", "20", "21", "22", "23"]},
         **{c: "近畿" for c in ["24", "25", "26", "27", "28", "29", "30"]},
         **{c: "中国・四国" for c in ["31", "32", "33", "34", "35", "36", "37", "38", "39"]},
         **{c: "九州・沖縄" for c in ["40", "41", "42", "43", "44", "45", "46", "47"]}}
out = {}


def harmonize18(df):
    """2023年の 100〜150・150〜200 をまとめて 2018年と同じ10階級にする"""
    d = df.copy()
    m = (d.year == 2023) & (d.lo.isin([100, 150]))
    d.loc[m, "lo"] = 100; d.loc[m, "hi"] = 200
    return d.groupby(["year", "code", "pref", "tenure", "lo", "size"], as_index=False).agg(hi=("hi", "first"), households=("households", "sum"))


def qf_table(df, method="pchip", tail_cap=None, unk=None, transform=None):
    """都道府県（＋全国）ごとの分位関数（世帯人員・所有の関係は総数）"""
    sub = df[(df.tenure == "総数") & (df["size"] == "total")]
    Q, A = {}, {}
    for code, g in sub.groupby("code"):
        e, c = bins_of(g)
        q, a = quantiles(e, c, method=method, tail_cap=tail_cap)
        Q[code] = q if transform is None else transform(q)
        A[code] = a
    return pd.DataFrame(Q).T, pd.Series(A)


def equivalized_qf(df):
    """等価：世帯人員 n の世帯の収入を √n で割った分布（世帯人員ごとの分布を割り戻して混ぜる）"""
    sub = df[(df.tenure == "総数") & (df["size"] != "total")]
    Q = {}
    for code, g in sub.groupby("code"):
        Fy = np.zeros_like(YG); s2 = 0; s1 = 0; tot = g.households.sum()
        for s, gs in g.groupby("size"):
            w = gs.households.sum() / tot
            if w <= 0:
                continue
            e, c = bins_of(gs)
            f = PchipInterpolator(e[:-1], c[:-1])
            k = np.sqrt(SIZE_N[s])
            # 等価収入 z = y/k → F_z(z) = F_y(k z)；k z が2,000を超えるところは上の裾（パレート）
            y = np.minimum(YG * k, 2000)
            F = np.maximum.accumulate(np.clip(f(y), 0, 1))
            sa, sb = 1 - c[-2], 1 - c[-1]
            al = np.log(sa / sb) / np.log(2000 / 1500) if sb > 0 and sa > sb else 2.0
            over = YG * k > 2000
            F[over] = 1 - sb * (YG[over] * k / 2000) ** (-al)
            Fy += w * F
        Fy = np.maximum.accumulate(Fy)
        Q[code] = np.interp(P, Fy, YG)   # 上0.5%は格子の上限（2,000万円）で頭打ちになりうるが、等価では上限に届かない
    return pd.DataFrame(Q).T


def frechet(Qp):
    """47都道府県の分位関数（行）について、フレシェ平均（分位関数の平均）とまわりのばらつきの分解"""
    bary = Qp.mean(axis=0).to_numpy()
    rows = [w2_decomp(Qp.loc[c].to_numpy(), bary) for c in Qp.index]
    d = pd.DataFrame(rows, index=Qp.index)
    tot = d.w2sq.mean()
    return dict(frechet_var=tot, frechet_sd=np.sqrt(tot), loc=d["loc"].mean() / tot, scale=d["scale"].mean() / tot,
                shape=d["shape"].mean() / tot), d


def cluster(Qp, k):
    Z = linkage(Qp.to_numpy(), method="ward")
    return fcluster(Z, k, criterion="maxclust")


def stats(Qp):
    return pd.DataFrame({"mean": Qp.mean(axis=1), "sd": Qp.std(axis=1)})


def summarize(Qp):
    fr, _ = frechet(Qp)
    return {k: round(float(v), 4) for k, v in fr.items()}


# ---------------- 基本：2023年 ----------------
df = load()
d23 = df[df.year == 2023]
Q23, A23 = qf_table(d23)
nat = Q23.loc["00000"].to_numpy()
Qp = Q23.drop(index="00000")
pref_name = d23.drop_duplicates("code").set_index("code").pref

# 分位点の表
qt = pd.DataFrame({f"p{int(round(p*100))}": Q23[i] for i, p in enumerate(P) if round(p * 100, 1) in (10.0, 25.0, 50.0, 75.0, 90.0)})
qt["mean_trim"] = Q23.mean(axis=1); qt["pareto_alpha"] = A23; qt["pref"] = pref_name
qt.to_csv(RES / "quantiles_2023.csv", encoding="utf-8")

# 全国との距離と分解
rows = []
for c in Qp.index:
    r = w2_decomp(Qp.loc[c].to_numpy(), nat); r["code"] = c; r["pref"] = pref_name[c]; r["block"] = BLOCK[c[:2]]
    rows.append(r)
wd = pd.DataFrame(rows).set_index("code")
for k in ["loc", "scale", "shape"]:
    wd[k + "_share"] = wd[k] / wd.w2sq
wd.to_csv(RES / "w2_to_national_2023.csv", encoding="utf-8")
assert wd.check.abs().max() < 1e-6

fr23, frd23 = frechet(Qp)
out["frechet_2023"] = {k: round(float(v), 4) for k, v in fr23.items()}
out["w2_to_nat_2023"] = dict(median=float(wd.w2.median()), min=float(wd.w2.min()), max=float(wd.w2.max()),
                             share_loc_median=float(wd.loc_share.median()), share_scale_median=float(wd.scale_share.median()),
                             share_shape_median=float(wd.shape_share.median()),
                             n_loc_majority=int((wd.loc_share > 0.5).sum()), n_scale_or_shape_majority=int((wd.loc_share <= 0.5).sum()))

# 分位点ごとの都道府県間のばらつき
sd_p = Qp.std(axis=0).to_numpy(); mean_p = Qp.mean(axis=0).to_numpy()
spread = pd.DataFrame({"p": P, "sd_across_pref": sd_p, "mean_across_pref": mean_p, "cv": sd_p / mean_p,
                       "q90_q10": Qp.quantile(0.9).to_numpy() - Qp.quantile(0.1).to_numpy()})
spread.to_csv(RES / "spread_by_p_2023.csv", index=False)
out["spread"] = {f"p{int(round(p*100))}": dict(sd=round(float(s), 1), cv=round(float(cv), 3))
                 for p, s, cv in zip(P, sd_p, sd_p / mean_p) if round(p * 100, 1) in (10.0, 25.0, 50.0, 75.0, 90.0)}

# 平均・中央値と、下・上の分位点の関係（平均で並べた順と、分布の別の場所で並べた順がどれだけ一致するか）
st = stats(Qp)
cor = {}
for lab, j in [("p10", 19), ("p25", 49), ("p50", 99), ("p75", 149), ("p90", 179)]:
    cor[lab] = round(float(pd.Series(Qp.iloc[:, j]).corr(st["mean"], method="spearman")), 3)
cor["sd_vs_mean"] = round(float(st["sd"].corr(st["mean"], method="spearman")), 3)
cor["p10_vs_p90"] = round(float(Qp.iloc[:, 19].corr(Qp.iloc[:, 179], method="spearman")), 3)
out["rank_corr_with_mean"] = cor

# ---------------- クラスタリング ----------------
sil = {}
for k in range(2, 7):
    lab = cluster(Qp, k)
    sil[k] = float(silhouette_score(Qp.to_numpy(), lab))
out["silhouette"] = {k: round(v, 3) for k, v in sil.items()}
K = 3  # シルエットは k=2・3 がほぼ同じで最も高い。k=4 以上では1県だけのクラスタができるので3を基本にする
lab_full = cluster(Qp, K)
lab_mean = fcluster(linkage(st[["mean"]].to_numpy(), "ward"), K, "maxclust")
z = (st - st.mean()) / st.std()
lab_ms = fcluster(linkage(z.to_numpy(), "ward"), K, "maxclust")
out["ari_full_vs_mean_only"] = round(float(adjusted_rand_score(lab_full, lab_mean)), 3)
out["ari_full_vs_mean_sd"] = round(float(adjusted_rand_score(lab_full, lab_ms)), 3)
cl = pd.DataFrame({"pref": pref_name[Qp.index], "block": [BLOCK[c[:2]] for c in Qp.index], "cluster": lab_full,
                   "cluster_mean_only": lab_mean, "cluster_mean_sd": lab_ms, "mean": st["mean"], "sd": st["sd"],
                   "p10": Qp.iloc[:, 19], "p50": Qp.iloc[:, 99], "p90": Qp.iloc[:, 179]}, index=Qp.index)
# クラスタ番号を平均の小さい順ではなく「中央値の順」で 1..K に振り直す（並び替えのためだけ）
order = cl.groupby("cluster").p50.mean().sort_values().index
remap = {o: i + 1 for i, o in enumerate(order)}
cl["cluster"] = cl.cluster.map(remap)
cl.to_csv(RES / "clusters_2023.csv", encoding="utf-8")
prof = []
for k_, g in cl.groupby("cluster"):
    q = Qp.loc[g.index].mean(axis=0).to_numpy()
    prof.append(dict(cluster=int(k_), n=len(g), p10=q[19], p25=q[49], p50=q[99], p75=q[149], p90=q[179],
                     ratio_90_10=q[179] / q[19], blocks=json.dumps(g.block.value_counts().to_dict(), ensure_ascii=False)))
prof = pd.DataFrame(prof); prof.to_csv(RES / "cluster_profiles_2023.csv", index=False, encoding="utf-8")
cq = pd.DataFrame({int(k_): Qp.loc[g.index].mean(axis=0).to_numpy() for k_, g in cl.groupby("cluster")}, index=P)
cq.to_csv(RES / "cluster_quantile_functions_2023.csv", encoding="utf-8")
out["cluster_profiles"] = prof.round(2).to_dict("records")
# クラスタの中の分散と間の分散（W² で）
within = sum(((Qp.loc[g.index] - Qp.loc[g.index].mean(axis=0)) ** 2).to_numpy().mean(axis=1).sum() for _, g in cl.groupby("cluster"))
total = ((Qp - Qp.mean(axis=0)) ** 2).to_numpy().mean(axis=1).sum()
out["cluster_between_share"] = round(float(1 - within / total), 3)
for kk in [2, 4, 5]:
    out[f"ari_k3_vs_k{kk}"] = round(float(adjusted_rand_score(lab_full, cluster(Qp, kk))), 3)

# ---------------- 構成をそろえた反実仮想（DFL 型） ----------------
cells = d23[(d23["size"] != "total") & (d23.tenure.isin(["持ち家", "借家"]))].copy()
cells["cell"] = cells.tenure + "×" + cells["size"]
nat_cells = cells[cells.code == "00000"]
w_nat = {
    "size": (d23[(d23.code == "00000") & (d23.tenure == "総数") & (d23["size"] != "total")].groupby("size").households.sum()),
    "tenure": (d23[(d23.code == "00000") & (d23.tenure.isin(["持ち家", "借家"])) & (d23["size"] == "total")].groupby("tenure").households.sum()),
    "cell": nat_cells.groupby("cell").households.sum(),
}
w_nat = {k: (v / v.sum()).to_dict() for k, v in w_nat.items()}
cf = {}
for c in Qp.index:
    g_size = d23[(d23.code == c) & (d23.tenure == "総数") & (d23["size"] != "total")]
    g_ten = d23[(d23.code == c) & (d23.tenure.isin(["持ち家", "借家"])) & (d23["size"] == "total")]
    g_cell = cells[cells.code == c]
    cf[("size", c)] = mix_quantiles(g_size, w_nat["size"], "size")
    cf[("tenure", c)] = mix_quantiles(g_ten, w_nat["tenure"], "tenure")
    cf[("cell", c)] = mix_quantiles(g_cell, w_nat["cell"], "cell")
dfl = {}
for kind in ["size", "tenure", "cell"]:
    Qc = pd.DataFrame({c: cf[(kind, c)] for c in Qp.index}).T
    fr, _ = frechet(Qc)
    dfl[kind] = dict(frechet_var=round(float(fr["frechet_var"]), 1), explained=round(float(1 - fr["frechet_var"] / fr23["frechet_var"]), 3),
                     loc=round(float(fr["loc"]), 3), scale=round(float(fr["scale"]), 3), shape=round(float(fr["shape"]), 3))
    Qc.to_csv(RES / f"counterfactual_qf_{kind}_2023.csv", encoding="utf-8")
# 位置・広がり・形それぞれのばらつきがどれだけ減ったか
Qcell = pd.DataFrame({c: cf[("cell", c)] for c in Qp.index}).T
_, frd_cf = frechet(Qcell)
for comp in ["loc", "scale", "shape"]:
    dfl["cell_" + comp + "_reduction"] = round(float(1 - frd_cf[comp].mean() / frd23[comp].mean()), 3)
out["dfl_2023"] = dfl
lab_cf = cluster(Qcell, K)
# 構成をそろえると平均がどちらへ動いたか（単身世帯の多い県ほど上がるか）
shift = Qcell.mean(axis=1) - Qp.mean(axis=1)
tot_h0 = d23[(d23.tenure == "総数") & (d23["size"] == "total")].groupby("code").households.sum()
one0 = (d23[(d23.tenure == "総数") & (d23["size"] == "p1")].groupby("code").households.sum() / tot_h0).loc[Qp.index]
out["dfl_mean_shift"] = dict(corr_with_one_person=round(float(shift.corr(one0, method="spearman")), 3),
                             corr_shift_with_mean=round(float(shift.corr(Qp.mean(axis=1), method="spearman")), 3),
                             shift_min=round(float(shift.min()), 1), shift_max=round(float(shift.max()), 1))
pd.DataFrame({"shift_mean": shift, "one_person": one0}).to_csv(RES / "dfl_mean_shift_2023.csv", encoding="utf-8")
out["ari_cluster_vs_composition_adjusted"] = round(float(adjusted_rand_score(lab_full, lab_cf)), 3)

# ---------------- 分布の回帰（分位関数を説明変数に回帰） ----------------
x = pd.DataFrame(index=Qp.index)
tot_h = d23[(d23.tenure == "総数") & (d23["size"] == "total")].groupby("code").households.sum()
x["one_person"] = d23[(d23.tenure == "総数") & (d23["size"] == "p1")].groupby("code").households.sum() / tot_h
x["owner"] = d23[(d23.tenure == "持ち家") & (d23["size"] == "total")].groupby("code").households.sum() / tot_h
x["mean_size"] = sum(d23[(d23.tenure == "総数") & (d23["size"] == s)].groupby("code").households.sum() * n for s, n in SIZE_N.items()) / tot_h
x = x.loc[Qp.index]
x.to_csv(RES / "covariates_2023.csv", encoding="utf-8")


def frechet_reg(Qp, X):
    Xd = np.column_stack([np.ones(len(X)), ((X - X.mean()) / X.std()).to_numpy()])
    B, *_ = np.linalg.lstsq(Xd, Qp.to_numpy(), rcond=None)
    fit = Xd @ B
    # 分位関数の単調性を保つ（あてはめ値を並べ替え＝L2 の射影の近似）
    fit = np.sort(fit, axis=1)
    resid = Qp.to_numpy() - fit
    tot = ((Qp - Qp.mean(axis=0)) ** 2).to_numpy().mean(axis=1).sum()
    r2 = 1 - (resid ** 2).mean(axis=1).sum() / tot
    r2_p = 1 - (resid ** 2).sum(axis=0) / ((Qp - Qp.mean(axis=0)) ** 2).to_numpy().sum(axis=0)
    return B, r2, r2_p


reg = {}
for name, cols in [("one_person", ["one_person"]), ("owner", ["owner"]), ("both", ["one_person", "owner"]),
                   ("mean_size", ["mean_size"]), ("all3", ["one_person", "owner", "mean_size"])]:
    B, r2, r2p = frechet_reg(Qp, x[cols])
    reg[name] = dict(r2_w=round(float(r2), 3), r2_p10=round(float(r2p[19]), 3), r2_p50=round(float(r2p[99]), 3), r2_p90=round(float(r2p[179]), 3))
    if name == "both":
        pd.DataFrame({"p": P, "intercept": B[0], "b_one_person": B[1], "b_owner": B[2], "r2": r2p}).to_csv(RES / "frechet_regression_coef_2023.csv", index=False)
# 交差検証（1県抜き）
pred_err = []; base_err = []
for c in Qp.index:
    tr = Qp.drop(index=c); xt = x.drop(index=c)[["one_person", "owner"]]
    Xd = np.column_stack([np.ones(len(xt)), ((xt - xt.mean()) / xt.std()).to_numpy()])
    B, *_ = np.linalg.lstsq(Xd, tr.to_numpy(), rcond=None)
    xc = ((x.loc[[c], ["one_person", "owner"]] - xt.mean()) / xt.std()).to_numpy()
    f = np.sort(np.column_stack([np.ones(1), xc]) @ B, axis=1)[0]
    pred_err.append(np.sqrt(np.mean((Qp.loc[c].to_numpy() - f) ** 2)))
    base_err.append(np.sqrt(np.mean((Qp.loc[c].to_numpy() - tr.mean(axis=0).to_numpy()) ** 2)))
reg["loo_w2_model"] = round(float(np.mean(pred_err)), 2); reg["loo_w2_barycenter"] = round(float(np.mean(base_err)), 2)
out["frechet_regression"] = reg
out["covariate_corr"] = x.corr().round(3).to_dict()

# ---------------- 対数の目で見る：分布は「全国の何倍か」でほぼ表せるか ----------------
lg = lambda q: np.log(q + 10)
QL = Q23.apply(lambda r: lg(r.to_numpy()), axis=1, result_type="expand"); QL.columns = range(len(P))
QLp = QL.drop(index="00000")
frL, frdL = frechet(QLp)
out["log_frechet_2023"] = {k: round(float(v), 4) for k, v in frL.items()}
# 全国の分位関数を k 倍した形で各県を表したときの、残りの W²（万円の目）
mult = []
for c in Qp.index:
    q = Qp.loc[c].to_numpy()
    kk = float(np.exp(np.mean(np.log(q + 10) - np.log(nat + 10))))
    fit = (nat + 10) * kk - 10
    k_ls = float((q @ nat) / (nat @ nat))
    mult.append(dict(code=c, k_geo=kk, k_ls=k_ls, w2_nat=np.sqrt(np.mean((q - nat) ** 2)), w2_resid=np.sqrt(np.mean((q - k_ls * nat) ** 2))))
mult = pd.DataFrame(mult).set_index("code"); mult.to_csv(RES / "multiplicative_fit_2023.csv", encoding="utf-8")
out["multiplicative"] = dict(k_min=round(float(mult.k_ls.min()), 3), k_max=round(float(mult.k_ls.max()), 3),
                             resid_share_of_w2sq=round(float((mult.w2_resid ** 2).sum() / (mult.w2_nat ** 2).sum()), 3),
                             w2_resid_median=round(float(mult.w2_resid.median()), 1), w2_nat_median=round(float(mult.w2_nat.median()), 1))

# ---------------- 2018→2023（10階級にそろえて） ----------------
dh = harmonize18(df)
Q18h, _ = qf_table(dh[dh.year == 2018]); Q23h, _ = qf_table(dh[dh.year == 2023])
Q18p = Q18h.drop(index="00000"); Q23p = Q23h.drop(index="00000")
fr18, _ = frechet(Q18p); fr23h, _ = frechet(Q23p)
chg = []
for c in Q18p.index:
    r = w2_decomp(Q23p.loc[c].to_numpy(), Q18p.loc[c].to_numpy()); r["code"] = c; r["pref"] = pref_name[c]
    r["dmean"] = Q23p.loc[c].mean() - Q18p.loc[c].mean(); r["dp10"] = Q23p.loc[c].iloc[19] - Q18p.loc[c].iloc[19]
    r["dp50"] = Q23p.loc[c].iloc[99] - Q18p.loc[c].iloc[99]; r["dp90"] = Q23p.loc[c].iloc[179] - Q18p.loc[c].iloc[179]
    chg.append(r)
chg = pd.DataFrame(chg).set_index("code"); chg.to_csv(RES / "change_2018_2023.csv", encoding="utf-8")
natc = w2_decomp(Q23h.loc["00000"].to_numpy(), Q18h.loc["00000"].to_numpy())
out["change_2018_2023"] = dict(
    frechet_var_2018=round(float(fr18["frechet_var"]), 1), frechet_var_2023_10cls=round(float(fr23h["frechet_var"]), 1),
    shares_2018={k: round(float(fr18[k]), 3) for k in ["loc", "scale", "shape"]},
    shares_2023_10cls={k: round(float(fr23h[k]), 3) for k in ["loc", "scale", "shape"]},
    national=dict(w2=round(float(natc["w2"]), 1), dmean=round(float(Q23h.loc["00000"].mean() - Q18h.loc["00000"].mean()), 1),
                  dp10=round(float(Q23h.loc["00000"].iloc[19] - Q18h.loc["00000"].iloc[19]), 1),
                  dp50=round(float(Q23h.loc["00000"].iloc[99] - Q18h.loc["00000"].iloc[99]), 1),
                  dp90=round(float(Q23h.loc["00000"].iloc[179] - Q18h.loc["00000"].iloc[179]), 1)),
    pref_dp10_median=round(float(chg.dp10.median()), 1), pref_dp50_median=round(float(chg.dp50.median()), 1),
    pref_dp90_median=round(float(chg.dp90.median()), 1),
    n_dp90_gt_dp10=int((chg.dp90 > chg.dp10).sum()),
    corr_dmean_initial_mean=round(float(chg.dmean.corr(Q18p.mean(axis=1), method="spearman")), 3),
    ari_cluster_2018_2023=round(float(adjusted_rand_score(cluster(Q18p, K), cluster(Q23p, K))), 3),
    log_frechet_var_2018=round(float(frechet(np.log(Q18p + 10))[0]["frechet_var"]), 5),
    log_frechet_var_2023=round(float(frechet(np.log(Q23p + 10))[0]["frechet_var"]), 5),
    cv_p50_2018=round(float(Q18p.iloc[:, 99].std() / Q18p.iloc[:, 99].mean()), 4),
    cv_p50_2023=round(float(Q23p.iloc[:, 99].std() / Q23p.iloc[:, 99].mean()), 4),
)

# ---------------- 頑健性 ----------------
rob = {}
base_lab = lab_full


def rob_entry(Qr, name):
    fr, _ = frechet(Qr)
    lab = cluster(Qr, K)
    rob[name] = dict(loc=round(float(fr["loc"]), 3), scale=round(float(fr["scale"]), 3), shape=round(float(fr["shape"]), 3),
                     ari_vs_base=round(float(adjusted_rand_score(base_lab, lab)), 3),
                     between_share=round(float(1 - sum(((Qr.loc[Qr.index[lab == k_]] - Qr.loc[Qr.index[lab == k_]].mean(axis=0)) ** 2).to_numpy().mean(axis=1).sum() for k_ in np.unique(lab)) / ((Qr - Qr.mean(axis=0)) ** 2).to_numpy().mean(axis=1).sum()), 3))


rob_entry(Qp, "基本（単調スプライン＋パレート、万円）")
Qu, _ = qf_table(d23, method="uniform"); rob_entry(Qu.drop(index="00000"), "階級内一様")
Qt, _ = qf_table(d23, tail_cap=3000); rob_entry(Qt.drop(index="00000"), "上の裾を2,000〜3,000万円の一様")
Ql, _ = qf_table(d23, transform=lambda q: np.log(q + 10)); rob_entry(Ql.drop(index="00000"), "対数（log(収入＋10万円)）")
Qe = equivalized_qf(d23); rob_entry(Qe.drop(index="00000"), "等価（世帯人員の平方根で割る）")
rob_entry(Q23p, "10階級にそろえる")
# 不詳を一番下／一番上の階級に入れる
raw = pd.read_csv(ROOT / "data/households_long.csv", dtype={"code": str, "inc_code": str})
r23 = raw[(raw.year == 2023) & (raw.inc_code != "00")].copy()
for where, lo, hi in [("不詳を一番下の階級（100万円未満）へ", 0, 100), ("不詳を700〜1,000万円の階級へ", 700, 1000)]:
    r = r23.copy(); m = r.inc_code == "99"; r.loc[m, "lo"] = lo; r.loc[m, "hi"] = hi
    Qr, _ = qf_table(r); rob_entry(Qr.drop(index="00000"), where)
# 等価でも構成をそろえると
fr_e, _ = frechet(Qe.drop(index="00000"))
rob["等価_frechet_var"] = round(float(fr_e["frechet_var"]), 1)
rob["相対のばらつき（フレシェ標準偏差÷平均）"] = dict(base=round(float(np.sqrt(fr23["frechet_var"]) / Qp.to_numpy().mean()), 4),
                                    equivalized=round(float(np.sqrt(fr_e["frechet_var"]) / Qe.drop(index="00000").to_numpy().mean()), 4))
out["robustness"] = rob
# 2018年のデータで同じ分解
fr18full, _ = frechet(qf_table(df[df.year == 2018])[0].drop(index="00000"))
out["robustness_2018"] = {k: round(float(fr18full[k]), 3) for k in ["loc", "scale", "shape"]}
# 2018年の構成の入れ替え
d18 = df[df.year == 2018]
cells18 = d18[(d18["size"] != "total") & (d18.tenure.isin(["持ち家", "借家"]))].copy(); cells18["cell"] = cells18.tenure + "×" + cells18["size"]
wn18 = cells18[cells18.code == "00000"].groupby("cell").households.sum(); wn18 = (wn18 / wn18.sum()).to_dict()
Q18full = qf_table(d18)[0].drop(index="00000")
Qc18 = pd.DataFrame({c: mix_quantiles(cells18[cells18.code == c], wn18, "cell") for c in Q18full.index}).T
out["dfl_2018_cell_explained"] = round(float(1 - frechet(Qc18)[0]["frechet_var"] / frechet(Q18full)[0]["frechet_var"]), 3)

json.dump(out, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
