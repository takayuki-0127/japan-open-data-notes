"""F267 06 レビュー検算（独立レビューを受けて結果のあとに足した確認）"""
import json, pathlib
import numpy as np, pandas as pd
BASE = pathlib.Path(__file__).resolve().parents[1]
DATA, RES = BASE / "data", BASE / "results"
m = pd.read_csv(DATA / "jfa_cvs_monthly.csv")
for c, s in [("ls", "sales_ex_yoy"), ("lc", "cust_ex_yoy"), ("lp", "price_ex_yoy")]:
    m[c] = np.log1p(m[s])
m["t"] = m.year * 12 + m.month - 1
def win(y, mo, before=1, n=13):  # 前月（駆け込み）から施策後12か月まで
    t0 = y * 12 + mo - 1 - before
    return set(range(t0, t0 + n))
EV = {"taspo_2008": win(2008, 6, 0, 12), "tobacco_2010": win(2010, 10), "ctax_2014": win(2014, 4),
      "tobacco_2018": win(2018, 10), "ctax_2019": win(2019, 10), "tobacco_2020": win(2020, 10), "tobacco_2021": win(2021, 10)}
COVID = set(m.t[m.year.isin([2020, 2021, 2022])])
def share(d):
    C = np.cov(np.c_[d.lc, d.lp, d.ls].T); return dict(cust=float((C[0, 0] + C[0, 1]) / C[2, 2]), price=float((C[1, 1] + C[0, 1]) / C[2, 2]),
                                                      corr=float(np.corrcoef(d.lc, d.lp)[0, 1]), n=int(len(d)))
base = m[m.year.between(2006, 2025)]
ex1 = COVID | EV["taspo_2008"] | EV["tobacco_2010"] | EV["ctax_2014"]
exall = ex1 | EV["tobacco_2018"] | EV["ctax_2019"] | EV["tobacco_2020"] | EV["tobacco_2021"]
out = {"windows": {k: [f"{min(v)//12}-{min(v)%12+1:02d}", f"{max(v)//12}-{max(v)%12+1:02d}"] for k, v in EV.items()}}
out["H1_ex_covid"] = share(base[~base.t.isin(COVID)])
out["H1_ex_covid_taspo_tob2010_ctax2014"] = share(base[~base.t.isin(ex1)])
out["H1_ex_all_tax_tobacco_covid"] = share(base[~base.t.isin(exall)])
fh = base[base.year <= 2015]
out["first_half_ex_taspo_tob2010_ctax2014"] = share(fh[~fh.t.isin(ex1)])
# 月の値（レビューで挙がった時期）
pick = ["2010-09", "2010-10", "2011-01", "2011-02", "2014-03", "2014-04"]
out["months"] = m.set_index("ym").loc[pick, ["sales_ex_yoy", "cust_ex_yoy", "price_ex_yoy"]].round(4).to_dict(orient="index")
# H3：年ごとの一致（売上の判定と客数・客単価の判定が同じか）
H = pd.read_csv(RES / "H3_allocation_by_year.csv")
agree = {}
for rule in ["equal", "trend_ratio", "trend_gap", "price_only"]:
    h = H[(H.X == "past5") & (H.rule == rule)]
    agree[rule] = dict(n=int(len(h)), disagree_s_c=int((h.hit_s != h.hit_c).sum()), disagree_s_p=int((h.hit_s != h.hit_p).sum()),
                       both_sub_hit=int((h.hit_c & h.hit_p).sum()), sales_hit=int(h.hit_s.sum()))
out["H3_year_agreement"] = agree
tr = H[(H.X == "past5") & (H.rule == "trend_ratio")].set_index("year")
out["trend_ratio_detail"] = {int(y): dict(Xs=round(r.Xs * 100, 3), Xc=round(r.Xc * 100, 3), Xp=round(r.Xp * 100, 3), mc_plus_mp=round((r.mc + r.mp) * 100, 3)) for y, r in tr.iterrows()}
# 2016年以降の目標の高さ
s16 = tr.loc[2016:2025]
out["targets_2016_2025"] = dict(Xs=[round(s16.Xs.min() * 100, 2), round(s16.Xs.max() * 100, 2)], Xp=[round(s16.Xp.min() * 100, 2), round(s16.Xp.max() * 100, 2)])
# 問い直し：税・たばこの時期を除いた相関
r = pd.read_csv(RES / "reask_price_vs_cpi_monthly.csv")
r["t"] = r.year * 12 + r.month - 1
k = "cpi_食料工業製品"
def cc(d): return dict(corr=float(np.corrcoef(d[k], d.lp)[0, 1]), n=int(len(d)))
out["reask_corr"] = {"all": cc(r), "ex_covid": cc(r[~r.t.isin(COVID)]),
                     "ex_covid_ctax2019_tobacco": cc(r[~r.t.isin(COVID | EV["ctax_2019"] | EV["tobacco_2018"] | EV["tobacco_2020"] | EV["tobacco_2021"])]),
                     "only_2020_2021_excluded": cc(r[~r.year.isin([2020, 2021])])}
yr = pd.read_csv(RES / "reask_price_vs_cpi_annual.csv").set_index("year")
out["cpi_2016_2021_range"] = [round(yr.loc[2016:2021, k].min() * 100, 2), round(yr.loc[2016:2021, k].max() * 100, 2)]
json.dump(out, open(RES / "review_checks.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
