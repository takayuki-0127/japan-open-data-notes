"""03 分析（オフライン）：戻り率（2025年÷2019年）を年齢・男女・地域・空港・月で出し、仮説 H1〜H5 を判定する。
出力：results/main.json、results/*.csv"""
import json, pathlib
import numpy as np, pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "outbound_pref_age_sex.csv")
pm = pd.read_csv(DATA / "outbound_port_month.csv")
pop = pd.read_csv(DATA / "pop_pref_age_sex.csv")
mon = pd.read_csv(DATA / "monthly_fx_price.csv")
ap = pd.read_csv(DATA / "annual_price.csv")
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井",
         "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川",
         "愛媛", "高知", "福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
REGION = {**{p: "北海道" for p in PREFS[0:1]}, **{p: "東北" for p in PREFS[1:7]}, **{p: "関東" for p in PREFS[7:14]},
          **{p: "中部" for p in PREFS[14:23]}, **{p: "近畿" for p in PREFS[23:30]}, **{p: "中国" for p in PREFS[30:35]},
          **{p: "四国" for p in PREFS[35:39]}, **{p: "九州・沖縄" for p in PREFS[39:47]}}
REG_ORDER = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
METRO = ["埼玉", "千葉", "東京", "神奈川", "愛知", "京都", "大阪", "兵庫"]
METRO_TOKYO = ["埼玉", "千葉", "東京", "神奈川"]
AGEG = {"0-4": "0〜19歳", "5-9": "0〜19歳", "10-14": "0〜19歳", "15-19": "0〜19歳", "20-24": "20代", "25-29": "20代", "30-34": "30代", "35-39": "30代",
        "40-44": "40代", "45-49": "40代", "50-54": "50代", "55-59": "50代", "60-64": "60歳以上", "65-69": "60歳以上", "70+": "60歳以上"}
AGEG_ORDER = ["0〜19歳", "20代", "30代", "40代", "50代", "60歳以上"]
AGES = list(AGEG)
BIG4 = ["成田", "羽田", "関西", "中部"]
r = lambda x: float(round(x, 4))

base = d[d.age.isin(AGES)].copy()  # 不詳・総数を除いた年齢の行
tot = d[(d.pref == "総数") & (d.age == "total")].groupby("year").n.sum()

def ratio(df, y1, y0, by):
    """by ごとに、y1年の出国者数 ÷ y0年（y0 がリストなら平均）"""
    y0s = y0 if isinstance(y0, list) else [y0]
    a = df[df.year == y1].groupby(by).n.sum()
    b = df[df.year.isin(y0s)].groupby(by).n.sum() / len(y0s)
    return (a / b)

M = {}
M["total_2019"] = int(tot[2019]); M["total_2024"] = int(tot[2024]); M["total_2025"] = int(tot[2025])
M["R_total_2025"] = r(tot[2025] / tot[2019]); M["R_total_2024"] = r(tot[2024] / tot[2019])
M["R_total_2025_vs_2017_19"] = r(tot[2025] / tot[[2017, 2018, 2019]].mean())
M["peak_year"] = int(tot.idxmax())
pd.DataFrame({"year": tot.index, "outbound": tot.values.astype(int), "ratio_to_2019": (tot / tot[2019]).round(4).values}).to_csv(RES / "total_by_year.csv", index=False)

# --- 年齢・男女 ---
nat = base[base.pref == "総数"].copy()
nat["ageg"] = nat.age.map(AGEG)
rows = []
for y1, y0, lab in [(2025, 2019, "2025/2019"), (2024, 2019, "2024/2019"), (2025, [2017, 2018, 2019], "2025/2017-19平均"), (2019, 2018, "2019/2018"), (2019, 2017, "2019/2017")]:
    for sex in ["計", "男", "女"]:
        g = nat if sex == "計" else nat[nat.sex == sex]
        for k, v in ratio(g, y1, y0, "ageg").items():
            rows.append(dict(comp=lab, sex=sex, ageg=k, ratio=r(v)))
        rows.append(dict(comp=lab, sex=sex, ageg="全体", ratio=r(ratio(g.assign(all=1), y1, y0, "all").iloc[0])))
