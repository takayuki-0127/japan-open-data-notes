"""主な分析：国別の推移と割合、増加の内訳（国別・在学段階別）、機関の種類ごとの国の構成、地方別、仮説、頑健性。"""
import json
import pandas as pd
from common import ROOT, FOCUS, FIVE, REGIONS

D, R = ROOT / "data", ROOT / "results"; R.mkdir(exist_ok=True)
st = pd.read_csv(D / "stage.csv", index_col="year")
ca = pd.read_csv(D / "country_all.csv")
tot = pd.read_csv(D / "country_all_total.csv", index_col="year").total
che = pd.read_csv(D / "country_he.csv")
he_tot = pd.read_csv(D / "country_he_total.csv", index_col="year").total
cj = pd.read_csv(D / "country_jls.csv")
reg = pd.read_csv(D / "region.csv")
wide = ca.pivot(index="year", columns="country", values="n")


def share(n, t):
    return round(100 * n / t, 1)


m = {}
m["total"] = {str(y): int(tot[y]) for y in [2013, 2019, 2022, 2025]}
m["stage_total"] = {str(y): int(st.total[y]) for y in [1983, 2011, 2019, 2022, 2025]}

# 国別の推移（主な10か国）
rows = []
for y in wide.index:
    for c in FOCUS:
        v = wide.at[y, c] if c in wide.columns else float("nan")
        rows.append({"year": y, "country": c, "n": None if pd.isna(v) else int(v), "share_pct": None if pd.isna(v) else share(v, tot[y])})
bc = pd.DataFrame(rows)
bc.to_csv(R / "by_country_year.csv", index=False)
cs = bc.pivot(index="year", columns="country", values="share_pct")
cn = bc.pivot(index="year", columns="country", values="n")
m["country"] = {c: {str(y): {"n": None if pd.isna(cn.at[y, c]) else int(cn.at[y, c]), "share": None if pd.isna(cs.at[y, c]) else float(cs.at[y, c])}
                    for y in [2013, 2019, 2022, 2025]} for c in FOCUS}
m["ratio_2013_2025"] = {c: round(float(cn.at[2025, c] / cn.at[2013, c]), 2) for c in FOCUS}
m["missing_in_list"] = {c: [int(y) for y in cn.index[cn[c].isna()]] for c in FOCUS}


def contrib(y0, y1, countries):
    d = tot[y1] - tot[y0]
    res = {"y0": y0, "y1": y1, "total_change": int(d)}
    for c in countries:
        a, b = wide.at[y0, c], wide.at[y1, c]
        res[c] = {"change": int(b - a), "share_of_change_pct": round(100 * (b - a) / d, 1)}
    five = sum(wide.at[y1, c] - wide.at[y0, c] for c in FIVE)
    res["five"] = {"change": int(five), "share_of_change_pct": round(100 * five / d, 1)}
    return res


m["contrib_2013_2025"] = contrib(2013, 2025, FOCUS)
m["contrib_2019_2025"] = contrib(2019, 2025, FOCUS)
m["contrib_2022_2025"] = contrib(2022, 2025, FOCUS)

# 在学段階別の増加の内訳
SC = [("grad", "大学院"), ("ug_jc_tech", "学部・短大・高専"), ("senshu", "専修学校（専門課程）"), ("prep", "準備教育課程"), ("jls", "日本語教育機関")]
srows = []
for y0, y1 in [(2013, 2025), (2019, 2025), (2022, 2025)]:
    dt = st.total[y1] - st.total[y0]
    for k, lab in SC:
        dv = st[k][y1] - st[k][y0]
        srows.append({"period": f"{y0}→{y1}", "stage": lab, "n0": int(st[k][y0]), "n1": int(st[k][y1]), "change": int(dv),
                      "share_of_change_pct": round(100 * dv / dt, 1), "share1_pct": share(st[k][y1], st.total[y1])})
sdf = pd.DataFrame(srows)
sdf.to_csv(R / "stage_contrib.csv", index=False)
m["stage_contrib"] = sdf.to_dict(orient="records")
s1925 = sdf[sdf.period == "2019→2025"].set_index("stage")
m["senshu_jls_share_of_change_2019_2025"] = round(float(s1925.loc[["専修学校（専門課程）", "日本語教育機関"], "share_of_change_pct"].sum()), 1)
m["stage_peak_2019_vs_2025"] = {lab: {"2019": int(st[k][2019]), "2025": int(st[k][2025])} for k, lab in SC}

