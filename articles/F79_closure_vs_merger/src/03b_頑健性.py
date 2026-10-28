"""頑健性の確認（Fine–Gray の合同会社・東京23区のハザード比と、CIF の差）"""
import json, numpy as np, pandas as pd
from common import DATA, RES, SEED, aj
from lifelines import CoxPHFitter
d = pd.read_parquet(DATA / "cr.parquet")

def design(s, region=True):
    cols = ["kindj", "area"] + (["region"] if region else [])
    X = pd.get_dummies(s[cols], drop_first=False).astype(float)
    X = X.drop(columns=[c for c in ["kindj_株式会社", "area_その他の市町村", "region_関東"] if c in X])
    X["cohort_c"] = (s.cohort - 2020) / 5
    return X
def fg(s, ev_mask, other_mask, region=True):
    X = design(s, region); X["T"] = np.where(other_mask, s["C"], s["T"]); X["E"] = ev_mask.astype(int).values
    sm = CoxPHFitter().fit(X, "T", "E").summary
    return {v: [round(float(np.exp(sm.loc[v, "coef"])), 3), round(float(np.exp(sm.loc[v, "coef lower 95%"])), 3),
                round(float(np.exp(sm.loc[v, "coef upper 95%"])), 3)] for v in ["kindj_合同会社", "area_東京23区"]}

rows = []
def add(name, s, ev, region=True, three=False):
    if ev == "close":
        e = s.cause3 == 1; o = s.cause3 == 2
        if three: e = s.cause.isin(["01"]); o = s.cause.isin(["11", "21"])
    else:
        e = s.cause3 == 2; o = s.cause3 == 1
    r = fg(s, e, o, region)
    rows.append({"setting": name, "event": ev, "LLC_HR": r["kindj_合同会社"], "23ku_HR": r["area_東京23区"], "n": len(s)})

base = d.sample(300000, random_state=SEED)
alt = d.sample(300000, random_state=SEED + 1)
old = d[d.cohort <= 2019]; old = old.sample(min(300000, len(old)), random_state=SEED)
for ev in ["close", "merge"]:
    add("基本（30万法人）", base, ev)
    add("別の30万法人の抽出", alt, ev)
    add("2019年までの設立だけ", old, ev)
    add("地域を入れない", base, ev, region=False)
add("閉鎖＝清算の結了等だけ（登記官による閉鎖も競合に）", base, "close", three=True)
rob = pd.DataFrame(rows); rob.to_csv(RES / "robustness.csv", index=False)

# 競合リスクを無視したときの差（1−KM − CIF）を、合併が多いグループで
diff = []
for name, s in [("全体", d), ("株式会社", d[d.kindj == "株式会社"]), ("東京23区の株式会社", d[(d.kindj == "株式会社") & (d.area == "東京23区")]),
                ("その他の市町村の合同会社", d[(d.kindj == "合同会社") & (d.area == "その他の市町村")])]:
    r = aj(s["T"].values, s.cause3.values, grid=np.array([5.0, 10.0]))
    # 合併についての 1−KM（閉鎖を打ち切りとみなす）
    sw = s.cause3.replace({1: 2, 2: 1}).values
    r2 = aj(s["T"].values, sw, grid=np.array([5.0, 10.0]))
    diff.append({"group": name, "n": len(s),
                 "close_CIF10": r.F1.iloc[1], "close_1mKM10": r.KM1.iloc[1],
                 "merge_CIF10": r.F2.iloc[1], "merge_1mKM10": r2.KM1.iloc[1],
                 "merge_share10": r.F2.iloc[1] / (r.F1.iloc[1] + r.F2.iloc[1])})
pd.DataFrame(diff).to_csv(RES / "km_vs_cif.csv", index=False)

out = {"rob": rows, "km_vs_cif": diff, "n_close21": int((d.cause == "21").sum()), "n_close01": int((d.cause == "01").sum())}
json.dump(out, open(RES / "robustness.json", "w"), ensure_ascii=False, indent=1, default=float)
print(rob.to_string()); print(pd.DataFrame(diff).to_string())
