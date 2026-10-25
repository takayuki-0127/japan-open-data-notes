"""集計値からハザード（その年の初めに残っていた人のうち、その年に辞めた割合）を作る"""
from common import *

m = pd.read_csv(DATA / "turnover_by_education.csv")
mac = pd.read_csv(DATA / "macro_annual.csv").set_index("year")
rows = []
for _, r in m.iterrows():
    cum = 0
    for k in (1, 2, 3):
        e = r[f"sep_y{k}"]
        if pd.isna(e): break
        at = r.hires - cum
        Y = int(r.grad_year)
        rows.append(dict(education=r.education, grad_year=Y, k=k, at_risk=at, events=e, hazard=e / at,
                         surv_end=1 - (cum + e) / r.hires,
                         entry_year=Y - 1, cal_year=Y + k - 1,
                         jr_entry=mac.jobs_ratio.get(Y - 1), jr_cur=mac.jobs_ratio.get(Y + k - 1),
                         ue_entry=mac.unemp.get(Y - 1), ue_cur=mac.unemp.get(Y + k - 1)))
        cum += e
hz = pd.DataFrame(rows)
hz.to_csv(RES / "hazard_by_education.csv", index=False)

# 産業別：1・2・3年目までの累積（それぞれ翌年・翌々年・3年後の6月に把握）からハザードを作る
ind = pd.read_csv(DATA / "turnover_by_industry.csv")
keep = ["建設業", "製造業", "情報通信業", "運輸業、郵便業", "卸売業", "小売業", "金融業、保険業", "不動産業、物品賃貸業",
        "学術研究、専門・技術サービス業", "宿泊業、飲食サービス業", "生活関連サービス業、娯楽業", "教育、学習支援業",
        "医療、福祉", "サービス業（他に分類されないもの）", "電気・ガス・熱供給・水道業", "調査産業計"]
ind = ind[ind.industry.isin(keep) & ind.grad_year.between(2010, 2022)].dropna(subset=["hires", "sep_cum1", "sep_cum2", "sep_cum3"])
g = ind.groupby(["education", "industry"])[["hires", "sep_cum1", "sep_cum2", "sep_cum3"]].sum().reset_index()
g["h1"] = g.sep_cum1 / g.hires
g["h2"] = (g.sep_cum2 - g.sep_cum1) / (g.hires - g.sep_cum1)
g["h3"] = (g.sep_cum3 - g.sep_cum2) / (g.hires - g.sep_cum2)
g["within3"] = g.sep_cum3 / g.hires
g.to_csv(RES / "hazard_by_industry_2010_2022.csv", index=False)

# 規模別（2003〜2023年3月卒の合計）
s = pd.read_csv(DATA / "turnover_by_size.csv")
p = s.pivot_table(index=["education", "grad_year", "size"], columns="k", values="sep_cum").reset_index()
h = s[s.k == 3][["education", "grad_year", "size", "hires"]]
p = p.merge(h, on=["education", "grad_year", "size"])
gs = p.groupby(["education", "size"])[[1, 2, 3, "hires"]].sum().reset_index()
gs["h1"] = gs[1] / gs.hires
gs["h2"] = (gs[2] - gs[1]) / (gs.hires - gs[1])
gs["h3"] = (gs[3] - gs[2]) / (gs.hires - gs[2])
gs["within3"] = gs[3] / gs.hires
gs.columns = [str(c) for c in gs.columns]
gs.to_csv(RES / "hazard_by_size_2003_2023.csv", index=False)

# 卒業年代ごとの残存（その年代の卒業者を合計して計算）
hz["cohort_group"] = pd.cut(hz.grad_year, [1995, 2000, 2005, 2010, 2015, 2020, 2025],
                            labels=["1996-2000", "2001-05", "2006-10", "2011-15", "2016-20", "2021-25"])
sv = []
for (ed, cg), d in hz.groupby(["education", "cohort_group"], observed=True):
    S = 1.0
    for k in (1, 2, 3):
        dk = d[d.k == k]
        if dk.empty: break
        hk = dk.events.sum() / dk.at_risk.sum()
        S *= 1 - hk
        sv.append(dict(education=ed, cohort_group=cg, k=k, hazard=hk, survival=S, n_cohorts=len(dk)))
pd.DataFrame(sv).to_csv(RES / "survival_by_cohort_group.csv", index=False)
print(hz.groupby(["education", "k"]).hazard.agg(["mean", "min", "max"]).round(3))
print(g[["education", "industry", "h1", "h2", "h3", "within3"]].round(3).sort_values(["education", "within3"]).to_string())
print(gs[["education", "size", "h1", "h2", "h3", "within3"]].round(3).to_string())
