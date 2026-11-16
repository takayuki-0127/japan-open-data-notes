"""03_analysis.py : 不本意非正規の割合を性・年齢で分け、年齢構成の影響と求人倍率との関係を見る（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "reason.csv")
allv = pd.read_csv(ROOT / "data" / "reason_all_versions.csv")
jr = pd.read_csv(ROOT / "data" / "jobs_ratio_annual.csv").set_index("year")["jobs_ratio"]
REASONS = ["都合のよい時間", "家計の補助・学費", "家事・育児等と両立", "通勤時間が短い", "専門的な技能", "正規の仕事がない", "その他"]
AGES = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]
d["rsum"] = d[REASONS].sum(axis=1)
d["share"] = d["正規の仕事がない"] / d.rsum * 100
d["share_total"] = d["正規の仕事がない"] / d.total * 100


def r(x, k=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


sh = d.pivot_table(index="year", columns=["sex", "age"], values="share")
sh.round(3).to_csv(RES / "share_by_sex_age.csv")
main = {}
tot = sh[("男女計", "年齢計")]
main["overall"] = {int(y): r(v) for y, v in tot.items()}
main["overall_definition_total"] = {int(y): r(v) for y, v in d[(d.sex == "男女計") & (d.age == "年齢計")].set_index("year").share_total.items()}
main["share_2025"] = {f"{s}_{a}": r(sh.loc[2025, (s, a)]) for s in ["男女計", "男", "女"] for a in ["年齢計"] + AGES}
main["share_2013"] = {f"{s}_{a}": r(sh.loc[2013, (s, a)]) for s in ["男女計", "男", "女"] for a in ["年齢計"] + AGES}
main["change_2013_2025_pt"] = {f"{s}_{a}": r(sh.loc[2025, (s, a)] - sh.loc[2013, (s, a)]) for s in ["男女計", "男", "女"] for a in ["年齢計"] + AGES}
nz = d[(d.year == 2025) & (d.sex == "男女計") & (d.age == "年齢計")].iloc[0]
main["counts_2025_manyen"] = {"total": r(nz.total, 0), "reason_sum": r(nz.rsum, 0), "involuntary": r(nz["正規の仕事がない"], 0)}
n13 = d[(d.year == 2013) & (d.sex == "男女計") & (d.age == "年齢計")].iloc[0]
main["counts_2013_manyen"] = {"total": r(n13.total, 0), "reason_sum": r(n13.rsum, 0), "involuntary": r(n13["正規の仕事がない"], 0)}
# 男の25〜54歳 の倍率
main["H2_ratio_to_overall_2025"] = {a: r(sh.loc[2025, ("男", a)] / sh.loc[2025, ("男女計", "年齢計")]) for a in ["25〜34歳", "35〜44歳", "45〜54歳"]}
# 不本意の人数の年齢構成（2025年）
inv = d[(d.year == 2025) & (d.sex.isin(["男", "女"])) & (d.age.isin(AGES))].set_index(["sex", "age"])["正規の仕事がない"]
main["involuntary_count_2025_by_sex_age"] = {f"{s}_{a}": r(v, 0) for (s, a), v in inv.items()}
main["involuntary_male_25_54_share_of_all"] = r(inv.loc[("男", slice(None))].loc[["25〜34歳", "35〜44歳", "45〜54歳"]].sum() / inv.sum() * 100, 1)


# ---- シフト・シェア ----
def shiftshare(cells, y0=2013, y1=2025):
    a = d[d.year.isin([y0, y1])].set_index(["year", "sex", "age"])
    w0 = a.loc[y0].loc[cells].rsum / a.loc[y0].loc[cells].rsum.sum()
    w1 = a.loc[y1].loc[cells].rsum / a.loc[y1].loc[cells].rsum.sum()
    s0 = a.loc[y0].loc[cells].share
    s1 = a.loc[y1].loc[cells].share
    within = ((w0 + w1) / 2 * (s1 - s0)).sum()
    comp = ((s0 + s1) / 2 * (w1 - w0)).sum()
    total = (w1 * s1).sum() - (w0 * s0).sum()
    return {"y0": y0, "y1": y1, "total_pt": r(total, 3), "within_pt": r(within, 3), "composition_pt": r(comp, 3),
            "composition_share": r(comp / total, 3)}


cells6 = [("男女計", a) for a in AGES]
cells12 = [(s, a) for s in ["男", "女"] for a in AGES]
main["shiftshare_age6"] = shiftshare(cells6)
main["shiftshare_sexage12"] = shiftshare(cells12)
main["shiftshare_age6_2013_2019"] = shiftshare(cells6, 2013, 2019)
w = d[(d.sex == "男女計") & (d.age.isin(AGES))].pivot_table(index="year", columns="age", values="rsum")
wsh = w.div(w.sum(axis=1), axis=0) * 100
wsh.round(2).to_csv(RES / "age_composition.csv")
main["age_composition_pct"] = {int(y): {a: r(wsh.loc[y, a], 1) for a in AGES} for y in [2013, 2019, 2025]}

# ---- 求人倍率との関係 ----
x = pd.DataFrame({"share": tot, "jr": jr}).dropna()
lev = np.corrcoef(x.share, x.jr)[0, 1]
dx = x.diff().dropna()
dif = np.corrcoef(dx.share, dx.jr)[0, 1]
b = np.polyfit(dx.jr, dx.share, 1)[0]
x.round(3).to_csv(RES / "share_vs_jobs_ratio.csv")
main["jobs_ratio"] = {"corr_level": r(lev, 3), "corr_diff": r(dif, 3), "slope_diff_pt_per_1": r(b, 2), "n": int(len(x)),
                      "jr": {int(y): r(v) for y, v in x.jr.items()},
                      "years_jr_down_share_up": [int(y) for y in dx.index if dx.loc[y, "jr"] < 0 and dx.loc[y, "share"] > 0]}
# 年齢別の差分の相関
ac = {}
for a in AGES:
    s = sh[("男女計", a)]
    z = pd.DataFrame({"s": s, "j": jr}).dropna().diff().dropna()
    ac[a] = r(np.corrcoef(z.s, z.j)[0, 1], 3)
main["jobs_ratio_corr_diff_by_age"] = ac
# 2つの版の重なり（2021・2022年）の差
ov = allv[allv.year.isin([2021, 2022])].pivot_table(index=["year", "sex", "age"], columns="version", values="正規の仕事がない")
main["version_overlap_max_abs_diff"] = r((ov[2022] - ov[2025]).abs().max(), 3)

# ---- 問い直し：ほかのどの理由が増えたか（割合の変化、男女計・年齢計と25〜34歳・男）----
rq = []
for s_, a_ in [("男女計", "年齢計"), ("男", "25〜34歳"), ("女", "35〜44歳"), ("男女計", "65歳以上")]:
    z = d[(d.sex == s_) & (d.age == a_)].set_index("year")
    for k in REASONS:
        p0 = z.loc[2013, k] / z.loc[2013, "rsum"] * 100
        p1 = z.loc[2025, k] / z.loc[2025, "rsum"] * 100
        rq.append({"sex": s_, "age": a_, "reason": k, "pct_2013": p0, "pct_2025": p1, "change_pt": p1 - p0})
rq = pd.DataFrame(rq)
rq.round(2).to_csv(RES / "requestion_reason_mix.csv", index=False)
main["requestion"] = {f"{s}_{a}": {row.reason: [r(row.pct_2013, 1), r(row.pct_2025, 1), r(row.change_pt, 1)] for row in g.itertuples()}
                      for (s, a), g in rq.groupby(["sex", "age"], sort=False)}

# ---- 頑健性 ----
rb = []
t2 = d[(d.sex == "男女計") & (d.age == "年齢計")].set_index("year").share_total
rb.append({"check": "主：分母＝理由の合計、男女計・年齢計", "v2013": tot.loc[2013], "v2025": tot.loc[2025], "change_pt": tot.loc[2025] - tot.loc[2013], "composition_share": main["shiftshare_age6"]["composition_share"]})
rb.append({"check": "1 分母＝総数（理由を答えなかった人を含む）", "v2013": t2.loc[2013], "v2025": t2.loc[2025], "change_pt": t2.loc[2025] - t2.loc[2013], "composition_share": None})
rb.append({"check": "2 分解の区分を男女×年齢12区分に", "v2013": tot.loc[2013], "v2025": tot.loc[2025], "change_pt": tot.loc[2025] - tot.loc[2013], "composition_share": main["shiftshare_sexage12"]["composition_share"]})
rb.append({"check": "3 期間の終わりを2019年に", "v2013": tot.loc[2013], "v2025": tot.loc[2019], "change_pt": tot.loc[2019] - tot.loc[2013], "composition_share": main["shiftshare_age6_2013_2019"]["composition_share"]})
m = d[(d.sex == "男") & (d.age == "年齢計")].set_index("year").share
rb.append({"check": "4 男だけ", "v2013": m.loc[2013], "v2025": m.loc[2025], "change_pt": m.loc[2025] - m.loc[2013], "composition_share": None})
rbd = pd.DataFrame(rb)
for c in ["v2013", "v2025", "change_pt"]:
    rbd[c] = rbd[c].astype(float).round(2)
rbd.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rbd.to_dict(orient="records")

# ---- 判定 ----
main["judgement"] = {
    "H1": "支持" if tot.loc[2025] < 10 else "外れ",
    "H2": "支持" if all(v >= 2 for v in main["H2_ratio_to_overall_2025"].values()) else "外れ",
    "H3": "支持" if main["shiftshare_age6"]["composition_share"] < 0.3 else "外れ",
    "H4": "支持" if (sh.loc[2025, ("男女計", "25〜34歳")] - sh.loc[2013, ("男女計", "25〜34歳")]) < (sh.loc[2025, ("男女計", "55〜64歳")] - sh.loc[2013, ("男女計", "55〜64歳")]) else "外れ",
}
with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True))
