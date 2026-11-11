"""05 問い直し（結果を見た後に追加）：65〜74歳の鈍りは「時期」のせいか「生まれ年（世代）」のせいか。
各歳 50〜89歳、5年の改善率 r5(x,t)=−(ln m(x,t)−ln m(x,t−5))/5 を 1995〜2019年について作り、
「年齢＋時期」と「年齢＋生まれ年」の2つの式の当てはまり（R²）を比べる。生まれ年ごとの平均（年齢をそろえた後）も出す。"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, SEXES

s1 = pd.read_csv(DATA / "single_mx.csv")
s1 = s1[(s1.age >= 45) & (s1.age <= 89)]
lm = s1.pivot_table(index=["sex", "age"], columns="year", values="mx").apply(np.log)
rows = []
for (s, a), row in lm.iterrows():
    for t in range(1995, 2020):
        rows.append({"sex": s, "age": a, "year": t, "cohort": t - a, "r5": -(row[t] - row[t - 5]) / 5 * 100})
d = pd.DataFrame(rows); d = d[d.age >= 50]
d.to_csv(RES / "F_reask_r5_single.csv", index=False)


def _unused(df, f):
    X = pd.get_dummies(df[f].astype(str), drop_first=False).astype(float).values
    y = df.r5.values
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ b
    return 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum(), X.shape[1]


out = {}
coh = []
for s in SEXES:
    u = d[d.sex == s].copy()
    u["age_s"] = u.age; u["per"] = u.year; u["coh"] = u.cohort
    # 年齢＋時期 / 年齢＋生まれ年（ダミーを並べて最小二乗）
    def fit(cols):
        X = pd.concat([pd.get_dummies(u[c].astype(str), prefix=c) for c in cols], axis=1).astype(float).values
        y = u.r5.values
        b, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ b
        r2 = float(1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()); k = int(np.linalg.matrix_rank(X)); n = len(y)
        return r2, k, float(1 - (1 - r2) * (n - 1) / (n - k))
    ra, ka, aa = fit(["age_s"]); rap, kap, aap = fit(["age_s", "per"]); rac, kac, aac = fit(["age_s", "coh"])
    out[s] = {"R2_age": round(ra, 3), "R2_age_period": round(rap, 3), "R2_age_cohort": round(rac, 3),
              "adjR2_age_period": round(aap, 3), "adjR2_age_cohort": round(aac, 3),
              "rank_age_period": kap, "rank_age_cohort": kac, "n": int(len(u))}
    # 年齢ごとの平均を引いた残りを生まれ年で平均（65〜74歳で見たとき）
    u["dev"] = u.r5 - u.groupby("age").r5.transform("mean")
    c = u[(u.age >= 60) & (u.age <= 79)].groupby("cohort").dev.agg(["mean", "count"]).reset_index()
    c["sex"] = s; coh.append(c)
coh = pd.concat(coh); coh.to_csv(RES / "F_reask_cohort_dev.csv", index=False)
# 65〜74歳の改善率を、生まれ年の区分で比べる（同じ年齢・同じ時期の幅の中で）
tab = d[(d.age >= 65) & (d.age <= 74)].copy()
tab["cgrp"] = pd.cut(tab.cohort, [1920, 1935, 1940, 1945, 1950, 1955], right=False, labels=["1921〜34", "1935〜39", "1940〜44", "1945〜49", "1950〜54"])
out["r5_65_74_by_cohort"] = {s: {str(k): round(v, 2) for k, v in tab[tab.sex == s].groupby("cgrp", observed=True).r5.mean().items()} for s in SEXES}
(RES / "reask.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
print(coh[coh.cohort.between(1925, 1960)].pivot_table(index="cohort", columns="sex", values="mean").round(2).to_string())
