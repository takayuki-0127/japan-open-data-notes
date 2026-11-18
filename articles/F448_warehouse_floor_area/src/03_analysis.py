"""倉庫の着工床面積：全国の推移、期間平均、地方別の寄与、関東の中の内訳、1むねあたりの大きさ、頑健性。
出力：results/main.json と CSV"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
TOKYO_AROUND = ["茨城", "栃木", "群馬", "埼玉", "千葉", "神奈川"]
PA, PB, PC = (2005, 2009), (2015, 2019), (2021, 2025)

df = pd.read_csv(ROOT / "data" / "pref_year.csv", dtype={"code": str})
w = df[df.kind == "倉庫"].copy()


def pmean(s, p):
    """年度を index に持つ Series の期間平均"""
    return float(s.loc[p[0]:p[1]].mean())


def r(x, n=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


# 全国の推移
nat = w.groupby("fy", sort=True)[["n_bldg", "floor_m2", "cost_man_yen"]].sum()
nat["floor_per_bldg"] = nat["floor_m2"] / nat["n_bldg"]
nat["kanto_share"] = w[w.region == "関東"].groupby("fy")["floor_m2"].sum() / nat["floor_m2"] * 100
nat.round(3).to_csv(R / "national.csv", encoding="utf-8")

# 5年度ごとの平均（地方別、北から南）
bins = [(1988, 1992), (1993, 1997), (1998, 2002), (2003, 2007), (2008, 2012), (2013, 2017), (2018, 2022), (2023, 2025)]
reg = w.groupby(["region", "fy"], sort=True)["floor_m2"].sum().unstack(0)[REGIONS]
rows = []
for b in bins:
    m = reg.loc[b[0]:b[1]].mean()
    row = {"period": f"{b[0]}-{b[1]}"}
    row.update({k: round(v / 1e4, 1) for k, v in m.items()})  # 万㎡
    row["全国"] = round(m.sum() / 1e4, 1)
    rows.append(row)
pd.DataFrame(rows).to_csv(R / "region_5yr_mean_10k_m2.csv", index=False, encoding="utf-8")


def contrib(series_by_region, p0, p1):
    a = series_by_region.loc[p0[0]:p0[1]].mean()
    b = series_by_region.loc[p1[0]:p1[1]].mean()
    d = b - a
    out = pd.DataFrame({"mean_p0_10k_m2": a / 1e4, "mean_p1_10k_m2": b / 1e4, "change_10k_m2": d / 1e4,
                        "change_pct": (b / a - 1) * 100, "share_of_national_change_pct": d / d.sum() * 100})
    return out.loc[[c for c in REGIONS if c in out.index]], float(a.sum()), float(b.sum())


c_ab, nat_a, nat_b = contrib(reg, PA, PB)
c_bc, _, nat_c = contrib(reg, PB, PC)
c_9 = contrib(reg, (1988, 1992), (1998, 2002))[0]
c_ab.round(2).to_csv(R / "contrib_2005_09_to_2015_19.csv", encoding="utf-8")
c_bc.round(2).to_csv(R / "contrib_2015_19_to_2021_25.csv", encoding="utf-8")

# 関東の中：東京都と周りの6県
pref = w.groupby(["pref", "fy"], sort=True)["floor_m2"].sum().unstack(0)
tok_a, tok_b, tok_c = (pmean(pref["東京"], p) for p in (PA, PB, PC))
aro = pref[TOKYO_AROUND].sum(axis=1)
aro_a, aro_b, aro_c = (pmean(aro, p) for p in (PA, PB, PC))
kanto_pref = []
for p in ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川"]:
    a, b, c = (pmean(pref[p], q) for q in (PA, PB, PC))
    kanto_pref.append({"pref": p, "mean_2005_09_10k_m2": round(a / 1e4, 1), "mean_2015_19_10k_m2": round(b / 1e4, 1),
                       "mean_2021_25_10k_m2": round(c / 1e4, 1), "pct_2005_09_to_2015_19": round((b / a - 1) * 100, 1),
                       "pct_2005_09_to_2021_25": round((c / a - 1) * 100, 1)})
pd.DataFrame(kanto_pref).to_csv(R / "kanto_prefs.csv", index=False, encoding="utf-8")

# 1むねあたりの床面積（地方別）
nb = w.groupby(["region", "fy"], sort=True)[["n_bldg", "floor_m2"]].sum()
size_rows = []
for g in REGIONS + ["全国"]:
    t = nb.loc[g] if g != "全国" else nat[["n_bldg", "floor_m2"]]
    vals = {}
    for p in (PA, PB, PC, (2021, 2023)):
        s = t.loc[p[0]:p[1]]
        vals[f"{p[0]}-{p[1]}"] = s["floor_m2"].sum() / s["n_bldg"].sum()
    size_rows.append({"region": g, **{k: round(v, 1) for k, v in vals.items()},
                      "ratio_2021_25_vs_2005_09": round(vals["2021-2025"] / vals["2005-2009"], 3)})
size = pd.DataFrame(size_rows)
size.to_csv(R / "floor_per_bldg_by_region.csv", index=False, encoding="utf-8")
sz = size.set_index("region")

# 関東の割合
ks = nat["kanto_share"]

# 頑健性
rob = []
def add(name, h, value, note):
    rob.append({"check": name, "hypothesis": h, "value": round(value, 2), "note": note})

add("基本：2005〜09→2015〜19 全国の増加率（%）", "H1", (nat_b / nat_a - 1) * 100, "床面積、5年度平均")
add("基本：同 増加分に占める関東（%）", "H2", float(c_ab.loc["関東", "share_of_national_change_pct"]), "")
# 1 期間を変える
for p0, p1 in [((2007, 2009), (2017, 2019)), ((2010, 2014), (2016, 2020)), ((2003, 2007), (2013, 2017))]:
    cc, a, b = contrib(reg, p0, p1)
    add(f"期間 {p0[0]}〜{p0[1] % 100:02d}→{p1[0]}〜{p1[1] % 100:02d}：全国の増加率（%）", "H1", (b / a - 1) * 100, "")
    add(f"期間 {p0[0]}〜{p0[1] % 100:02d}→{p1[0]}〜{p1[1] % 100:02d}：増加分に占める関東（%）", "H2",
        float(cc.loc["関東", "share_of_national_change_pct"]), "")
# 2 定義を変える：運輸業用建築物
t = df[df.kind == "運輸業用建築物"].groupby(["region", "fy"], sort=True)["floor_m2"].sum().unstack(0)[REGIONS]
cc, a, b = contrib(t, PA, PB)
add("定義：運輸業用建築物（用途別）全国の増加率（%）", "H1", (b / a - 1) * 100, "産業別の分類。倉庫業以外の運輸の建物も入る")
add("定義：運輸業用建築物 増加分に占める関東（%）", "H2", float(cc.loc["関東", "share_of_national_change_pct"]), "")
# 3 工事費予定額
tc = w.groupby(["region", "fy"], sort=True)["cost_man_yen"].sum().unstack(0)[REGIONS]
cc, a, b = contrib(tc, PA, PB)
add("量の測り方：工事費予定額（名目）全国の増加率（%）", "H1", (b / a - 1) * 100, "建築費の上昇を含む")
add("量の測り方：工事費予定額 増加分に占める関東（%）", "H2", float(cc.loc["関東", "share_of_national_change_pct"]), "")
# 4 大きな年を除く（各期間で全国の最大の年度を除く）
def drop_max(sr, p):
    s = sr.loc[p[0]:p[1]]
    return s.drop(s.sum(axis=1).idxmax())
a2, b2 = drop_max(reg, PA), drop_max(reg, PB)
d2 = b2.mean() - a2.mean()
add("各期間で最大の年度を除く：全国の増加率（%）", "H1", (b2.mean().sum() / a2.mean().sum() - 1) * 100,
    f"除いた年度 {int(reg.loc[PA[0]:PA[1]].sum(axis=1).idxmax())}・{int(reg.loc[PB[0]:PB[1]].sum(axis=1).idxmax())}")
add("各期間で最大の年度を除く：増加分に占める関東（%）", "H2", float(d2["関東"] / d2.sum() * 100), "")
# H4 の確かめ：2025年1月以降のむね数に小数があるので、2021〜23年度だけで
add("H4：1むねあたり床面積の倍率 2021〜23 vs 2005〜09", "H4",
    float(sz.loc["全国", "2021-2023"] / sz.loc["全国", "2005-2009"]), "むね数に小数が入る2024・2025年度を除く")
# H3 の確かめ：2021〜25年度で
add("H3：2005〜09→2021〜25 東京都の増加率（%）", "H3", (tok_c / tok_a - 1) * 100, "")
add("H3：2005〜09→2021〜25 周りの6県の増加率（%）", "H3", (aro_c / aro_a - 1) * 100, "")
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False, encoding="utf-8")

peak_fy = int(nat["floor_m2"].idxmax())
main = {
    "national_floor_10k_m2": {"1990": r(nat.loc[1990, "floor_m2"] / 1e4), "2009": r(nat.loc[2009, "floor_m2"] / 1e4),
                              "2021": r(nat.loc[2021, "floor_m2"] / 1e4), "2025": r(nat.loc[2025, "floor_m2"] / 1e4),
                              "peak_fy": peak_fy, "peak": r(nat.loc[peak_fy, "floor_m2"] / 1e4),
                              "min_fy": int(nat["floor_m2"].idxmin()), "min": r(nat["floor_m2"].min() / 1e4),
                              "ratio_2021_vs_2009": r(nat.loc[2021, "floor_m2"] / nat.loc[2009, "floor_m2"], 2),
                              "ratio_2021_vs_1990": r(nat.loc[2021, "floor_m2"] / nat.loc[1990, "floor_m2"], 2)},
    "national_mean_10k_m2": {"1988_92": r(pmean(nat["floor_m2"], (1988, 1992)) / 1e4), "2005_09": r(nat_a / 1e4),
                             "2015_19": r(nat_b / 1e4), "2021_25": r(nat_c / 1e4)},
    "H1_pct_2005_09_to_2015_19": r((nat_b / nat_a - 1) * 100),
    "pct_2015_19_to_2021_25": r((nat_c / nat_b - 1) * 100),
    "pct_2005_09_to_2021_25": r((nat_c / nat_a - 1) * 100),
    "H2_kanto_share_of_change_pct": r(c_ab.loc["関東", "share_of_national_change_pct"]),
    "kanto_share_of_change_2015_19_to_2021_25_pct": r(c_bc.loc["関東", "share_of_national_change_pct"]),
    "region_change_pct_2005_09_to_2015_19": {k: r(v) for k, v in c_ab["change_pct"].items()},
    "region_share_of_change_2005_09_to_2015_19": {k: r(v) for k, v in c_ab["share_of_national_change_pct"].items()},
    "region_change_pct_2015_19_to_2021_25": {k: r(v) for k, v in c_bc["change_pct"].items()},
    "region_change_pct_1988_92_to_1998_02": {k: r(v) for k, v in c_9["change_pct"].items()},
    "kanto_share_of_level_pct": {"1988_92": r(ks.loc[1988:1992].mean()), "2005_09": r(ks.loc[2005:2009].mean()),
                                 "2015_19": r(ks.loc[2015:2019].mean()), "2021_25": r(ks.loc[2021:2025].mean())},
    "H3": {"tokyo_pct_2005_09_to_2015_19": r((tok_b / tok_a - 1) * 100), "around6_pct_2005_09_to_2015_19": r((aro_b / aro_a - 1) * 100),
           "tokyo_pct_2005_09_to_2021_25": r((tok_c / tok_a - 1) * 100), "around6_pct_2005_09_to_2021_25": r((aro_c / aro_a - 1) * 100),
           "tokyo_share_of_kanto_2005_09": r(tok_a / (tok_a + aro_a) * 100), "tokyo_share_of_kanto_2021_25": r(tok_c / (tok_c + aro_c) * 100)},
    "H4_floor_per_bldg_m2": {"2005_09": r(sz.loc["全国", "2005-2009"]), "2015_19": r(sz.loc["全国", "2015-2019"]),
                             "2021_25": r(sz.loc["全国", "2021-2025"]), "2021_23": r(sz.loc["全国", "2021-2023"]),
                             "ratio_2021_25_vs_2005_09": r(sz.loc["全国", "ratio_2021_25_vs_2005_09"], 2)},
    "n_bldg_national": {"1990": r(nat.loc[1990, "n_bldg"], 0), "2005_09": r(pmean(nat["n_bldg"], PA), 0),
                        "2021_25": r(pmean(nat["n_bldg"], PC), 0)},
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(pd.DataFrame(rob).to_string())
print(size.to_string())
print(pd.DataFrame(kanto_pref).to_string())