age_t = pd.DataFrame(rows)
age_t.to_csv(RES / "ratio_by_age_sex.csv", index=False)
q = lambda comp, sex, ag: float(age_t[(age_t.comp == comp) & (age_t.sex == sex) & (age_t.ageg == ag)].ratio.iloc[0])
a5 = ratio(nat, 2025, 2019, "age").reindex(AGES)
a5s = nat[nat.year.isin([2019, 2025])].pivot_table(index=["age", "sex"], columns="year", values="n", aggfunc="sum")
a5s["ratio"] = (a5s[2025] / a5s[2019]).round(4)
a5s.reset_index().assign(order=lambda x: x.age.map({a: i for i, a in enumerate(AGES)})).sort_values(["order", "sex"]).drop(columns="order").to_csv(RES / "ratio_by_age5_sex.csv", index=False)
M["R_age"] = {k: q("2025/2019", "計", k) for k in AGEG_ORDER}
M["R_age_women"] = {k: q("2025/2019", "女", k) for k in AGEG_ORDER}
M["R_age_men"] = {k: q("2025/2019", "男", k) for k in AGEG_ORDER}
M["R_women"] = q("2025/2019", "女", "全体"); M["R_men"] = q("2025/2019", "男", "全体")
g2059 = nat[nat.age.isin(AGES[4:12])]
R2059 = float(g2059[g2059.year == 2025].n.sum() / g2059[g2059.year == 2019].n.sum())
R60 = M["R_age"]["60歳以上"]
M["R_20_59"] = r(R2059)
M["H1_gap_pt"] = r((R2059 - R60) * 100)
M["H1"] = "支持" if (R2059 - R60) * 100 >= 5 else "外れ"
R_all_nat = float(nat[nat.year == 2025].n.sum() / nat[nat.year == 2019].n.sum())
M["R_all_age_known"] = r(R_all_nat)
M["H2_gap_pt"] = r((M["R_age_women"]["20代"] - R_all_nat) * 100)
M["H2"] = "支持" if M["H2_gap_pt"] >= 5 else "外れ"
# ふだんの揺れ：2019/2018 の年齢差
M["normal_year_age_spread_pt"] = r((age_t[(age_t.comp == "2019/2018") & (age_t.sex == "計") & (age_t.ageg != "全体")].ratio.agg(lambda s: s.max() - s.min())) * 100)
M["share_60plus_2019"] = r(nat[(nat.year == 2019) & (nat.ageg == "60歳以上")].n.sum() / nat[nat.year == 2019].n.sum())
M["share_60plus_2025"] = r(nat[(nat.year == 2025) & (nat.ageg == "60歳以上")].n.sum() / nat[nat.year == 2025].n.sum())
# 減った人数のうち 60歳以上の分
dec = nat[nat.year == 2019].groupby("ageg").n.sum() - nat[nat.year == 2025].groupby("ageg").n.sum()
M["decline_total"] = int(dec.sum()); M["decline_share_60plus"] = r(dec["60歳以上"] / dec.sum())
M["decline_share_by_age"] = {k: r(dec[k] / dec.sum()) for k in AGEG_ORDER}

# --- 地域 ---
pr = base[base.pref.isin(PREFS)].copy()
pr["region"] = pr.pref.map(REGION)
pr["metro"] = np.where(pr.pref.isin(METRO), "大都市圏", "地方")
pr["metro_tokyo"] = np.where(pr.pref.isin(METRO_TOKYO), "首都圏", "首都圏以外")
reg = ratio(pr, 2025, 2019, "region").reindex(REG_ORDER)
met = ratio(pr, 2025, 2019, "metro")
mett = ratio(pr, 2025, 2019, "metro_tokyo")
M["R_region"] = {k: r(v) for k, v in reg.items()}
M["R_metro"] = r(met["大都市圏"]); M["R_nonmetro"] = r(met["地方"])
M["H3_gap_pt"] = r((met["大都市圏"] - met["地方"]) * 100)
M["H3"] = "支持" if M["H3_gap_pt"] >= 5 else "外れ"
M["R_tokyo_area"] = r(mett["首都圏"]); M["R_non_tokyo_area"] = r(mett["首都圏以外"])
M["H3_gap_pt_tokyo_def"] = r((mett["首都圏"] - mett["首都圏以外"]) * 100)
M["R_metro_2024"] = r(ratio(pr, 2024, 2019, "metro")["大都市圏"]); M["R_nonmetro_2024"] = r(ratio(pr, 2024, 2019, "metro")["地方"])
m1719 = ratio(pr, 2025, [2017, 2018, 2019], "metro")
M["H3_gap_pt_base1719"] = r((m1719["大都市圏"] - m1719["地方"]) * 100)
m_norm = ratio(pr, 2019, 2018, "metro"); M["metro_gap_pt_2019_2018"] = r((m_norm["大都市圏"] - m_norm["地方"]) * 100)
prefr = ratio(pr, 2025, 2019, "pref").reindex(PREFS)
pref_t = pd.DataFrame({"pref": PREFS, "region": [REGION[p] for p in PREFS], "metro": [p in METRO for p in PREFS],
                       "n2019": pr[pr.year == 2019].groupby("pref").n.sum().reindex(PREFS).astype(int).values,
                       "n2025": pr[pr.year == 2025].groupby("pref").n.sum().reindex(PREFS).astype(int).values,
                       "ratio": prefr.round(4).values})
