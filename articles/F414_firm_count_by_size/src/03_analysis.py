"""企業等数の増減を、経営組織×規模、産業に分ける。結果は results/ に出す（オフライン、乱数なし）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "firms_long.csv")
SG = {1: "0〜4人", 2: "5〜19人", 3: "5〜19人", 4: "20〜99人", 5: "20〜99人", 6: "20〜99人", 7: "100〜299人",
      8: "300人以上", 9: "300人以上", 10: "300人以上", 11: "300人以上"}
SG_ORDER = ["0〜4人", "5〜19人", "20〜99人", "100〜299人", "300人以上"]
ORG_J = {"individual": "個人経営", "company": "会社企業", "other_corp": "会社以外の法人", "total": "計"}
INDS = list("ABCDEFGHIJKLMNOPQR")
tot = d[(d.ind == "A～R")]
res = {}

# 年×経営組織の総数
lv = tot[tot["size"] == 0].pivot(index="year", columns="org", values="firms")
lv.to_csv(R / "level_by_org.csv")
res["level"] = {str(y): {o: int(lv.loc[y, o]) for o in lv.columns} for y in lv.index}


def change(y0, y1, orgs=("individual", "company", "other_corp")):
    a = tot[(tot.year == y0) & (tot["size"] > 0)].copy(); b = tot[(tot.year == y1) & (tot["size"] > 0)].copy()
    for x in (a, b):
        x["sg"] = x["size"].map(SG)
    ga = a.groupby(["org", "sg"]).firms.sum(); gb = b.groupby(["org", "sg"]).firms.sum()
    ch = (gb - ga).rename("change").reset_index()
    ch["from"] = ch.apply(lambda r: int(ga[(r.org, r.sg)]), axis=1)
    ch["to"] = ch.apply(lambda r: int(gb[(r.org, r.sg)]), axis=1)
    ch = ch[ch.org.isin(orgs)]
    net = int(ch.change.sum())
    ch["share_of_net"] = ch.change / net
    return ch, net


# 本線：2012→2021
ch, net = change(2012, 2021)
ch["period"] = "2012-2021"
res["main"] = {"net": net, "from": int(lv.loc[2012, "total"]), "to": int(lv.loc[2021, "total"]),
               "pct": float(lv.loc[2021, "total"] / lv.loc[2012, "total"] - 1)}
by_org = ch.groupby("org").change.sum()
res["main"]["by_org"] = {o: {"change": int(by_org[o]), "share_of_net": float(by_org[o] / net),
                             "pct": float(lv.loc[2021, o] / lv.loc[2012, o] - 1)} for o in by_org.index}
by_sg = ch.groupby("sg").change.sum()
from_sg = ch.groupby("sg")["from"].sum()
res["main"]["by_size"] = {s: {"change": int(by_sg[s]), "share_of_net": float(by_sg[s] / net), "pct": float(by_sg[s] / from_sg[s])}
                          for s in SG_ORDER}
res["main"]["cells"] = {f"{r.org}|{r.sg}": {"change": int(r.change), "from": int(r["from"]), "to": int(r["to"]),
                                             "share_of_net": float(r.share_of_net)} for _, r in ch.iterrows()}
ch.to_csv(R / "change_org_size_2012_2021.csv", index=False, float_format="%.4f")
# 個人経営の0〜4人の減少と、それ以外
ind04 = ch[(ch.org == "individual") & (ch.sg == "0〜4人")].change.iloc[0]
res["main"]["individual_0_4_change"] = int(ind04)
res["main"]["individual_0_4_share_of_net"] = float(ind04 / net)
res["main"]["rest_change"] = int(net - ind04)
# 会社企業：規模別
comp = ch[ch.org == "company"].set_index("sg")
res["main"]["company_by_size"] = {s: {"change": int(comp.loc[s, "change"]), "pct": float(comp.loc[s, "change"] / comp.loc[s, "from"])}
                                  for s in SG_ORDER}
# 100人以上
big = ch[ch.sg.isin(["100〜299人", "300人以上"])]
res["main"]["size100plus"] = {"change": int(big.change.sum()), "pct": float(big.change.sum() / big["from"].sum())}

# 産業別（大分類）：個人経営と会社企業の増減
rows = []
for ind in INDS:
    for o in ("individual", "company", "other_corp", "total"):
        f = lambda y: int(d[(d.year == y) & (d.ind == ind) & (d["size"] == 0) & (d.org == o)].firms.iloc[0])
        rows.append({"ind": ind, "ind_name": d[(d.ind == ind)].ind_name.iloc[0], "org": o, "y2012": f(2012), "y2016": f(2016), "y2021": f(2021)})
ind_df = pd.DataFrame(rows)
ind_df["change"] = ind_df.y2021 - ind_df.y2012
ind_net = {o: int(ind_df[ind_df.org == o].change.sum()) for o in ("individual", "company", "other_corp", "total")}
ind_df["share_of_org_change"] = [r.change / ind_net[r.org] for r in ind_df.itertuples()]
ind_df["pct"] = ind_df.change / ind_df.y2012.replace(0, np.nan)
ind_df.to_csv(R / "change_by_industry_2012_2021.csv", index=False, float_format="%.4f")
iv = ind_df[ind_df.org == "individual"].set_index("ind")
res["industry_individual"] = {i: {"name": iv.loc[i, "ind_name"], "change": int(iv.loc[i, "change"]), "share": float(iv.loc[i, "share_of_org_change"]),
                                  "pct": None if pd.isna(iv.loc[i, "pct"]) else float(iv.loc[i, "pct"]), "y2012": int(iv.loc[i, "y2012"])} for i in INDS}
res["industry_individual_DIM_share"] = float(iv.loc[["D", "I", "M"], "change"].sum() / ind_net["individual"])
res["industry_individual_DIMN_share"] = float(iv.loc[["D", "I", "M", "N"], "change"].sum() / ind_net["individual"])
cv = ind_df[ind_df.org == "company"].set_index("ind")
res["industry_company"] = {i: {"name": cv.loc[i, "ind_name"], "change": int(cv.loc[i, "change"]), "pct": float(cv.loc[i, "pct"])} for i in INDS if cv.loc[i, "y2012"] > 0}

# 仮説
M = res["main"]
res["hypotheses"] = {
    "H1": {"individual_share_of_net": M["by_org"]["individual"]["share_of_net"], "result": "支持" if M["by_org"]["individual"]["share_of_net"] >= 0.8 else "外れ"},
    "H2": {"size0_4_share_of_net": M["by_size"]["0〜4人"]["share_of_net"], "result": "支持" if M["by_size"]["0〜4人"]["share_of_net"] >= 0.9 else "外れ"},
    "H3": {"company_pct": M["by_org"]["company"]["pct"], "individual_pct": M["by_org"]["individual"]["pct"],
           "result": "支持" if abs(M["by_org"]["company"]["pct"]) <= 0.05 and M["by_org"]["individual"]["pct"] <= -0.25 else "外れ"},
    "H4": {"DIM_share": res["industry_individual_DIM_share"], "result": "支持" if res["industry_individual_DIM_share"] >= 0.5 else "外れ"},
}

# 頑健性
rob = []
def rob_row(label, y0, y1, orgs=("individual", "company", "other_corp")):
    c, n = change(y0, y1, orgs)
    bo = c.groupby("org").change.sum(); bs = c.groupby("sg").change.sum()
    rob.append({"check": label, "from_year": y0, "to_year": y1, "net": n,
                "individual_share": float(bo.get("individual", np.nan) / n), "size0_4_share": float(bs["0〜4人"] / n),
                "individual_change": int(bo.get("individual", 0)), "company_change": int(bo.get("company", 0)),
                "company_pct": float(bo.get("company", 0) / lv.loc[y0, "company"])})
rob_row("本線：2012→2021年（活動調査どうし）", 2012, 2021)
rob_row("前半：2012→2016年", 2012, 2016)
rob_row("後半：2016→2021年", 2016, 2021)
rob_row("会社以外の法人を除く 2012→2021年", 2012, 2021, ("individual", "company"))
rob_row("始まりを2014年（基礎調査）に：2014→2021年", 2014, 2021)
rb = pd.DataFrame(rob)
# 規模のまとめ方を変える：0〜9人
a = tot[(tot.year == 2012) & (tot["size"].isin([1, 2])) & (tot.org != "total")].firms.sum()
b = tot[(tot.year == 2021) & (tot["size"].isin([1, 2])) & (tot.org != "total")].firms.sum()
res["robust_size0_9_share"] = float((b - a) / net)
rb.to_csv(R / "robustness.csv", index=False, float_format="%.4f")
res["robustness"] = rb.to_dict("records")
# 会社企業 2021→2024（参考：2024年は国内の常用雇用者で規模を分けている）
c21 = tot[(tot.year == 2021) & (tot.org == "company") & (tot["size"] > 0)].copy(); c24 = tot[(tot.year == 2024) & (tot.org == "company") & (tot["size"] > 0)].copy()
for x in (c21, c24):
    x["sg"] = x["size"].map(SG)
g21 = c21.groupby("sg").firms.sum(); g24 = c24.groupby("sg").firms.sum()
res["company_2021_2024"] = {"total_2021": int(g21.sum()), "total_2024": int(g24.sum()), "pct": float(g24.sum() / g21.sum() - 1),
                            "by_size": {s: {"y2021": int(g21[s]), "y2024": int(g24[s]), "pct": float(g24[s] / g21[s] - 1)} for s in SG_ORDER}}
res["individual_2024_with_employees"] = int(lv.loc[2024, "individual"])

# 年ごとの経営組織×規模（図のため）
yr = tot[(tot["size"] > 0) & (tot.org != "total")].copy(); yr["sg"] = yr["size"].map(SG)
yr = yr.groupby(["year", "org", "sg"]).agg(firms=("firms", "sum"), reg_emp=("reg_emp", "sum")).reset_index()
yr.to_csv(R / "level_org_size_by_year.csv", index=False)

# 問い直し：企業の数は減ったが、常用雇用者はどの規模に移ったのか（2012→2021）
e = yr[yr.year.isin([2012, 2021])].groupby(["year", "sg"]).agg(firms=("firms", "sum"), reg_emp=("reg_emp", "sum")).reset_index()
e["emp_share"] = e.reg_emp / e.groupby("year").reg_emp.transform("sum")
e["firm_share"] = e.firms / e.groupby("year").firms.transform("sum")
e.to_csv(R / "requestion_employment_by_size.csv", index=False, float_format="%.5f")
ee = e.set_index(["year", "sg"])
res["requestion"] = {s: {"emp_share_2012": float(ee.loc[(2012, s), "emp_share"]), "emp_share_2021": float(ee.loc[(2021, s), "emp_share"]),
                         "reg_emp_2012": int(ee.loc[(2012, s), "reg_emp"]), "reg_emp_2021": int(ee.loc[(2021, s), "reg_emp"]),
                         "firm_share_2012": float(ee.loc[(2012, s), "firm_share"]), "firm_share_2021": float(ee.loc[(2021, s), "firm_share"])} for s in SG_ORDER}
res["requestion_total_reg_emp"] = {"y2012": int(e[e.year == 2012].reg_emp.sum()), "y2021": int(e[e.year == 2021].reg_emp.sum())}
ind04e = yr[(yr.org == "individual") & (yr.sg == "0〜4人")].set_index("year")
res["individual_0_4_reg_emp"] = {str(y): int(ind04e.loc[y, "reg_emp"]) for y in (2012, 2016, 2021)}

json.dump(res, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: res[k] for k in ("main", "hypotheses", "industry_individual_DIM_share", "industry_individual_DIMN_share", "company_2021_2024", "requestion", "requestion_total_reg_emp", "robust_size0_9_share")}, ensure_ascii=False, indent=1))
print(rb.round(3).to_string())
print(ind_df[ind_df.org.isin(["individual", "company"])].round(3).to_string())