# 機関の種類ごとの国の構成（2025年・2019年）
comp = []
for y in [2019, 2025]:
    h = che[che.year == y].set_index("country").n
    jj = cj[cj.year == y].set_index("country").n
    for c in FOCUS:
        comp.append({"year": y, "country": c, "he_n": int(h.get(c, 0)) if c in h.index else None,
                     "he_share": share(h[c], he_tot[y]) if c in h.index else None,
                     "jls_n": int(jj[c]) if c in jj.index else None, "jls_share": share(jj[c], int(st.jls[y])) if c in jj.index else None})
comp = pd.DataFrame(comp)
comp.to_csv(R / "composition_by_type.csv", index=False)
m["composition_by_type"] = comp.where(comp.notna(), None).to_dict(orient="records")

# 地方別（北から南）
order = [r for r, _ in REGIONS]
rg = reg[reg.basis == "本部"].pivot(index="region", columns="year", values="n").loc[order]
rshare = (100 * rg / rg.sum()).round(1)
rt = pd.DataFrame({"n_2019": rg[2019], "n_2025": rg[2025], "share_2019": rshare[2019], "share_2025": rshare[2025],
                   "change_pct": (100 * (rg[2025] / rg[2019] - 1)).round(1)})
rt.to_csv(R / "region_2019_2025.csv")
m["region"] = {r: {k: float(v) for k, v in rt.loc[r].items()} for r in order}
rb = reg[(reg.basis == "校舎") & (reg.year == 2025)].set_index("region").n.loc[order]
m["region_kanto_2025_campus_share"] = share(rb["関東"], rb.sum())
m["tokyo"] = {}
pf = pd.read_csv(D / "pref.csv")
for y in [2019, 2025]:
    t = pf[(pf.year == y) & (pf.basis == "本部")]
    m["tokyo"][str(y)] = {"n": int(t[t.pref == "東京"].n.iloc[0]), "share": share(t[t.pref == "東京"].n.iloc[0], t.n.sum())}

# 仮説
h = {}
c13, c25 = m["country"]["中国"]["2013"]["share"], m["country"]["中国"]["2025"]["share"]
h["H1"] = {"china_share_2013": c13, "china_share_2025": c25, "drop_pt": round(c13 - c25, 1), "verdict": "支持" if c13 - c25 >= 15 else "外れ"}
f = m["contrib_2013_2025"]["five"]["share_of_change_pct"]
h["H2"] = {"five_share_of_change_pct": f, "verdict": "支持" if f >= 50 else "外れ"}
s = m["senshu_jls_share_of_change_2019_2025"]
h["H3"] = {"senshu_jls_share_of_change_pct": s, "verdict": "支持" if s >= 50 else "外れ"}
c = comp[(comp.year == 2025) & (comp.country == "中国")].iloc[0]
h["H4"] = {"china_he_share": float(c.he_share), "china_jls_share": float(c.jls_share), "verdict": "支持" if c.he_share > c.jls_share else "外れ"}
k19, k25 = m["region"]["関東"]["share_2019"], m["region"]["関東"]["share_2025"]
h["H5"] = {"kanto_2019": k19, "kanto_2025": k25, "verdict": "支持" if k25 < k19 else "外れ"}
m["hypotheses"] = h

# 頑健性
rob = []
for y0 in [2013, 2019, 2022]:
    cc = contrib(y0, 2025, ["中国"])
    sd = sdf[sdf.period == f"{y0}→2025"].set_index("stage")
    rob.append({"check": "起点を変える", "period": f"{y0}→2025", "total_change": cc["total_change"],
                "five_share_of_change_pct": cc["five"]["share_of_change_pct"], "china_share_of_change_pct": cc["中国"]["share_of_change_pct"],
                "senshu_jls_share_of_change_pct": round(float(sd.loc[["専修学校（専門課程）", "日本語教育機関"], "share_of_change_pct"].sum()), 1)})
pv = pd.read_csv(D / "prev_value_check.csv")
rob.append({"check": "各年の表の「前年の値」と前年の表の値", "period": "2013〜2024", "note": f"{len(pv)}組を比べ、違いは {int((pv['diff'] != 0).sum())} 組"})
rob.append({"check": "地方別を校舎の所在地で集計", "period": "2025", "note": f"関東の割合 本部 {m['region']['関東']['share_2025']}% / 校舎 {m['region_kanto_2025_campus_share']}%"})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)
m["robustness"] = rob.where(rob.notna(), None).to_dict(orient="records")
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True,
          default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(h, ensure_ascii=False))
print(json.dumps({k: m[k] for k in ["contrib_2013_2025", "contrib_2019_2025", "missing_in_list", "region", "tokyo"]}, ensure_ascii=False))
print(sdf.to_string()); print(comp.to_string()); print(rob.to_string())