# 出国率（人口千人あたり、2019・2024）
pp = pop.groupby(["year", "pref"]).pop_k.sum().unstack(0)
for y in (2019, 2024):
    pref_t[f"rate_{y}"] = (pr[pr.year == y].groupby("pref").n.sum().reindex(PREFS) / pp[y].reindex(PREFS)).round(2).values  # 千人あたり
pref_t["rate_ratio_2024"] = (pref_t.rate_2024 / pref_t.rate_2019).round(4)
pref_t.to_csv(RES / "ratio_by_pref.csv", index=False)
M["pref_ratio_min"] = r(prefr.min()); M["pref_ratio_max"] = r(prefr.max()); M["pref_ratio_median"] = r(prefr.median())
M["n_pref_ratio_ge_0.8"] = int((prefr >= 0.8).sum())
M["corr_rate2019_vs_ratio"] = r(np.corrcoef(pref_t.rate_2019, pref_t.ratio)[0, 1])
M["rate_2019_metro"] = r(pr[(pr.year == 2019) & (pr.metro == "大都市圏")].n.sum() / pop[(pop.year == 2019) & pop.pref.isin(METRO)].pop_k.sum())
M["rate_2019_nonmetro"] = r(pr[(pr.year == 2019) & (pr.metro == "地方")].n.sum() / pop[(pop.year == 2019) & ~pop.pref.isin(METRO)].pop_k.sum())

# --- 出国率（年齢、人口あたり） ---
pa = pop.copy(); pa["ageg"] = pa.age.map(AGEG)
na = pr.copy(); na["ageg"] = na.age.map(AGEG)
rate = {}
for y in (2019, 2024):
    rate[y] = na[na.year == y].groupby("ageg").n.sum() / pa[pa.year == y].groupby("ageg").pop_k.sum()
rt = pd.DataFrame({"ageg": AGEG_ORDER, "rate_2019_per_1000": rate[2019].reindex(AGEG_ORDER).round(1).values,
                   "rate_2024_per_1000": rate[2024].reindex(AGEG_ORDER).round(1).values})
rt["rate_ratio_2024"] = (rt.rate_2024_per_1000 / rt.rate_2019_per_1000).round(4)
rt["count_ratio_2024"] = [r(ratio(na, 2024, 2019, "ageg")[k]) for k in AGEG_ORDER]
rt.to_csv(RES / "rate_by_age.csv", index=False)
M["rate_ratio_2024_by_age"] = dict(zip(rt.ageg, rt.rate_ratio_2024.astype(float)))
M["count_ratio_2024_by_age"] = dict(zip(rt.ageg, rt.count_ratio_2024.astype(float)))
R2059_rate = float(na[(na.year == 2024) & na.age.isin(AGES[4:12])].n.sum() / pa[(pa.year == 2024) & pa.age.isin(AGES[4:12])].pop_k.sum()
                   / (na[(na.year == 2019) & na.age.isin(AGES[4:12])].n.sum() / pa[(pa.year == 2019) & pa.age.isin(AGES[4:12])].pop_k.sum()))
