"""F04 都道府県別：構造時系列（ローカルレベル＋季節＋全国の陽性者数・緊急事態宣言）を県ごとに当てはめる簡易版。
計算を軽くするため、PyMC ではなく statsmodels（カルマンフィルタ・最尤推定）で推定し、予測区間はシミュレーションで作る。
共変量は宿泊する側の動きを表すものとして全国の値を使う（県内の陽性者数ではなく）。学習 2015年1月〜2020年6月、比べる期間は 2020年8〜11月（東京は10〜11月だけ対象）。"""
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import panel, RES, PREFS, SEED, GOTO, CORE

d = panel()
rng = np.random.default_rng(SEED)
nat = d[d.pref == "全国"].set_index("date")[["x_cases", "emerg"]]
rows = []
for p in ["全国"] + PREFS:
    s = d[d.pref == p].set_index("date").asfreq("MS").loc["2015-01":"2020-12"].drop(columns=["x_cases", "emerg"]).join(nat)
    tr = s.loc[:"2020-06"]
    te = s.loc[GOTO]
    X = ["x_cases", "emerg"]
    mod = sm.tsa.UnobservedComponents(tr.y, level="llevel", freq_seasonal=[{"period": 12, "harmonics": 6}], exog=tr[X])
    fit = mod.fit(disp=False, maxiter=500)
    sims = fit.simulate(nsimulations=len(te), repetitions=2000, anchor="end", exog=te[X]).values.reshape(len(te), -1)
    cf = np.exp(sims) * te.days.values[:, None]
    act = te.japanese.values
    msk = np.isin(te.index, CORE) if p != "東京" else te.index.isin(pd.to_datetime(["2020-10-01", "2020-11-01"]))
    ratio = act[msk].sum() / cf[msk].sum(0) - 1
    rows.append(dict(pref=p, period="10〜11月" if p == "東京" else "8〜11月", eff_pct_med=np.median(ratio) * 100, eff_pct_lo=np.quantile(ratio, .025) * 100,
                     eff_pct_hi=np.quantile(ratio, .975) * 100, eff_nights_med=np.median(act[msk].sum() - cf[msk].sum(0)),
                     vs2019_pct=(act[msk].sum() / s.loc[te.index[msk] - pd.DateOffset(years=1), "japanese"].sum() - 1) * 100,
                     beta_cases=fit.params.get("beta.x_cases", np.nan), beta_emerg=fit.params.get("beta.emerg", np.nan)))
r = pd.DataFrame(rows)
r.to_csv(RES / "pref_effect.csv", index=False, float_format="%.4f")
q = r[r.pref != "全国"]
print(r[r.pref == "全国"].round(2).to_string())
print(q.eff_pct_med.describe().round(1).to_string())
print(q.sort_values("eff_pct_med", ascending=False)[["pref", "eff_pct_med", "eff_pct_lo", "eff_pct_hi", "vs2019_pct"]].round(1).to_string())
print("corr(effect, vs2019)", np.corrcoef(q.eff_pct_med, q.vs2019_pct)[0, 1].round(2), "lo>0:", (q.eff_pct_lo > 0).sum())
