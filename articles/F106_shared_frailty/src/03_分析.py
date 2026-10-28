"""本分析：同じ県（市区町村）の法人は、同じように閉鎖しやすいのか。

1. 独立を仮定したモデル（フレイルなし）、県のガンマ・フレイル、県の対数正規フレイル、県の固定効果
2. フレイルの大きさ：分散θ、2社の閉鎖時刻の連動（Kendall のτ = θ/(θ+2)）、z の90%範囲、尤度比検定
3. 分散の分け方：属性を入れる前後、市区町村のフレイル、県の固定効果を入れた上での市区町村のフレイル
4. 経験ベイズで縮めた県・市区町村の倍率（名前は出さない）
5. 安定性：設立年の前半・後半、株式会社とそれ以外で、県の倍率がそろうか
"""
import json, numpy as np, pandas as pd
from scipy.stats import gamma as G, spearmanr, pearsonr, chi2
from common import DATA, RES, SEED
from frailty import fit_poisson, fit_gamma, fit_lognormal, coef_table

np.random.seed(SEED)
c = pd.read_parquet(DATA / "pe_cells.parquet")
KEYS = ["kindj_合同会社", "kindj_その他法人", "area_東京23区", "area_政令市"]
LAB = {"kindj_合同会社": "合同会社（対 株式会社）", "kindj_その他法人": "一般社団・NPOなど（対 株式会社）",
       "area_東京23区": "東京23区（対 その他の市町村）", "area_政令市": "政令市（対 その他の市町村）"}


def by(cells, keys):
    return cells.groupby(keys, as_index=False)[["expo", "ev_all", "ev_01", "ev_mg"]].sum()


cp = by(c, ["prefn", "kindj", "area", "cohort", "k"])
reg = {**{p: "北海道・東北" for p in range(1, 8)}, **{p: "関東" for p in range(8, 15)},
       **{p: "中部" for p in range(15, 24)}, **{p: "近畿" for p in range(24, 31)},
       **{p: "中国・四国" for p in range(31, 40)}, **{p: "九州・沖縄" for p in range(40, 48)}}
summ = {}

# 1. モデルの比較
f0 = fit_poisson(cp, group="prefn")
fg = fit_gamma(cp, group="prefn")
fl = fit_lognormal(cp, group="prefn")
ffe = fit_poisson(cp, fe="prefn", group="prefn")
rows = []
for k in KEYS:
    i = f0.names.index(k)
    rows.append(dict(term=LAB[k], model="独立（通常のSE）", hr=np.exp(f0.beta[i]), lo=np.exp(f0.beta[i] - 1.96 * f0.se[i]), hi=np.exp(f0.beta[i] + 1.96 * f0.se[i]), se=f0.se[i]))
    rows.append(dict(term=LAB[k], model="独立（県で束ねた頑健SE）", hr=np.exp(f0.beta[i]), lo=np.exp(f0.beta[i] - 1.96 * f0.se_robust[i]), hi=np.exp(f0.beta[i] + 1.96 * f0.se_robust[i]), se=f0.se_robust[i]))
    for nm, f in [("県のガンマ・フレイル", fg), ("県の対数正規フレイル", fl), ("県の固定効果", ffe)]:
        j = f.names.index(k)
        rows.append(dict(term=LAB[k], model=nm, hr=np.exp(f.beta[j]), lo=np.exp(f.beta[j] - 1.96 * f.se[j]), hi=np.exp(f.beta[j] + 1.96 * f.se[j]), se=f.se[j]))
hr = pd.DataFrame(rows); hr.to_csv(RES / "hr_by_model.csv", index=False)
print(hr.round(3).to_string())


def frailty_stats(theta):
    a = 1 / theta
    q05, q95 = G.ppf([0.05, 0.95], a, scale=theta)
    return dict(theta=theta, sd=np.sqrt(theta), kendall_tau=theta / (theta + 2), z05=q05, z95=q95)


