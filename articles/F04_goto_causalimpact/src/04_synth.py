"""F04 合成コントロール：東京を、他の46道府県の重みつき平均（合成東京）と比べる。
値：log(1日あたり日本人延べ宿泊者数) − その県の2019年平均。重みは2015年1月〜2020年6月（Go To 前）で合わせる（非負・合計1）。
7〜9月は合成東京の側（他県）だけが Go To の対象、10〜11月は両方が対象。差が10月以降どれだけ縮んだかを見る。
推定の幅は、各道府県を「東京役」にした置き換え（プラセボ）で評価。"""
import numpy as np, pandas as pd
from scipy.optimize import minimize
from common import panel, RES, PREFS

d = panel()
d = d[(d.pref != "全国") & (d.date >= "2015-01-01") & (d.date <= "2020-12-01")]
Y = d.pivot(index="date", columns="pref", values="y")
Y = Y - Y.loc["2019"].mean()
pre = Y.index <= "2020-06-01"
JAS = Y.index.isin(pd.to_datetime(["2020-07-01", "2020-08-01", "2020-09-01"]))
ON = Y.index.isin(pd.to_datetime(["2020-10-01", "2020-11-01"]))


def synth(t, donors):
    A, b = Y.loc[pre, donors].values, Y.loc[pre, t].values
    k = len(donors)
    res = minimize(lambda w: ((A @ w - b) ** 2).sum(), np.full(k, 1 / k), method="SLSQP", bounds=[(0, 1)] * k,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"maxiter": 500, "ftol": 1e-12})
    w = res.x
    gap = Y[t] - Y[donors].values @ w
    rmspe_pre = np.sqrt((gap[pre] ** 2).mean())
    return w, gap, rmspe_pre


donors = [p for p in PREFS if p != "東京"]
w, gap_t, rm = synth("東京", donors)
wt = pd.Series(w, index=donors).sort_values(ascending=False)
wt[wt > 0.005].round(3).to_csv(RES / "synth_weights.csv", header=["weight"])
out = pd.DataFrame({"tokyo": Y["東京"], "synthetic": Y["東京"] - gap_t, "gap": gap_t})
out.to_csv(RES / "synth_tokyo_path.csv", float_format="%.5f")
change_t = gap_t[ON].mean() - gap_t[JAS].mean()
rows = []
for p in PREFS:
    if p == "東京":
        continue
    _, gp, rmp = synth(p, [q for q in PREFS if q not in (p, "東京")])
    rows.append(dict(pref=p, rmspe_pre=rmp, gap_jas=gp[JAS].mean(), gap_on=gp[ON].mean(), change=gp[ON].mean() - gp[JAS].mean()))
pl = pd.DataFrame(rows)
pl.to_csv(RES / "synth_placebo.csv", index=False, float_format="%.5f")
good = pl[pl.rmspe_pre <= 2 * rm]
summ = dict(rmspe_pre_tokyo=rm, gap_jun=float(gap_t.loc["2020-06-01"]), gap_jas=float(gap_t[JAS].mean()), gap_on=float(gap_t[ON].mean()), gap_dec=float(gap_t.loc["2020-12-01"]),
            change=float(change_t), change_pct=float((np.exp(change_t) - 1) * 100),
            placebo_lo=float(pl.change.quantile(.025)), placebo_hi=float(pl.change.quantile(.975)),
            rank_from_top=int((pl.change > change_t).sum() + 1), n=len(pl),
            rank_from_top_goodfit=int((good.change > change_t).sum() + 1), n_goodfit=len(good))
pd.Series(summ).to_csv(RES / "synth_summary.csv", header=["value"], float_format="%.5f")
print(wt.head(8).round(3).to_string()); print(out.loc["2020"].round(3).to_string()); print(pd.Series(summ).round(4).to_string())
