"""副業がある人の割合を、属性の組み合わせで説明する（集計表のログリニアモデル＝グループ化したロジット）。
入力: data/side_job_long.csv
出力: results/*.csv, results/summary.json
注: 公表値は復元倍率をかけた推計人口（100人単位）。標本の人数に戻すため、推計人口を SCALE（既定100）で割って
    二項モデルの重みにする（推測：1標本あたりおよそ100人分。頑健性で50・200も試す）。逸脱度の「割合」は SCALE によらない。
"""
import json, itertools
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

np.random.seed(139)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"; OUT.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "side_job_long.csv")

INC_ORDER = sorted(df.income.unique())
def inc_group(s):
    c = int(s.split("_")[0])
    return {1: "1_100万円未満", 2: "1_100万円未満", 3: "2_100〜199万円", 4: "2_100〜199万円", 5: "3_200〜299万円", 6: "3_200〜299万円",
            7: "4_300〜499万円", 8: "4_300〜499万円", 9: "5_500〜699万円", 10: "5_500〜699万円"}.get(c, "6_700万円以上")
df["inc6"] = df.income.map(inc_group)
EMP_ORDER = ["正規", "非正規", "役員", "自営業主など"]
AGE_ORDER = sorted(df.age.unique())

def wide(d, keys):
    g = d.groupby(keys + ["side"]).n.sum().unstack("side").fillna(0)
    g["N"] = g["副業あり"] + g["副業なし"]
    g = g[g.N > 0].reset_index()
    g["p"] = g["副業あり"] / g.N
    return g

def fit(g, rhs, scale=100.0):
    m = smf.glm("p ~ " + rhs, data=g, family=sm.families.Binomial(), var_weights=g.N / scale).fit()
    return m

def dissim(g, m):
    e1 = m.fittedvalues * g.N; o1 = g["副業あり"]
    return float((np.abs(o1 - e1).sum() * 2) / (2 * g.N.sum()))

summary = {}
REF = "C(sex, Treatment('男')) + C(age, Treatment('35〜44歳')) + C(emp, Treatment('正規')) + C(inc6, Treatment('4_300〜499万円'))"
FACT = {"sex": "C(sex, Treatment('男'))", "age": "C(age, Treatment('35〜44歳'))", "emp": "C(emp, Treatment('正規'))",
        "inc6": "C(inc6, Treatment('4_300〜499万円'))"}

# ---------- 1. 属性ごとの副業の割合（粗い率） ----------
crude = []
base = df[df.hours == "総数"]
for y in (2017, 2022):
    d = base[base.year == y]
    for var in ["sex", "age", "emp", "inc6", "income"]:
        g = wide(d, [var])
        for _, r in g.iterrows():
            crude.append(dict(year=y, var=var, level=r[var], rate=r.p, N=r.N, side=r["副業あり"]))
    summary[f"rate_{y}"] = float(d[d.side == "副業あり"].n.sum() / d.n.sum())
crude = pd.DataFrame(crude); crude.to_csv(OUT / "crude_rates.csv", index=False)