M["H1_gap_pt_rate2024"] = r((R2059_rate - M["rate_ratio_2024_by_age"]["60歳以上"]) * 100)
M["H1_gap_pt_2024"] = r((float(na[(na.year == 2024) & na.age.isin(AGES[4:12])].n.sum() / na[(na.year == 2019) & na.age.isin(AGES[4:12])].n.sum()) - M["count_ratio_2024_by_age"]["60歳以上"]) * 100)
c1719 = ratio(nat, 2025, [2017, 2018, 2019], "ageg")
M["H1_gap_pt_base1719"] = r((float(nat[(nat.year == 2025) & nat.age.isin(AGES[4:12])].n.sum() / (nat[nat.year.isin([2017, 2018, 2019]) & nat.age.isin(AGES[4:12])].n.sum() / 3)) - c1719["60歳以上"]) * 100)

# --- 空港 ---
ap_ = pm[(pm.kind == "空港") & (pm.port != "空港")].copy()
ap_["grp"] = np.where(ap_.port.isin(BIG4), "4大空港", "地方空港")
ap_["grp_f"] = np.where(ap_.port.isin(BIG4 + ["福岡"]), "4大空港＋福岡", "それ以外の空港")
pg = ratio(ap_, 2025, 2019, "grp"); pgf = ratio(ap_, 2025, 2019, "grp_f")
M["R_big4"] = r(pg["4大空港"]); M["R_regional_airports"] = r(pg["地方空港"])
M["H4_gap_pt"] = r((pg["4大空港"] - pg["地方空港"]) * 100)
M["H4"] = "支持" if M["H4_gap_pt"] >= 10 else "外れ"
M["H4_gap_pt_with_fukuoka"] = r((pgf["4大空港＋福岡"] - pgf["それ以外の空港"]) * 100)
pg24 = ratio(ap_, 2024, 2019, "grp"); M["H4_gap_pt_2024"] = r((pg24["4大空港"] - pg24["地方空港"]) * 100)
pg1719 = ratio(ap_, 2025, [2017, 2018, 2019], "grp"); M["H4_gap_pt_base1719"] = r((pg1719["4大空港"] - pg1719["地方空港"]) * 100)
ORDER_AP = ["新千歳", "仙台", "新潟", "成田", "羽田", "小松", "静岡", "中部", "関西", "広島", "福岡", "長崎", "熊本", "鹿児島", "那覇", "その他"]
port_t = ap_[ap_.year.isin([2019, 2025])].pivot_table(index="port", columns="year", values="n", aggfunc="sum").reindex(ORDER_AP)
port_t["ratio"] = (port_t[2025] / port_t[2019]).round(4)
port_t["share_2019"] = (port_t[2019] / port_t[2019].sum()).round(4); port_t["share_2025"] = (port_t[2025] / port_t[2025].sum()).round(4)
port_t.reset_index().rename(columns={2019: "n2019", 2025: "n2025"}).to_csv(RES / "ratio_by_airport.csv", index=False)
M["R_airport"] = {k: r(v) for k, v in port_t.ratio.items()}
M["share_haneda_2019"] = r(port_t.share_2019["羽田"]); M["share_haneda_2025"] = r(port_t.share_2025["羽田"])
M["share_big4_2019"] = r(port_t.loc[BIG4, "share_2019"].sum()); M["share_big4_2025"] = r(port_t.loc[BIG4, "share_2025"].sum())

# --- 月：戻り率と為替・値段 ---
tm = pm[pm.port == "総数"].pivot_table(index="month", columns="year", values="n")
mrows = []
for y in range(2023, 2026):
    for m in range(1, 13):
        mrows.append(dict(ym=y * 100 + m, year=y, month=m, n=int(tm.loc[m, y]), ratio_to_2019=r(tm.loc[m, y] / tm.loc[m, 2019])))
