"""問い直し（結果を見てから足した）：
新しい契約（2021〜23年に入居）の上乗せ +8 は、どの建築時期でも同じか。
建築時期ごとに、2021〜23年に入居した世帯と、2015年以前に入居した世帯（借家数で重みづけた平均）の1畳当たり家賃を比べる。
あわせて、入居の時期ごとに、建物の古さによる下がり方（1年当たり）を推定する。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
r3 = lambda x: round(float(x), 3)
z = pd.read_csv(RES / "t27_private_cells.csv")
rows = []
for c, g in z.groupby("construction", sort=False):
    a = g[g.mv == "2021〜23年"]; o = g[g.mv == "2015年以前"]
    if len(a) and len(o):
        lo = np.average(o.lr, weights=o.n)
        rows.append(dict(construction=c, age=r3(a.age.iloc[0]), new_rent=float(a.rent.iloc[0]), old_rent_wavg=r3(np.exp(lo / 100)), premium=r3(a.lr.iloc[0] - lo), n_new=int(a.n.iloc[0]), n_old=int(o.n.sum())))
p = pd.DataFrame(rows).sort_values("age"); p.to_csv(RES / "requestion_premium_by_construction.csv", index=False)
sl = {}
for mv, g in z.groupby("mv"):
    m = sm.WLS(g.lr, sm.add_constant(g[["age"]]), weights=g.n).fit(cov_type="HC3")
    sl[mv] = dict(slope=r3(m.params["age"]), se=r3(m.bse["age"]), n_cells=int(len(g)))
X = sm.add_constant(pd.DataFrame({"age": p.age}))
mm = sm.WLS(p.premium, X, weights=p.n_new).fit(cov_type="HC3")
out = dict(premium_by_construction=p.set_index("construction").premium.to_dict(), premium_trend_per_year_age=r3(mm.params["age"]), premium_trend_se=r3(mm.bse["age"]),
           slope_by_movein=sl, premium_min=r3(p.premium.min()), premium_max=r3(p.premium.max()))
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0)); print(p.to_string())