# ---------- 2. 年ごとのモデル比較 ----------
models = []; ors = []
for y in (2017, 2022):
    g = wide(base[base.year == y], ["sex", "age", "emp", "inc6"])
    m0 = fit(g, "1"); D0 = m0.deviance
    res = {"M0 切片だけ": m0}
    for v in FACT:
        res[f"M1 {v}だけ"] = fit(g, FACT[v])
    m1 = fit(g, REF); res["M2 4属性の主効果"] = m1
    pair_gain = {}
    for a, b in itertools.combinations(FACT, 2):
        mm = fit(g, REF + f" + {FACT[a]}:{FACT[b]}")
        pair_gain[f"{a}×{b}"] = mm
    best = max(pair_gain, key=lambda k: (m1.deviance - pair_gain[k].deviance))
    for k, mm in pair_gain.items():
        res[f"M3 主効果＋{k}"] = mm
    allpairs = " + ".join(f"{FACT[a]}:{FACT[b]}" for a, b in itertools.combinations(FACT, 2))
    res["M4 主効果＋2属性の組み合わせすべて"] = fit(g, REF + " + " + allpairs)
    for k, mm in res.items():
        models.append(dict(year=y, model=k, deviance=mm.deviance, df_resid=mm.df_resid, aic=mm.aic,
                           dev_explained=1 - mm.deviance / D0, dissimilarity=dissim(g, mm)))
    summary[f"best_pair_{y}"] = best
    # オッズ比（主効果モデル）と粗いオッズ比
    tot_p = g["副業あり"].sum() / g.N.sum()
    for name, coef in m1.params.items():
        if name == "Intercept": continue
        ci = m1.conf_int().loc[name]
        var = [v for v in FACT if FACT[v] in name][0]
        lev = name.split("[T.")[1].rstrip("]")
        ors.append(dict(year=y, var=var, level=lev, OR=np.exp(coef), lo=np.exp(ci[0]), hi=np.exp(ci[1]), kind="調整"))
    for var in FACT:
        gg = wide(base[base.year == y], [var])
        refl = {"sex": "男", "age": "35〜44歳", "emp": "正規", "inc6": "4_300〜499万円"}[var]
        pr = gg.set_index(var).p
        for lev, p in pr.items():
            if lev == refl: continue
            ors.append(dict(year=y, var=var, level=lev, OR=(p / (1 - p)) / (pr[refl] / (1 - pr[refl])), lo=np.nan, hi=np.nan, kind="粗い"))
models = pd.DataFrame(models); models.to_csv(OUT / "model_comparison.csv", index=False)
ors = pd.DataFrame(ors); ors.to_csv(OUT / "odds_ratios.csv", index=False)

# ---------- 3. 所得×雇用形態の率（2022） ----------
ie = wide(base, ["year", "emp", "inc6"]); ie.to_csv(OUT / "rate_emp_income.csv", index=False)
ia = wide(base, ["year", "sex", "age"]); ia.to_csv(OUT / "rate_sex_age.csv", index=False)

# ---------- 4. 2017→2022 の変化：構成と率に分ける ----------
cells = ["sex", "age", "emp", "inc6"]
g17 = wide(base[base.year == 2017], cells).set_index(cells); g22 = wide(base[base.year == 2022], cells).set_index(cells)
J = g17.join(g22, lsuffix="_17", rsuffix="_22", how="outer").fillna(0)
w17 = J.N_17 / J.N_17.sum(); w22 = J.N_22 / J.N_22.sum()
p17 = J.p_17.fillna(0); p22 = J.p_22.fillna(0)
total = float((w22 * p22).sum() - (w17 * p17).sum())
within = float((0.5 * (w17 + w22) * (p22 - p17)).sum())
comp = float((0.5 * (p17 + p22) * (w22 - w17)).sum())
summary["change"] = dict(total_pt=100 * total, within_pt=100 * within, composition_pt=100 * comp)
# 年×属性の交互作用：どこで伸びたか（属性ごとに、年の効果を推定）
pool = wide(base, ["year"] + cells); pool["y22"] = (pool.year == 2022).astype(int)
mp = fit(pool, REF + " + y22")
summary["pooled_year_OR"] = float(np.exp(mp.params["y22"]))
chg = []
for v in FACT:
    mi = fit(pool, REF + f" + y22 + y22:{FACT[v]}")
    lr = mp.deviance - mi.deviance
    chg.append(dict(var=v, dev_drop=lr, df=mp.df_resid - mi.df_resid, share_of_main_dev=lr / mp.deviance))
    gg = wide(base, ["year", v])
    for lev in gg[v].unique():
        a = gg[(gg.year == 2017) & (gg[v] == lev)].p.values; b = gg[(gg.year == 2022) & (gg[v] == lev)].p.values
        chg.append(dict(var=v, level=lev, rate17=a[0], rate22=b[0], diff_pt=100 * (b[0] - a[0])))
