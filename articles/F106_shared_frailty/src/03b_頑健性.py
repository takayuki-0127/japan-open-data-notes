"""頑健性とシミュレーション。

A. 設定を変えたときの県のフレイル（θ）と主な係数
   閉鎖の定義（清算の結了等だけ）／東京都を除く／2019年までの設立だけ／設立後5年まで／フレイルの分布（対数正規）／合併を結末にした参考
B. 種別の差は県によって違うか（県×種別の交互作用）。独立モデルの頑健SEが大きくなった理由の確認
C. シミュレーション：本当のθを決めてデータを作り直し、θを取り戻せるか、θ=0 で誤って「ばらつきあり」と出る割合、
   ばらつきを無視したときの東京23区の95%区間が真の値を含む割合
"""
import json, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from scipy.stats import chi2
from common import DATA, RES, SEED
from frailty import fit_poisson, fit_gamma, fit_lognormal, design

rng = np.random.default_rng(SEED)
c = pd.read_parquet(DATA / "pe_cells.parquet")
by = lambda x: x.groupby(["prefn", "kindj", "area", "cohort", "k"], as_index=False)[["expo", "ev_all", "ev_01", "ev_mg"]].sum()
cp = by(c)
KEYS = ["kindj_合同会社", "kindj_その他法人", "area_東京23区", "area_政令市"]


def row(name, f, kind="gamma"):
    th = f.theta if kind == "gamma" else f.sigma**2
    out = dict(setting=name, theta=th, sd=np.sqrt(th), kendall_tau=th / (th + 2))
    for k in KEYS:
        if k in f.names:
            out[k] = np.exp(f.beta[f.names.index(k)])
    return out


rows = []
rows.append(row("基本（県・ガンマ）", fit_gamma(cp)))
rows.append(row("フレイルを対数正規に", fit_lognormal(cp), "ln"))
rows.append(row("閉鎖＝清算の結了等だけ", fit_gamma(cp, ev="ev_01")))
rows.append(row("東京都を除く（46道府県）", fit_gamma(cp[cp.prefn != 13])))
rows.append(row("2019年までの設立だけ", fit_gamma(cp[cp.cohort <= 2019])))
rows.append(row("設立後5年まで", fit_gamma(cp[cp.k <= 4])))
rows.append(row("設立後6年目以降", fit_gamma(cp[cp.k >= 5])))
rows.append(row("参考：結末を合併にした場合", fit_gamma(cp, ev="ev_mg")))
rob = pd.DataFrame(rows); rob.to_csv(RES / "robustness.csv", index=False)
print(rob.round(4).to_string())

# B. 県×種別
fe = fit_poisson(cp, fe="prefn")
cpi = cp.copy(); cpi["pk"] = cpi.prefn.astype(str) + "_" + cpi.kindj
fi = fit_poisson(cpi, cov=("kindj", "area", "cohort"), fe="pk")
lr = 2 * (fi.loglik - fe.loglik); dfree = len(fi.beta) - len(fe.beta)
# 県ごとの合同会社の倍率（県の中での比較）
per = []
for p, g in cp.groupby("prefn"):
    if g.kindj.nunique() < 3: continue
    f = fit_poisson(g, cov=("kindj", "area", "cohort"))
    i = f.names.index("kindj_合同会社"); j = f.names.index("kindj_その他法人")
    per.append(dict(prefn=p, llc=f.beta[i], llc_se=f.se[i], oth=f.beta[j], oth_se=f.se[j]))
per = pd.DataFrame(per); per.to_csv(RES / "kind_by_pref.csv", index=False)


def tau2(b, se):  # DerSimonian–Laird のばらつき（標本誤差を除いた県の間の分散）
    w = 1 / se**2; m = np.sum(w * b) / w.sum(); Q = np.sum(w * (b - m) ** 2)
    return max(0, (Q - (len(b) - 1)) / (w.sum() - np.sum(w**2) / w.sum())), np.exp(m)


t_llc, m_llc = tau2(per.llc, per.llc_se); t_oth, m_oth = tau2(per.oth, per.oth_se)
het = dict(LR=lr, df=dfree, p=chi2.sf(lr, dfree), llc_tau=np.sqrt(t_llc), llc_mean=m_llc,
           llc_range_80=[float(np.exp(np.log(m_llc) - 1.2816 * np.sqrt(t_llc))), float(np.exp(np.log(m_llc) + 1.2816 * np.sqrt(t_llc)))],
           oth_tau=np.sqrt(t_oth), oth_mean=m_oth,
           oth_range_80=[float(np.exp(np.log(m_oth) - 1.2816 * np.sqrt(t_oth))), float(np.exp(np.log(m_oth) + 1.2816 * np.sqrt(t_oth)))])
print(het)

# C. シミュレーション
base = fit_gamma(cp)
X = design(cp).to_numpy(); off = np.log(cp.expo.to_numpy())
g, gidx = np.unique(cp.prefn.to_numpy(), return_inverse=True)
mu0 = np.exp(X @ base.beta + off)
it = base.names.index("area_東京23区"); true_tokyo = base.beta[it]
sim = []
for th in [0.0, 0.01, 0.027, 0.05]:
    for r in range(100):
        z = np.ones(len(g)) if th == 0 else rng.gamma(1 / th, th, len(g))
        y = rng.poisson(mu0 * z[gidx])
        cs = cp.copy(); cs["ev_all"] = y
        fp = fit_poisson(cs); fg = fit_gamma(cs)
        i0 = fp.names.index("area_東京23区")
        lrs = max(0, 2 * (fg.loglik - fp.loglik))
        sim.append(dict(true_theta=th, rep=r, theta_hat=fg.theta, p_lr=0.5 * chi2.sf(lrs, 1) if lrs > 0 else 1.0,
                        cover_naive=abs(fp.beta[i0] - true_tokyo) < 1.96 * fp.se[i0],
                        cover_robust=abs(fp.beta[i0] - true_tokyo) < 1.96 * fp.se_robust[i0],
                        cover_frailty=abs(fg.beta[i0] - true_tokyo) < 1.96 * fg.se[i0]))
sim = pd.DataFrame(sim); sim.to_csv(RES / "simulation.csv", index=False)
ss = sim.groupby("true_theta").agg(theta_mean=("theta_hat", "mean"), theta_q10=("theta_hat", lambda x: x.quantile(.1)), theta_q90=("theta_hat", lambda x: x.quantile(.9)),
                                   reject=("p_lr", lambda p: (p < 0.05).mean()), cover_naive=("cover_naive", "mean"),
                                   cover_robust=("cover_robust", "mean"), cover_frailty=("cover_frailty", "mean")).reset_index()
ss.to_csv(RES / "simulation_summary.csv", index=False)
print(ss.round(3).to_string())
json.dump(dict(kind_heterogeneity=het, simulation=ss.to_dict("records")), open(RES / "robustness.json", "w"), ensure_ascii=False, indent=1, default=float)
