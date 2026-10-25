"""F04 全国：Go To 期間（2020年7〜12月）の日本人延べ宿泊者数を、ベイズ構造時系列の反実仮想と比べる（基本＋頑健性）"""
import numpy as np, pandas as pd, json
from common import national, RES, GOTO, CORE
from bsts import fit_bsts, summarize, cum

n = national()
target = GOTO
act_y = n.loc[target, "y"].values
days = n.loc[target, "days"].values.astype(float)
act = n.loc[target, "japanese"].values.astype(float)
core = np.isin(target, CORE)
nodec = target < pd.Timestamp("2020-12-01")
R = lambda a, b: pd.date_range(a, b, freq="MS")
VARIANTS = {
    "基本：2015年1月〜2020年6月で学習、共変量＝陽性者数＋緊急事態宣言": dict(train=R("2015-01", "2020-06"), cov=("x_cases", "emerg")),
    "学習を2011年1月から": dict(train=R("2011-01", "2020-06"), cov=("x_cases", "emerg")),
    "学習を2017年1月から": dict(train=R("2017-01", "2020-06"), cov=("x_cases", "emerg")),
    "共変量を陽性者数だけに": dict(train=R("2015-01", "2020-06"), cov=("x_cases",)),
    "学習に2021年（Go Toなし）も加える": dict(train=R("2015-01", "2020-06").append(R("2021-01", "2021-12")), cov=("x_cases", "emerg")),
    "参考：コロナ前（2015〜2019年）だけで学習、共変量なし": dict(train=R("2015-01", "2019-12"), cov=()),
}
rows, monthly, diag = [], [], {}
for k, v in VARIANTS.items():
    ycf, dg, beta = fit_bsts(n, v["train"], target, covars=v["cov"])
    sm, cf, eff = summarize(ycf, act_y, days, target)
    sm.insert(0, "variant", k); monthly.append(sm)
    for lab, msk in [("2020年7〜12月", np.ones(len(target), bool)), ("2020年8〜11月", core), ("2020年7〜11月（12月を除く）", nodec)]:
        rows.append(dict(variant=k, period=lab, **cum(eff, cf, act, msk)))
    dg["beta_mean"] = beta.mean(0).round(3).tolist(); dg["beta_q"] = np.quantile(beta, [.025, .975], axis=0).round(3).tolist() if beta.shape[1] else []
    diag[k] = dg
    print(k, dg, [f"{r['period']} {r['eff_med']/1e4:.0f}万[{r['eff_lo']/1e4:.0f},{r['eff_hi']/1e4:.0f}] {r['pct_med']:+.1f}%" for r in rows[-3:]], flush=True)
    if k.startswith("基本"):
        np.save(RES / "_base_cf.npy", cf)
pd.DataFrame(rows).to_csv(RES / "bsts_cumulative.csv", index=False, float_format="%.4f")
pd.concat(monthly).to_csv(RES / "bsts_monthly.csv", index=False, float_format="%.4f")
json.dump(diag, open(RES / "bsts_diagnostics.json", "w"), ensure_ascii=False, indent=1)