pd.DataFrame(chg).to_csv(OUT / "change_by_group.csv", index=False)

# ---------- 5. 本業の就業時間を加える ----------
hrs = df[df.hours != "総数"]
hm = []
for y in (2017, 2022):
    gh = wide(hrs[hrs.year == y], cells + ["hours"])
    mA = fit(gh, REF)
    mB = fit(gh, REF + " + C(hours, Treatment('200日以上・週35〜59時間'))")
    m0 = fit(gh, "1")
    for name, coef in mB.params.items():
        if "hours" in name or "emp" in name:
            ci = mB.conf_int().loc[name]
            hm.append(dict(year=y, term=name, OR=np.exp(coef), lo=np.exp(ci[0]), hi=np.exp(ci[1])))
    hm.append(dict(year=y, term="逸脱度の説明割合（時間なし→あり）", OR=1 - mA.deviance / m0.deviance, lo=1 - mB.deviance / m0.deviance, hi=np.nan))
    gr = wide(hrs[hrs.year == y], ["hours"])
    for _, r in gr.iterrows():
        hm.append(dict(year=y, term="率:" + r.hours, OR=r.p, lo=r.N, hi=np.nan))
pd.DataFrame(hm).to_csv(OUT / "hours_model.csv", index=False)

# ---------- 6. 頑健性 ----------
rob = []
def emp_or(m, lev):
    k = [n for n in m.params.index if "emp" in n and lev in n][0]
    ci = m.conf_int().loc[k]; return np.exp(m.params[k]), np.exp(ci[0]), np.exp(ci[1])
for y in (2017, 2022):
    d = base[base.year == y]
    variants = {}
    g = wide(d, cells); variants["主（所得6区分・SCALE100）"] = (g, REF, 100)
    g16 = wide(d, ["sex", "age", "emp", "income"])
    variants["所得16区分"] = (g16, REF.replace("C(inc6, Treatment('4_300〜499万円'))", "C(income)"), 100)
    variants["SCALE 50"] = (g, REF, 50); variants["SCALE 200"] = (g, REF, 200)
    variants["75歳以上を除く"] = (wide(d[d.age != "75歳以上"], cells), REF, 100)
    variants["自営業主などを除く"] = (wide(d[d.emp != "自営業主など"], cells), REF, 100)
    gh = wide(hrs[hrs.year == y], cells + ["hours"])
    variants["本業の就業時間を加える"] = (gh, REF + " + C(hours)", 100)
    variants["2属性の組み合わせすべてを加える"] = (g, REF + " + " + " + ".join(f"{FACT[a]}:{FACT[b]}" for a, b in itertools.combinations(FACT, 2) if not (a == 'emp' or b == 'emp')), 100)
    for k, (gg, rhs, sc) in variants.items():
        m = fit(gg, rhs, sc)
        row = dict(year=y, variant=k)
        for lev in ["非正規", "役員", "自営業主など"]:
            try:
                o, lo, hi = emp_or(m, lev); row[f"OR_{lev}"] = o; row[f"lo_{lev}"] = lo; row[f"hi_{lev}"] = hi
            except IndexError:
                pass
        kf = [n for n in m.params.index if "sex" in n]
        row["OR_女"] = float(np.exp(m.params[kf[0]]))
        rob.append(row)
rob = pd.DataFrame(rob); rob.to_csv(OUT / "robustness.csv", index=False)

summary["models"] = models.to_dict("records")
json.dump(summary, open(OUT / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(json.dumps({k: v for k, v in summary.items() if k != "models"}, ensure_ascii=False, indent=1, default=float))
print(models[["year", "model", "dev_explained", "dissimilarity"]].round(4).to_string())
print(ors.round(3).to_string())
print(pd.DataFrame(chg).round(4).to_string())
print(pd.DataFrame(hm).round(4).to_string())
print(rob.round(3).to_string())
