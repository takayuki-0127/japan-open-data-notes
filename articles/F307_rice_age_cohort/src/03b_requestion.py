"""問い直し（結果を見てから足した）：
事前に比べた「世代＋時代」は「年齢＋時代」に勝たなかったが、「年齢＋世代」（時代の分を置かない）が最もよく当てはまる組が多かった。
年ごと（2002〜2025年）の144のマスを使い、生まれ年（およその中央）を5年ごとにまとめて、
「年齢＋世代」と「年齢＋時代」の当てはまりを比べる。あわせて、生まれ年ごとの米の買い方（1人あたり）を年齢をそろえて並べる。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "grains_by_age.csv")
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
MID = {"29歳以下": 25, "30～39歳": 35, "40～49歳": 45, "50～59歳": 55, "60～69歳": 65, "70歳以上": 75}
r3 = lambda x: round(float(x), 3)
q = d[d.item == "rice"].pivot(index="year", columns="age", values="quantity")
hs = d[d.item == "hh_size"].pivot(index="year", columns="age", values="amount")
rows = []
for y in q.index:
    for a in AG:
        b = y - MID[a]
        rows.append(dict(year=int(y), age=a, birth_mid=int(b), cohort5=int(5 * np.floor(b / 5)), q=q.loc[y, a], pp=q.loc[y, a] / hs.loc[y, a]))
t = pd.DataFrame(rows); t["lq"] = np.log(t.q); t["lpp"] = np.log(t.pp)
t.round(4).to_csv(RES / "requestion_cells.csv", index=False)
out = {}
for var in ("lq", "lpp"):
    fit = lambda fm: smf.ols(fm.replace("Y", var), t).fit()
    # 世代＋時代 は1つの列が他の列の組み合わせになる（階数が1足りない）。AIC は実際の自由度で計算される
    ap = fit("Y ~ C(age) + C(year)"); ac = fit("Y ~ C(age) + C(cohort5)"); cp = fit("Y ~ C(cohort5) + C(year)")
    out[var] = dict(n=int(len(t)), aic_age_period=r3(ap.aic), aic_age_cohort=r3(ac.aic), aic_cohort_period=r3(cp.aic),
                    r2_age_period=r3(ap.rsquared), r2_age_cohort=r3(ac.rsquared), r2_cohort_period=r3(cp.rsquared),
                    df_age_period=int(ap.df_model), df_age_cohort=int(ac.df_model))
    if var == "lpp":
        co = ac.params.filter(like="cohort5")
        base = sorted(t.cohort5.unique())[0]
        eff = {int(base): 0.0}
        for k, v in co.items():
            eff[int(k.split("[T.")[1].rstrip("]"))] = float(v)
        out["cohort_effect_pp_log100"] = {str(k): r3(100 * v) for k, v in sorted(eff.items())}
# 同じ年齢（60〜69歳）で、生まれ年の違う世帯の1人あたりの量
s60 = t[t.age == "60～69歳"].set_index("year").pp
out["pp_60s"] = {str(y): r3(s60.loc[y]) for y in (2002, 2012, 2022, 2025)}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
