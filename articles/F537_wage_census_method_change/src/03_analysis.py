"""03_analysis.py：同じ2019年を古い方法と新しい方法で集計したときの差、2006〜2019年の伸びの差。
乱数は使わない。医療・福祉の産業（2019年の分類で P）は扱わない話題のため、産業別の結果から除く（産業計には含まれる）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "wage_long.csv")
ts = pd.read_csv(ROOT / "data" / "old_timeseries.csv")
EXCL = ["P"]  # 医療,福祉（2019年の産業分類）
VARS = ["shoteinai", "kimatte", "bonus", "workers"]


def pick(method, year, industry="TOTAL", size="計", sex="計", age="計"):
    s = d[(d["method"] == method) & (d["year"] == year) & (d["industry"] == industry) & (d["size"] == size) & (d["sex"] == sex) & (d["age"] == age)]
    assert len(s) == 1, (method, year, industry, size, sex, age, len(s))
    return s.iloc[0]


def pct(a, b):
    return round(100 * (a / b - 1), 2)


# 1. 2019年、新旧の差（産業計）：男女・企業規模
rows = []
for sex in ["計", "男", "女"]:
    for size in ["計", "1000+", "100-999", "10-99"]:
        o, n = pick("old", 2019, size=size, sex=sex), pick("new", 2019, size=size, sex=sex)
        rows.append(dict(sex=sex, size=size, **{f"old_{v}": o[v] for v in VARS}, **{f"new_{v}": n[v] for v in VARS},
                         **{f"diff_{v}_pct": pct(n[v], o[v]) for v in VARS}))
SS = pd.DataFrame(rows); SS.to_csv(R / "diff_2019_sex_size.csv", index=False)

# 2. 2019年、産業別（男女計・規模計）
names = d[(d["year"] == 2019) & (d["method"] == "new")].drop_duplicates("industry").set_index("industry")["industry_name"]
rows = []
for ind in sorted(i for i in d[(d["year"] == 2019) & (d["method"] == "old")]["industry"].unique() if i != "TOTAL"):
    o, n = pick("old", 2019, industry=ind), pick("new", 2019, industry=ind)
    rows.append(dict(industry=ind, name=names[ind], **{f"old_{v}": o[v] for v in VARS}, **{f"new_{v}": n[v] for v in VARS},
                     **{f"diff_{v}_pct": pct(n[v], o[v]) for v in VARS}))
IND_ALL = pd.DataFrame(rows)
IND = IND_ALL[~IND_ALL["industry"].isin(EXCL)].copy()
IND.to_csv(R / "diff_2019_industry.csv", index=False)

# 3. 2019年、年齢階級別（産業計・男女計・規模計）
AGES = ["~19歳", "20~24歳", "25~29歳", "30~34歳", "35~39歳", "40~44歳", "45~49歳", "50~54歳", "55~59歳", "60~64歳", "65~69歳", "70歳~"]
rows = []
for a in AGES:
    o, n = pick("old", 2019, age=a), pick("new", 2019, age=a)
    rows.append(dict(age=a, old_shoteinai=o["shoteinai"], new_shoteinai=n["shoteinai"], diff_shoteinai_pct=pct(n["shoteinai"], o["shoteinai"]),
                     old_workers=o["workers"], new_workers=n["workers"], diff_workers_pct=pct(n["workers"], o["workers"])))
AG = pd.DataFrame(rows); AG.to_csv(R / "diff_2019_age.csv", index=False)

# 4. 産業計の差を、産業ごとの賃金の差と、人数の構成の差に分ける（すべての産業を使う）
o = IND_ALL.set_index("industry"); tot_o, tot_n = pick("old", 2019), pick("new", 2019)
wo = o["old_workers"] / o["old_workers"].sum(); wn = o["new_workers"] / o["new_workers"].sum()
xo, xn = o["old_shoteinai"], o["new_shoteinai"]
recon_o, recon_n = float((wo * xo).sum()), float((wn * xn).sum())
wage_eff = float((wo * (xn - xo)).sum()); comp_eff = float(((wn - wo) * xn).sum())
SHIFT = dict(total_old=float(tot_o["shoteinai"]), total_new=float(tot_n["shoteinai"]), recon_old=round(recon_o, 2), recon_new=round(recon_n, 2),
             sum_workers_old=float(o["old_workers"].sum()), workers_total_old=float(tot_o["workers"]),
             diff=round(recon_n - recon_o, 2), wage_effect=round(wage_eff, 2), composition_effect=round(comp_eff, 2))

# 5. 時系列：古い方法（第3表）と新しい方法（遡及集計）、2006〜2019年
newts = d[(d["method"] == "new") & (d["industry"] == "TOTAL") & (d["size"] == "計") & (d["age"] == "計")].pivot_table(index="year", columns="sex", values="shoteinai")
T = ts[(ts["year"] >= 2006) & (ts["year"] <= 2019)].set_index("year")
TS = pd.DataFrame({"old_計": T["old_男女計"], "old_男": T["old_男"], "old_女": T["old_女"],
                   "new_計": newts["計"], "new_男": newts["男"], "new_女": newts["女"]})
for s in ["計", "男", "女"]:
    TS[f"diff_{s}_pct"] = (100 * (TS[f"new_{s}"] / TS[f"old_{s}"] - 1)).round(2)
TS.reset_index().to_csv(R / "timeseries_old_new.csv", index=False)
growth = {}
for base in [2006, 2009, 2015]:
    for s in ["計", "男", "女"]:
        go = pct(TS.loc[2019, f"old_{s}"], TS.loc[base, f"old_{s}"]); gn = pct(TS.loc[2019, f"new_{s}"], TS.loc[base, f"new_{s}"])
        growth[f"{base}_{s}"] = dict(old=go, new=gn, gap_pt=round(gn - go, 2))
# 年ごとの前年比の差
yoy = {}
for s in ["計"]:
    go = TS[f"old_{s}"].pct_change() * 100; gn = TS[f"new_{s}"].pct_change() * 100
    gap = (gn - go).dropna()
    yoy = dict(max_abs_gap_pt=round(float(gap.abs().max()), 2), year_of_max=int(gap.abs().idxmax()),
               mean_abs_gap_pt=round(float(gap.abs().mean()), 2),
               sign_disagree_years=[int(y) for y in gap.index if np.sign(go[y]) != np.sign(gn[y])])

# 頑健性：きまって支給・賞与で、2019年の差
rob = []
for v, lab in [("shoteinai", "所定内給与額（本線）"), ("kimatte", "きまって支給する現金給与額"), ("bonus", "年間賞与その他特別給与額")]:
    r = SS[(SS["sex"] == "計")].set_index("size")[f"diff_{v}_pct"]
    i = IND[f"diff_{v}_pct"]
    rob.append(dict(check=lab, total=r["計"], size_1000=r["1000+"], size_100_999=r["100-999"], size_10_99=r["10-99"],
                    n_ind_abs_ge3=int((i.abs() >= 3).sum()), ind_min=float(i.min()), ind_max=float(i.max())))
RB = pd.DataFrame(rob); RB.to_csv(R / "robustness.csv", index=False)

g = SS.set_index(["sex", "size"])
main = {
    "total_2019": {v: {"old": float(g.loc[("計", "計"), f"old_{v}"]), "new": float(g.loc[("計", "計"), f"new_{v}"]), "diff_pct": float(g.loc[("計", "計"), f"diff_{v}_pct"])} for v in VARS},
    "sex_2019_shoteinai_diff_pct": {s: float(g.loc[(s, "計"), "diff_shoteinai_pct"]) for s in ["計", "男", "女"]},
    "sex_2019_workers_diff_pct": {s: float(g.loc[(s, "計"), "diff_workers_pct"]) for s in ["計", "男", "女"]},
    "size_2019_shoteinai_diff_pct": {z: float(g.loc[("計", z), "diff_shoteinai_pct"]) for z in ["計", "1000+", "100-999", "10-99"]},
    "size_2019_workers_diff_pct": {z: float(g.loc[("計", z), "diff_workers_pct"]) for z in ["計", "1000+", "100-999", "10-99"]},
    "size_2019_shoteinai": {z: {"old": float(g.loc[("計", z), "old_shoteinai"]), "new": float(g.loc[("計", z), "new_shoteinai"])} for z in ["1000+", "100-999", "10-99"]},
    "workers_share_10_99": {"old": round(float(g.loc[("計", "10-99"), "old_workers"] / g.loc[("計", "計"), "old_workers"] * 100), 1),
                            "new": round(float(g.loc[("計", "10-99"), "new_workers"] / g.loc[("計", "計"), "new_workers"] * 100), 1)},
    "industry_n": int(len(IND)), "industry_n_abs_ge3": int((IND["diff_shoteinai_pct"].abs() >= 3).sum()),
    "industry_min": IND.loc[IND["diff_shoteinai_pct"].idxmin(), ["name", "diff_shoteinai_pct"]].to_dict(),
    "industry_max": IND.loc[IND["diff_shoteinai_pct"].idxmax(), ["name", "diff_shoteinai_pct"]].to_dict(),
    "industry_mean_abs": round(float(IND["diff_shoteinai_pct"].abs().mean()), 2),
    "age_min": AG.loc[AG["diff_shoteinai_pct"].idxmin(), ["age", "diff_shoteinai_pct"]].to_dict(),
    "age_max": AG.loc[AG["diff_shoteinai_pct"].idxmax(), ["age", "diff_shoteinai_pct"]].to_dict(),
    "shift_share": SHIFT,
    "growth": growth, "yoy_gap": yoy,
    "diff_by_year_total_pct": {int(k): float(v) for k, v in TS["diff_計_pct"].items()},
}
H = {
    "H1": dict(old=growth["2006_計"]["old"], new=growth["2006_計"]["new"], gap_pt=growth["2006_計"]["gap_pt"], rule="|gap|<1", supported=abs(growth["2006_計"]["gap_pt"]) < 1),
    "H2": dict(n_abs_ge3=main["industry_n_abs_ge3"], rule=">=3", supported=main["industry_n_abs_ge3"] >= 3),
    "H3": dict(d10_99=main["size_2019_shoteinai_diff_pct"]["10-99"], d1000=main["size_2019_shoteinai_diff_pct"]["1000+"], rule="|10-99|>|1000+|",
               supported=abs(main["size_2019_shoteinai_diff_pct"]["10-99"]) > abs(main["size_2019_shoteinai_diff_pct"]["1000+"])),
    "H4": dict(female=main["sex_2019_shoteinai_diff_pct"]["女"], male=main["sex_2019_shoteinai_diff_pct"]["男"], rule="|女|>|男|",
               supported=abs(main["sex_2019_shoteinai_diff_pct"]["女"]) > abs(main["sex_2019_shoteinai_diff_pct"]["男"])),
}
main["hypotheses"] = {k: {kk: (bool(vv) if isinstance(vv, (bool, np.bool_)) else vv) for kk, vv in v.items()} for k, v in H.items()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True, default=float)
print(json.dumps(main, ensure_ascii=False, indent=1, default=float))
print(IND[["industry", "name", "old_shoteinai", "new_shoteinai", "diff_shoteinai_pct", "diff_workers_pct"]].to_string())
print(AG.to_string()); print(TS.to_string()); print(RB.to_string())
