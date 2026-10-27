"""Kaplan–Meier・Cox 比例ハザード・比例ハザードの確認・頑健性"""
import json, numpy as np, pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import proportional_hazard_test, logrank_test
from common import DATA, RES, SEED

d = pd.read_parquet(DATA / "survival.parquet")
RES.mkdir(exist_ok=True)
out = {"n": int(len(d)), "events": int(d.E.sum())}
grid = np.arange(0, 10.6, 0.25)

def km(df, E="E"):
    k = KaplanMeierFitter().fit(df["T"], df[E])
    s = k.survival_function_at_times(grid).values
    ci = k.confidence_interval_
    lo = np.interp(grid, ci.index.values, ci.iloc[:, 0].values); hi = np.interp(grid, ci.index.values, ci.iloc[:, 1].values)
    return s, lo, hi

rows = []
for g, df in [("全体", d)] + list(d.groupby("kindj")):
    s, lo, hi = km(df)
    for t, a, b, c in zip(grid, s, lo, hi): rows.append(["種別", g, t, a, b, c])
for g, df in d.groupby("cohort"):
    s, lo, hi = km(df)
    for t, a, b, c in zip(grid, s, lo, hi): rows.append(["設立年", str(g), t, a, b, c])
for g, df in d.groupby("area"):
    s, lo, hi = km(df)
    for t, a, b, c in zip(grid, s, lo, hi): rows.append(["地域", g, t, a, b, c])
kmdf = pd.DataFrame(rows, columns=["by", "group", "t", "S", "lo", "hi"])
kmdf.to_csv(RES / "km_curves.csv", index=False)
def at(by, g, t): return float(kmdf[(kmdf.by == by) & (kmdf.group == g) & (np.isclose(kmdf.t, t))].S.iloc[0])
out["S5"] = {g: round(at("種別", g, 5), 4) for g in ["全体", "株式会社", "合同会社", "その他（一般社団・NPOなど）"]}
out["S10_all"] = round(at("種別", "全体", 10), 4)
out["S3_cohort"] = {str(c): round(at("設立年", str(c), 3), 4) for c in range(2016, 2024)}
out["S5_area"] = {g: round(at("地域", g, 5), 4) for g in d.area.unique()}

# 打ち切りを無視した「閉鎖した割合」と Kaplan–Meier の比較
out["naive_all"] = round(float(d.E.mean()), 4)
out["km_close10"] = round(1 - at("種別", "全体", 10), 4)
out["km_close5"] = round(1 - at("種別", "全体", 5), 4)
d5 = d[d.start <= pd.Timestamp("2021-09-30")]          # 5年以上観察できる法人だけで数えた5年以内の閉鎖割合
out["naive5_old"] = round(float(((d5["T"] <= 5) & (d5.E == 1)).mean()), 4)

# 1年ごとのハザード（年数ごとの閉鎖率）
haz = []
for kname, df in [("全体", d)] + list(d.groupby("kindj")):
    for y in range(0, 10):
        at_risk = df[df["T"] >= y]; ev = at_risk[(at_risk["T"] < y + 1) & (at_risk.E == 1)]
        haz.append([kname, y + 1, len(at_risk), len(ev), len(ev) / len(at_risk) if len(at_risk) else np.nan])
pd.DataFrame(haz, columns=["kind", "year", "at_risk", "events", "hazard"]).to_csv(RES / "yearly_hazard.csv", index=False)

# 都道府県別 5年生存率（集計のみ）
pref = []
for p, df in d.groupby("prefn"):
    k = KaplanMeierFitter().fit(df["T"], df.E)
    pref.append([int(p), len(df), float(k.survival_function_at_times(5).iloc[0])])
pd.DataFrame(pref, columns=["pref", "n", "S5"]).to_csv(RES / "pref_S5.csv", index=False)

# Cox（30万件の無作為抽出）
def prep(df):
    X = pd.get_dummies(df[["kindj", "region", "area"]], drop_first=False).astype(float)
    X = X.drop(columns=["kindj_株式会社", "region_関東", "area_その他の市町村"])
    X["cohort_c"] = df.cohort - 2020
    X["T"] = df["T"].clip(lower=1 / 365.25); X["E"] = df.E
    return X
cox = {}
for name, seed in [("base", SEED), ("seed2", SEED + 1)]:
    s = d.sample(300_000, random_state=seed)
    X = prep(s)
    m = CoxPHFitter(penalizer=0.0).fit(X, "T", "E")
    cox[name] = m.summary[["exp(coef)", "exp(coef) lower 95%", "exp(coef) upper 95%", "p"]].round(4)
    if name == "base":
        m.summary.to_csv(RES / "cox_summary.csv")
        ph = proportional_hazard_test(m, X, time_transform="rank")
        ph.summary.to_csv(RES / "ph_test.csv")
        out["ph_test"] = ph.summary["p"].round(4).to_dict()
        mbase = m
