"""F04 東京の途中参加（2020年10月1日〜）を使った比較（差の差）。
結果：log(2020年の月の日本人延べ宿泊者数 ÷ 2019年の同じ月)。7〜9月は東京だけ対象外、10〜11月は全都道府県が対象。
12月は途中から一時停止が入るので除く。推定の幅は、東京の代わりに他の46道府県を「処置」とみなす置き換え（プラセボ）で評価。"""
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from common import panel, RES, PREFS

d = panel()
d = d[d.pref != "全国"]
p19 = d[d.date.dt.year == 2019][["pref", "date", "japanese"]].assign(month=lambda x: x.date.dt.month)
p20 = d[d.date.dt.year == 2020].assign(month=lambda x: x.date.dt.month)
g = p20.merge(p19[["pref", "month", "japanese"]].rename(columns={"japanese": "jp19"}), on=["pref", "month"])
g["g"] = np.log(g.japanese / g.jp19)
g[["pref", "month", "japanese", "jp19", "g", "x_cases"]].to_csv(RES / "did_panel_2020.csv", index=False, float_format="%.5f")

# 月ごとの「東京 − 他46道府県の平均」と、プラセボ（各県 − 残り46の平均）の幅
W = g.pivot(index="month", columns="pref", values="g")
gap = {p: W[p] - W.drop(columns=p).mean(axis=1) for p in PREFS}
es = pd.DataFrame({"tokyo_minus_others": gap["東京"]})
pl = pd.DataFrame({p: v for p, v in gap.items() if p != "東京"})
es["placebo_lo"], es["placebo_hi"] = pl.quantile(.025, axis=1), pl.quantile(.975, axis=1)
es["tokyo_rank_low"] = [(pl.loc[m] < es.loc[m, "tokyo_minus_others"]).sum() + 1 for m in es.index]
es.to_csv(RES / "did_event_study.csv", float_format="%.5f")


def did(df, treat, months=(7, 8, 9, 10, 11), post=(10, 11), cases=False):
    s = df[df.month.isin(months)].copy()
    s["D"] = ((s.pref == treat) & s.month.isin(post)).astype(int)
    f = "g ~ D + C(pref) + C(month)" + (" + x_cases" if cases else "")
    return smf.ols(f, s).fit().params["D"]


rows = []
for lab, kw in [("基本（7〜11月、7〜9月が前・10〜11月が後）", {}), ("陽性者数（log）を調整", dict(cases=True)),
                ("前を9月だけ", dict(months=(9, 10, 11))), ("後を10月だけ", dict(months=(7, 8, 9, 10), post=(10,))),
                ("12月も後に含める", dict(months=(7, 8, 9, 10, 11, 12), post=(10, 11, 12)))]:
    est = did(g, "東京", **kw)
    plc = np.array([did(g, p, **kw) for p in PREFS if p != "東京"])
    rows.append(dict(spec=lab, delta=est, pct=(np.exp(est) - 1) * 100, placebo_lo=np.quantile(plc, .025), placebo_hi=np.quantile(plc, .975),
                     rank_from_top=int((plc > est).sum() + 1), n_placebo=len(plc), p_perm=((np.abs(plc) >= abs(est)).sum() + 1) / (len(plc) + 1)))
r = pd.DataFrame(rows)
r.to_csv(RES / "did_tokyo.csv", index=False, float_format="%.5f")
print(es.round(3).to_string()); print(r.round(4).to_string())