mr = pd.DataFrame(mrows).merge(mon, on="ym", how="left")
c19 = mon[(mon.ym // 100) == 2019][["ym", "cpi_foreign_pack", "usdjpy"]].assign(month=lambda x: x.ym % 100)
mr = mr.merge(c19[["month", "cpi_foreign_pack", "usdjpy"]].rename(columns={"cpi_foreign_pack": "cpi_fp_2019", "usdjpy": "usdjpy_2019"}), on="month")
mr["cpi_fp_vs_2019"] = (mr.cpi_foreign_pack / mr.cpi_fp_2019).round(4)
mr["usdjpy_vs_2019"] = (mr.usdjpy / mr.usdjpy_2019).round(4)
mr = mr.sort_values("ym").reset_index(drop=True)
mr.to_csv(RES / "monthly_ratio.csv", index=False)
X = sm.add_constant(np.arange(len(mr)) / 12.0)
fit = sm.OLS(mr.ratio_to_2019.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
lo, hi = fit.conf_int()[1]
M["monthly_trend_pt_per_year"] = r(fit.params[1] * 100); M["monthly_trend_ci"] = [r(lo * 100), r(hi * 100)]
M["H5"] = "支持" if lo > 0 else "外れ"
M["monthly_ratio_2023_first"] = r(mr.ratio_to_2019.iloc[0]); M["monthly_ratio_2025_last"] = r(mr.ratio_to_2019.iloc[-1])
M["monthly_ratio_2025_max"] = r(mr[mr.year == 2025].ratio_to_2019.max()); M["monthly_ratio_2025_min"] = r(mr[mr.year == 2025].ratio_to_2019.min())
M["monthly_ratio_2025_max_month"] = int(mr[mr.year == 2025].sort_values("ratio_to_2019").month.iloc[-1])
M["usdjpy_2019"] = r(mon[(mon.ym // 100) == 2019].usdjpy.mean()); M["usdjpy_2025"] = r(mon[(mon.ym // 100) == 2025].usdjpy.mean())
M["usdjpy_2023_2025_min"] = r(mon[(mon.ym >= 202301)].usdjpy.min()); M["usdjpy_2023_2025_max"] = r(mon[(mon.ym >= 202301)].usdjpy.max())
M["cpi_foreign_pack_2019"] = float(ap[ap.year == 2019].cpi_foreign_pack.iloc[0]); M["cpi_foreign_pack_2025"] = float(ap[ap.year == 2025].cpi_foreign_pack.iloc[0])
M["cpi_foreign_pack_ratio"] = r(M["cpi_foreign_pack_2025"] / M["cpi_foreign_pack_2019"])
M["cpi_all_ratio"] = r(float(ap[ap.year == 2025].cpi_all.iloc[0]) / float(ap[ap.year == 2019].cpi_all.iloc[0]))
M["corr_monthly_ratio_usdjpy"] = r(np.corrcoef(mr.ratio_to_2019, mr.usdjpy)[0, 1])

# --- 頑健性の表 ---
rob = [
    ("H1 年齢（20〜59歳−60歳以上）", "基本：2025年÷2019年", M["H1_gap_pt"]),
    ("H1 年齢（20〜59歳−60歳以上）", "基準を2017〜19年平均", M["H1_gap_pt_base1719"]),
    ("H1 年齢（20〜59歳−60歳以上）", "2024年÷2019年", M["H1_gap_pt_2024"]),
    ("H1 年齢（20〜59歳−60歳以上）", "出国率（人口あたり）2024年", M["H1_gap_pt_rate2024"]),
    ("H3 地域（大都市圏−地方）", "基本：2025年÷2019年", M["H3_gap_pt"]),
    ("H3 地域（大都市圏−地方）", "基準を2017〜19年平均", M["H3_gap_pt_base1719"]),
    ("H3 地域（大都市圏−地方）", "2024年÷2019年", r((M["R_metro_2024"] - M["R_nonmetro_2024"]) * 100)),
    ("H3 地域（大都市圏−地方）", "大都市圏を首都圏1都3県だけにする", M["H3_gap_pt_tokyo_def"]),
    ("H4 空港（4大空港−地方空港）", "基本：2025年÷2019年", M["H4_gap_pt"]),
    ("H4 空港（4大空港−地方空港）", "基準を2017〜19年平均", M["H4_gap_pt_base1719"]),
    ("H4 空港（4大空港−地方空港）", "2024年÷2019年", M["H4_gap_pt_2024"]),
    ("H4 空港（4大空港−地方空港）", "福岡を大きな空港に入れる", M["H4_gap_pt_with_fukuoka"]),
]
pd.DataFrame(rob, columns=["check", "variant", "gap_pt"]).to_csv(RES / "robustness.csv", index=False)
(RES / "main.json").write_text(json.dumps(M, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(M, ensure_ascii=False, indent=1))
