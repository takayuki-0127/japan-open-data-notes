"""競合リスクの生存分析：法人の「閉鎖」と「合併による解散」

1. Aalen–Johansen 法の累積発生関数（CIF）を、閉鎖・合併それぞれについて種別ごとに出す
2. 「合併を打ち切りとみなした 1−KM」と CIF を比べる（競合リスクを無視したときの過大評価）
3. 原因別ハザード（cause-specific Cox）と Fine–Gray の部分分布ハザード
   - 打ち切りは全員「2026-09-30」で管理上決まっている（打ち切りの時刻が全員わかる）ので、
     Fine–Gray は「競合イベントが起きた法人を、自分の打ち切りの時刻までリスク集合に残す」Cox と同じになる
     （Fine & Gray 1999 の censoring complete の場合）
4. 確認：5年以上追える法人で「5年以内に閉鎖／合併したか」のロジスティック回帰（直接2値）
5. 全法人（古い法人も含む）の年別の閉鎖・合併の件数
"""
import json, numpy as np, pandas as pd
from lifelines import CoxPHFitter
from common import DATA, RAW, RES, SEED, aj
import statsmodels.formula.api as smf

d = pd.read_parquet(DATA / "cr.parquet")
H = np.arange(0, 11.01, 0.25)
out = {}

# 1–2. CIF
rows = []
for k, g in [("全体", d)] + list(d.groupby("kindj")):
    r = aj(g["T"].values, g.cause3.values); r["kind"] = k; rows.append(r)
cif = pd.concat(rows).rename_axis("year").reset_index()
cif.to_csv(RES / "cif_by_kind.csv", index=False)
def at(k, y, col): return float(cif[(cif.kind == k) & (np.isclose(cif.year, y))][col].iloc[0])
for k in ["全体", "株式会社", "合同会社", "その他（一般社団・NPOなど）"]:
    out[f"cif_{k}"] = {f"{y}年": {"閉鎖": round(at(k, y, "F1"), 4), "合併": round(at(k, y, "F2"), 4),
                                "残存": round(at(k, y, "S"), 4), "1-KM閉鎖": round(at(k, y, "KM1"), 4)} for y in [3, 5, 10]}
# 合併の割合（イベントのうち合併）
out["merge_share_of_exits_10y"] = {k: round(at(k, 10, "F2") / (at(k, 10, "F1") + at(k, 10, "F2")), 4)
                                   for k in ["全体", "株式会社", "合同会社", "その他（一般社団・NPOなど）"]}

# 地域・設立年別の合併の CIF
rows = []
for col in ["area", "region"]:
    for v, g in d.groupby(col):
        r = aj(g["T"].values, g.cause3.values, grid=np.array([3, 5, 8]))
        rows.append({"by": col, "value": v, "n": len(g), **{f"merge{y}": r.F2.iloc[i] for i, y in enumerate([3, 5, 8])},
                     **{f"close{y}": r.F1.iloc[i] for i, y in enumerate([3, 5, 8])}})
for v, g in d.groupby("cohort"):
    r = aj(g["T"].values, g.cause3.values, grid=np.array([3]))
    rows.append({"by": "cohort", "value": int(v), "n": len(g), "merge3": r.F2.iloc[0], "close3": r.F1.iloc[0]})
grp = pd.DataFrame(rows); grp.to_csv(RES / "cif_by_group.csv", index=False)

# 3. Cox（原因別）と Fine–Gray（30万法人の無作為抽出）
def design(s):
    X = pd.get_dummies(s[["kindj", "area", "region"]], drop_first=False).astype(float)
    X = X.drop(columns=["kindj_株式会社", "area_その他の市町村", "region_関東"])
    X["cohort_c"] = (s.cohort - 2020) / 5
    return X
def fit_cs(s, ev):
    X = design(s); X["T"] = s["T"].values; X["E"] = (s.cause3 == ev).astype(int).values
    m = CoxPHFitter(penalizer=0.0).fit(X, "T", "E"); return m
def fit_fg(s, ev):
    X = design(s); other = (s.cause3 != ev) & (s.cause3 != 0)
    X["T"] = np.where(other, s["C"], s["T"]); X["E"] = (s.cause3 == ev).astype(int).values
    return CoxPHFitter(penalizer=0.0).fit(X, "T", "E")
def tab(m, label):
    sm = m.summary
    return pd.DataFrame({"model": label, "var": sm.index, "HR": np.exp(sm["coef"]),
                         "lo": np.exp(sm["coef lower 95%"]), "hi": np.exp(sm["coef upper 95%"]), "p": sm["p"]})
s = d.sample(300000, random_state=SEED)
tabs = []
for ev, nm in [(1, "閉鎖"), (2, "合併")]:
    tabs.append(tab(fit_cs(s, ev), f"原因別Cox_{nm}"))
    tabs.append(tab(fit_fg(s, ev), f"FineGray_{nm}"))
hr = pd.concat(tabs); hr.to_csv(RES / "hr_cs_fg.csv", index=False)
def g(model, var): r = hr[(hr.model == model) & (hr["var"] == var)].iloc[0]; return [round(r.HR, 3), round(r.lo, 3), round(r.hi, 3)]
out["hr"] = {m: {v: g(m, v) for v in ["kindj_合同会社", "kindj_その他（一般社団・NPOなど）", "area_東京23区", "area_政令市", "cohort_c"]}
             for m in hr.model.unique()}

# 4. 直接2値：5年以上追える法人で5年以内に閉鎖／合併
b = d[d.C >= 5].copy()
b["close5"] = ((b.cause3 == 1) & (b["T"] <= 5)).astype(int)
b["merge5"] = ((b.cause3 == 2) & (b["T"] <= 5)).astype(int)
b = b.rename(columns={"kindj": "kind", "C": "cens"})
lg = {}
for y in ["close5", "merge5"]:
    m = smf.logit(f"{y} ~ C(kind, Treatment('株式会社')) + C(area, Treatment('その他の市町村')) + C(region, Treatment('関東')) + cohort", b).fit(disp=0)
    ci = m.conf_int()
    lg[y] = {k: [round(float(np.exp(m.params[k])), 3), round(float(np.exp(ci.loc[k, 0])), 3), round(float(np.exp(ci.loc[k, 1])), 3)]
             for k in m.params.index if "合同会社" in k or "東京23区" in k or "その他（" in k}
    lg[y + "_rate"] = round(float(b[y].mean()), 5)
out["logit5"] = lg; out["n_logit5"] = int(len(b))

# 5. 全法人の年別
y = pd.read_csv(RAW / "houjin_yearly_counts.csv", dtype={"kind": str, "cause": str})
c = y[(y.type == "close") & (y.kind.isin(["301", "302", "305"]))].copy()
c["what"] = c.cause.map({"01": "清算の結了等", "21": "登記官による閉鎖", "11": "合併による解散", "31": "本店移転"})
yy = c.pivot_table(index="year", columns="what", values="n", aggfunc="sum").fillna(0).astype(int)
yy = yy[(yy.index >= 2016) & (yy.index <= 2025)]
yy.to_csv(RES / "yearly_all_corps.csv")
out["yearly_merge"] = {int(k): int(v) for k, v in yy["合併による解散"].items()}
out["yearly_close01"] = {int(k): int(v) for k, v in yy["清算の結了等"].items()}
out["merge_share_all_2016_2024"] = round(float(yy.loc[2016:2024, "合併による解散"].sum() /
    (yy.loc[2016:2024, ["清算の結了等", "合併による解散"]].sum().sum())), 4)

out["n"] = int(len(d)); out["events"] = d.cause3.value_counts().to_dict()
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:4000])
