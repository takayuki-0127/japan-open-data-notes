"""06 独立レビューへの対応（レビュー後に追加）。
(a) R2 の取り扱い：計画の「2011年を除き前後の年で補間」と、記事で使った直線の傾き（2011年を除く／含む）
(b) H3 の基準直線から2011年を除いたときの上振れ
(c) 問い直しの式の比較：両端の生まれ年（観測数の少ない年）を除いた当てはまり
(d) 65〜69歳の10年の改善率と、生まれ年の区分の5年改善率の関係
(e) 高い年齢のデータの性質（死亡数が小数の割合）
(f) 地図：2000年代の65歳以上の改善率の幅、Arriaga 2019→2024 の寄与（70歳以上）"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, SEXES, GLABEL, GSTART

g = pd.read_csv(DATA / "group_mx.csv")
s1 = pd.read_csv(DATA / "single_mx.csv")
lm = g.pivot_table(index=["sex", "g"], columns="year", values="mx").apply(np.log)
out = {}
G = {l: i for i, l in enumerate(GLABEL)}


def slope(y0, y1, drop=(), interp=False):
    yrs = list(range(y0, y1 + 1)); m = lm[yrs].copy()
    if interp:
        for d in drop:
            m[d] = (m[d - 1] + m[d + 1]) / 2
        use = yrs
    else:
        use = [y for y in yrs if y not in drop]
    X = np.array(use, float)
    return pd.Series({k: -np.polyfit(X, r[use].values, 1)[0] * 100 for k, r in m.iterrows()})


# (a)
lm_i = lm.copy(); lm_i[2011] = (lm[2010] + lm[2012]) / 2
end_interp = -(lm_i[2019] - lm_i[2009]) / 10 * 100
end_base = -(lm[2019] - lm[2009]) / 10 * 100
b_no = slope(2010, 2019, drop=(2011,)); b_in = slope(2010, 2019); b_ip = slope(2010, 2019, drop=(2011,), interp=True)
a_ols = slope(2000, 2009)
ra = pd.DataFrame({"B_end": end_base, "B_end_interp2011": end_interp, "B_ols_no2011": b_no, "B_ols_with2011": b_in,
                   "B_ols_interp2011": b_ip, "A_ols": a_ols}).reset_index()
ra.columns = ["sex", "g"] + list(ra.columns[2:])
ra["label"] = ra.g.map(lambda i: GLABEL[i]); ra["age0"] = ra.g.map(lambda i: GSTART[i])
ra.to_csv(RES / "G_review_r2_variants.csv", index=False)
o40 = ra[ra.age0 >= 40]
out["a_end_interp_max_absdiff"] = round(float((ra.B_end - ra.B_end_interp2011).abs().max()), 6)
out["a_n_slow_40plus_ols_with2011"] = {s: int((o40[o40.sex == s].B_ols_with2011 < o40[o40.sex == s].A_ols).sum()) for s in SEXES}
out["a_n_slow_40plus_ols_interp2011"] = {s: int((o40[o40.sex == s].B_ols_interp2011 < o40[o40.sex == s].A_ols).sum()) for s in SEXES}
out["a_65_74_90_99"] = {s: {r.label: {"no2011": round(r.B_ols_no2011, 2), "with2011": round(r.B_ols_with2011, 2), "interp": round(r.B_ols_interp2011, 2), "A_ols": round(r.A_ols, 2)}
                            for r in ra[(ra.sex == s) & ra.age0.isin([65, 70, 90, 95])].itertuples()} for s in SEXES}
both = {}
for s in SEXES:
    u = o40[o40.sex == s]
    both[s] = {"with2011_slow_65_74": bool(((u.age0.isin([65, 70])) & (u.B_ols_with2011 < u.A_ols)).sum() == 2)}
out["a_65_74_slow_with2011"] = both


# (b)
def excess(drop=()):
    yrs = [y for y in range(2010, 2020) if y not in drop]; X = np.array(yrs, float); rows = []
    for k, r in lm.iterrows():
        b, a = np.polyfit(X, r[yrs].values, 1)
        rows.append({"sex": k[0], "g": k[1], "ex": float(np.mean([np.exp(r[y] - (a + b * y)) - 1 for y in (2022, 2023, 2024)]) * 100)})
    return pd.DataFrame(rows).set_index(["sex", "g"]).ex
e0, e1 = excess(), excess((2011,))
d = pd.DataFrame({"base": e0, "no2011": e1}).reset_index(); d["label"] = d.g.map(lambda i: GLABEL[i]); d["age0"] = d.g.map(lambda i: GSTART[i])
d["diff"] = d.no2011 - d.base
d.to_csv(RES / "G_review_h3_no2011.csv", index=False)
o75 = d[d.age0 >= 75]
out["b_h3_no2011"] = {s: {r.label: round(r.no2011, 2) for r in o75[o75.sex == s].itertuples()} for s in SEXES}
out["b_absdiff_75plus"] = [round(float(o75["diff"].abs().min()), 2), round(float(o75["diff"].abs().max()), 2)]
out["b_verdict_no2011"] = bool(all(o75[o75.sex == s].no2011.min() >= 5 for s in SEXES))

# (c)
r5 = pd.read_csv(RES / "F_reask_r5_single.csv")
cres = {}
for s in SEXES:
    u = r5[r5.sex == s].copy()
    cnt = u.cohort.value_counts()
    cres[s] = {"n_cohorts": int(cnt.size), "min_count": int(cnt.min()), "cohort_min_count": int(cnt.idxmin())}
    for thr in (10, 20):
        v = u[u.cohort.map(cnt) >= thr]

        def fit(cols):
            X = pd.concat([pd.get_dummies(v[c].astype(str), prefix=c) for c in cols], axis=1).astype(float).values
            y = v.r5.values; b, *_ = np.linalg.lstsq(X, y, rcond=None); res = y - X @ b
            r2 = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum(); k = np.linalg.matrix_rank(X); n = len(y)
            return round(float(1 - (1 - r2) * (n - 1) / (n - k)), 3), int(k)
        (ap, kp), (ac, kc) = fit(["age", "year"]), fit(["age", "cohort"])
        cres[s][f"min{thr}"] = {"n": int(len(v)), "cohorts": f"{int(v.cohort.min())}〜{int(v.cohort.max())}",
                                "adjR2_age_period": ap, "adjR2_age_cohort": ac, "k_period": kp, "k_cohort": kc}
out["c_reask_edge"] = cres

# (d)
rq = json.loads((RES / "reask.json").read_text())["r5_65_74_by_cohort"]
dd = {}
for s in SEXES:
    gi = G["65〜69"]
    r1 = float(-(lm.loc[(s, gi), 2014] - lm.loc[(s, gi), 2009]) / 5 * 100)
    r2 = float(-(lm.loc[(s, gi), 2019] - lm.loc[(s, gi), 2014]) / 5 * 100)
    dd[s] = {"r_65_69_2009_14": round(r1, 2), "r_65_69_2014_19": round(r2, 2),
             "B_65_69": round(float(end_base.loc[(s, gi)]), 2),
             "avg_cohortgrp_1945_49_1950_54": round((rq[s]["1945〜49"] + rq[s]["1950〜54"]) / 2, 2)}
out["d_65_69"] = dd

# (e)
raw = s1
frac = (raw.deaths % 1 != 0)
out["e_frac_deaths_all"] = round(float(frac.mean()), 3)
out["e_frac_deaths_90plus_2000on"] = round(float(frac[(raw.age >= 90) & (raw.year >= 2000)].mean()), 3)
out["e_frac_deaths_2000on"] = round(float(frac[raw.year >= 2000].mean()), 3)

# (f)
A = pd.read_csv(RES / "A_rates_by_age.csv")
out["f_A_65_89"] = {s: [round(float(A[(A.sex == s) & A.age0.between(65, 85)].A_2000_09.min()), 2), round(float(A[(A.sex == s) & A.age0.between(65, 85)].A_2000_09.max()), 2)] for s in SEXES}
C = pd.read_csv(RES / "C_rolling10.csv"); C["age0"] = C.g.map(lambda i: GSTART[i])
cc = C[C.age0.between(65, 85) & C.end.between(1985, 2009)]
out["f_roll_65_89_1985_2009"] = {s: [round(float(cc[cc.sex == s].rate.quantile(q)), 2) for q in (0.1, 0.5, 0.9)] for s in SEXES}
D = pd.read_csv(RES / "D_arriaga.csv"); D["age0"] = D.g.map(lambda i: GSTART[i])
dz = D[(D.period == "2019→2024") & (D.age0 >= 60)]
out["f_arriaga_2019_24"] = {s: {r.label: round(r.contrib, 3) for r in dz[dz.sex == s].itertuples()} for s in SEXES}
B3 = json.loads((RES / "main.json").read_text())
out["g_h3_r3"] = B3["H3_R3"]
(RES / "review.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(json.dumps(out, ensure_ascii=False, indent=1))