lr = 2 * (fg.loglik - f0.loglik)
summ["pref_gamma"] = {**frailty_stats(fg.theta), "theta_lo": fg.theta * np.exp(-1.96 * fg.se_logtheta), "theta_hi": fg.theta * np.exp(1.96 * fg.se_logtheta),
                      "LR": lr, "p_LR": 0.5 * chi2.sf(lr, 1)}
summ["pref_lognormal"] = dict(sigma=fl.sigma, sigma_lo=fl.sigma * np.exp(-1.96 * fl.se_logsigma), sigma_hi=fl.sigma * np.exp(1.96 * fl.se_logsigma),
                              mhr=float(np.exp(np.sqrt(2) * fl.sigma * 0.6745)), z05=float(np.exp(-1.645 * fl.sigma)), z95=float(np.exp(1.645 * fl.sigma)),
                              loglik=fl.loglik, loglik_gamma=fg.loglik)
summ["fe_spread"] = dict(sd_log_fe=float(np.std(np.r_[0, ffe.beta[[i for i, n in enumerate(ffe.names) if n.startswith("prefn_")]]])))
summ["n"] = dict(firms=int(pd.read_parquet(DATA / "firms.parquet").shape[0]), events=int(c.ev_all.sum()), risk_years=float(c.expo.sum()),
                 pref=47, muni=int(c.muni.nunique()))
# 東京23区の係数：SE の比
i = f0.names.index("area_東京23区"); j = fg.names.index("area_東京23区")
summ["se_ratio_tokyo"] = dict(naive=f0.se[i], robust=f0.se_robust[i], gamma=fg.se[j], ratio_robust=f0.se_robust[i] / f0.se[i], ratio_gamma=fg.se[j] / f0.se[i])
i = f0.names.index("kindj_合同会社"); j = fg.names.index("kindj_合同会社")
summ["se_ratio_llc"] = dict(naive=f0.se[i], robust=f0.se_robust[i], gamma=fg.se[j], ratio_robust=f0.se_robust[i] / f0.se[i], ratio_gamma=fg.se[j] / f0.se[i])

# 2-3. 分散の分け方
decomp = []
fn = fit_gamma(cp, cov=("cohort",), group="prefn")
decomp.append(dict(setting="県：設立年だけ調整", unit="県", **frailty_stats(fn.theta)))
decomp.append(dict(setting="県：種別・地域区分・設立年を調整（基本）", unit="県", **frailty_stats(fg.theta)))
cr = c.assign(region=c.prefn.map(reg))
fr = fit_gamma(by(cr, ["region", "kindj", "area", "cohort", "k"]), group="region")
decomp.append(dict(setting="地方（6）", unit="地方", **frailty_stats(fr.theta)))
fm = fit_gamma(c, group="muni")
decomp.append(dict(setting="市区町村", unit="市区町村", **frailty_stats(fm.theta)))
fmw = fit_gamma(c, group="muni", fe="prefn")
decomp.append(dict(setting="市区町村（県の固定効果を入れて、県の中の違いだけ）", unit="市区町村", **frailty_stats(fmw.theta)))
dec = pd.DataFrame(decomp); dec.to_csv(RES / "variance_decomposition.csv", index=False)
print(dec.round(4).to_string())
summ["muni_gamma"] = {**frailty_stats(fm.theta), "LR": 2 * (fm.loglik - fit_poisson(c, group="muni").loglik)}
summ["muni_within_pref"] = frailty_stats(fmw.theta)

# 4. 経験ベイズの倍率
a = 1 / fg.theta
pref = pd.DataFrame(dict(prefn=fg.groups, region=[reg[p] for p in fg.groups], D=fg.D, E=fg.H, raw=fg.raw, eb=fg.post,
                         eb_lo=G.ppf(0.025, fg.D + a, scale=1 / (a + fg.H)), eb_hi=G.ppf(0.975, fg.D + a, scale=1 / (a + fg.H)),
                         ln_eb=fl.post_z))