out["cox"] = {k: v["exp(coef)"].to_dict() for k, v in cox.items()}
out["cox_ci"] = cox["base"][["exp(coef) lower 95%", "exp(coef) upper 95%"]].to_dict("index")

# 比例ハザード: 合同会社/株式会社 のハザード比を期間で分けて推定
pw = []
for a, b in [(0, 1), (1, 3), (3, 6), (6, 11)]:
    s = d.sample(300_000, random_state=SEED)
    s = s[s["T"] > a].copy(); s["E2"] = ((s.E == 1) & (s["T"] <= b)).astype(int); s["T2"] = s["T"].clip(upper=b) - a
    X = pd.get_dummies(s[["kindj"]]).astype(float).drop(columns=["kindj_株式会社"]); X["cohort_c"] = s.cohort - 2020
    X["T"] = s.T2.clip(lower=1 / 365.25); X["E"] = s.E2
    m = CoxPHFitter().fit(X, "T", "E")
    for k in ["kindj_合同会社", "kindj_その他（一般社団・NPOなど）"]:
        r = m.summary.loc[k]; pw.append([f"{a}-{b}年", k.replace("kindj_", ""), r["exp(coef)"], r["exp(coef) lower 95%"], r["exp(coef) upper 95%"]])
pd.DataFrame(pw, columns=["period", "kind", "HR", "lo", "hi"]).to_csv(RES / "hr_by_period.csv", index=False)
out["hr_by_period"] = pw

# 頑健性
rb = []
s = d.sample(300_000, random_state=SEED)
def hr(X): 
    m = CoxPHFitter().fit(X, "T", "E"); r = m.summary.loc["kindj_合同会社"]; return [r["exp(coef)"], r["exp(coef) lower 95%"], r["exp(coef) upper 95%"]]
X = prep(s); rb.append(["基本（清算結了・登記官閉鎖＝消えた）", *hr(X), float(KaplanMeierFitter().fit(s["T"], s.E).survival_function_at_times(5).iloc[0])])
s2 = s.copy(); s2["E"] = s2.E_merge; X = prep(s2); rb.append(["合併による解散も「消えた」に含める", *hr(X), float(KaplanMeierFitter().fit(s2["T"], s2.E).survival_function_at_times(5).iloc[0])])
s3 = s.copy(); s3["E"] = (s3.cause == "01").astype(int); X = prep(s3); rb.append(["清算結了だけ", *hr(X), float(KaplanMeierFitter().fit(s3["T"], s3.E).survival_function_at_times(5).iloc[0])])
s4 = s[s.cohort <= 2019]; X = prep(s4); rb.append(["2019年までの設立だけ", *hr(X), float(KaplanMeierFitter().fit(s4["T"], s4.E).survival_function_at_times(5).iloc[0])])
s5 = s.copy(); s5 = s5[s5["T"] >= 1]; s5["T"] = s5["T"] - 1; X = prep(s5); rb.append(["1年目に消えた法人を除く（1年後から数える）", *hr(X), np.nan])
X = prep(s); X = X.drop(columns=[c for c in X.columns if c.startswith("region_") or c.startswith("area_")]); rb.append(["地域を入れない", *hr(X), np.nan])
pd.DataFrame(rb, columns=["setting", "HR_GK", "lo", "hi", "S5_all"]).round(4).to_csv(RES / "robustness.csv", index=False)
out["robust"] = rb

# 全法人の年別の新規・閉鎖
y = pd.read_csv(DATA / "raw" / "houjin_yearly_counts.csv", dtype={"cause": str, "kind": str})
yy = y[y.type.isin(["new", "close"])].copy(); yy["year"] = yy.year.astype(int)
t = yy[yy.kind.isin(["301", "305", "399"])].pivot_table(index="year", columns=["type"], values="n", aggfunc="sum").fillna(0)
cz = yy[(yy.type == "close")].pivot_table(index="year", columns="cause", values="n", aggfunc="sum").fillna(0)
t.join(cz, rsuffix="_c").to_csv(RES / "yearly_counts.csv")
out["yearly"] = t.loc[2016:2025].astype(int).to_dict()
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["n", "events", "S5", "S10_all", "S3_cohort", "S5_area", "naive_all", "km_close5", "km_close10", "naive5_old", "ph_test"]}, ensure_ascii=False, indent=0, default=float))
print(cox["base"]); print(pd.DataFrame(pw)); print(pd.DataFrame(rb))