pref.to_csv(RES / "pref_eb.csv", index=False)   # 県コードは結果の再現用。記事では県名を出さない
am = 1 / fm.theta
muni = pd.DataFrame(dict(muni=fm.groups, D=fm.D, E=fm.H, raw=fm.raw, eb=fm.post))
muni["prefn"] = muni.muni // 1000
muni.drop(columns="muni").to_csv(RES / "muni_eb.csv", index=False)   # 市区町村コードは出さない
summ["pref_eb"] = dict(raw_min=float(pref.raw.min()), raw_max=float(pref.raw.max()), eb_min=float(pref.eb.min()), eb_max=float(pref.eb.max()),
                       n_ci_excl1=int(((pref.eb_lo > 1) | (pref.eb_hi < 1)).sum()))
small = muni.E < 10
summ["muni_eb"] = dict(n=len(muni), n_small=int(small.sum()), raw_sd_small=float(np.std(np.log(muni.raw[small].clip(lower=0.05)))),
                       eb_sd_small=float(np.std(np.log(muni.eb[small]))), raw_sd_large=float(np.std(np.log(muni.raw[muni.E >= 100]))),
                       eb_sd_large=float(np.std(np.log(muni.eb[muni.E >= 100]))), n_large=int((muni.E >= 100).sum()),
                       zero_event=int((muni.D == 0).sum()))
print(summ["muni_eb"])

# 5. 安定性
stab = {}
c5 = c[c.k <= 4]
early = fit_gamma(by(c5[c5.cohort <= 2019], ["prefn", "kindj", "area", "cohort", "k"]), group="prefn")
late = fit_gamma(by(c5[c5.cohort >= 2020], ["prefn", "kindj", "area", "cohort", "k"]), group="prefn")
x, y = np.log(early.post), np.log(late.post)
stab["cohort_pref"] = dict(theta_early=early.theta, theta_late=late.theta, pearson=pearsonr(x, y)[0], spearman=spearmanr(x, y)[0])
kk = c[c.kindj == "株式会社"]; ko = c[c.kindj != "株式会社"]
f1 = fit_gamma(by(kk, ["prefn", "kindj", "area", "cohort", "k"]), cov=("area", "cohort"), group="prefn")
f2 = fit_gamma(by(ko, ["prefn", "kindj", "area", "cohort", "k"]), group="prefn")
stab["kind_pref"] = dict(theta_kk=f1.theta, theta_other=f2.theta, pearson=pearsonr(np.log(f1.post), np.log(f2.post))[0], spearman=spearmanr(f1.post, f2.post)[0])
me = fit_gamma(c5[c5.cohort <= 2019], group="muni"); ml = fit_gamma(c5[c5.cohort >= 2020], group="muni")
mm = pd.DataFrame(dict(muni=me.groups, e=np.log(me.post), Ee=me.H)).merge(pd.DataFrame(dict(muni=ml.groups, l=np.log(ml.post), El=ml.H)), on="muni")
big = mm[(mm.Ee >= 30) & (mm.El >= 30)]
stab["cohort_muni"] = dict(n=len(mm), pearson=pearsonr(mm.e, mm.l)[0], n_big=len(big), pearson_big=pearsonr(big.e, big.l)[0])
pd.DataFrame(dict(prefn=early.groups, region=[reg[p] for p in early.groups], early=early.post, late=late.post, kk=f1.post, other=f2.post)).to_csv(RES / "stability_pref.csv", index=False)
summ["stability"] = stab
print(json.dumps(stab, ensure_ascii=False, indent=1))

json.dump(summ, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: summ[k] for k in ["pref_gamma", "pref_lognormal", "fe_spread", "se_ratio_tokyo", "se_ratio_llc", "muni_gamma", "muni_within_pref", "pref_eb"]}, ensure_ascii=False, indent=1, default=float))
