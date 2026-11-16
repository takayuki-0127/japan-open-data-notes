"""生乳生産量の分解（戸数 × 1戸あたり経産牛 × 1頭あたり生産量）、地域、規模。results/main.json と CSV。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"; R.mkdir(exist_ok=True)
h = pd.read_csv(D / "dairy_herd.csv")
h["version"] = h["version"].fillna("")
pr = pd.read_csv(D / "raw_milk_production.csv").set_index("year")
sz = pd.read_csv(D / "dairy_adults_by_size.csv")
fs = pd.read_csv(D / "dairy_farms_by_size.csv")


def series(region, ver2019="旧"):
    q = h[h.region == region]
    q = q[(q.year != 2019) | (q.version == ver2019)]
    return q.set_index("year")


def r(x, k=1):
    return round(float(x), k)


N = series("全国")
main = {}


def decompose(y0, y1, cow="parous", avg_next=False, src=N):
    def cows(y):
        if avg_next:
            return (src.loc[y, cow] + src.loc[y + 1, cow]) / 2
        return src.loc[y, cow]
    P0, P1 = pr.loc[y0, "milk_t"], pr.loc[y1, "milk_t"]
    F0, F1 = src.loc[y0, "farms"], src.loc[y1, "farms"]
    C0, C1 = cows(y0), cows(y1)
    lp = np.log(P1 / P0); lf = np.log(F1 / F0); ls = np.log((C1 / F1) / (C0 / F0)); ly = np.log((P1 / C1) / (P0 / C0))
    return {"y0": y0, "y1": y1, "cow": cow, "avg_next": avg_next,
            "milk_change_pct": r(100 * (P1 / P0 - 1), 2), "farms_change_pct": r(100 * (F1 / F0 - 1)),
            "cows_per_farm": [r(C0 / F0), r(C1 / F1)], "cows_per_farm_ratio": r(C1 / F1 / (C0 / F0), 2),
            "yield_kg": [r(1000 * P0 / C0, 0), r(1000 * P1 / C1, 0)], "yield_ratio": r(P1 / C1 / (P0 / C0), 3),
            "log_milk": r(lp, 3), "log_farms": r(lf, 3), "log_scale": r(ls, 3), "log_yield": r(ly, 3),
            "offset_share_scale_pct": r(100 * ls / (ls + ly)), "offset_share_yield_pct": r(100 * ly / (ls + ly))}


dec = {"main_1985_2024": decompose(1985, 2024), "start1990": decompose(1990, 2024), "start2000": decompose(2000, 2024),
       "milking_cows": decompose(1985, 2024, cow="milking"), "avg_feb_next": decompose(1985, 2023, avg_next=True),
       "end2023": decompose(1985, 2023)}
# 2019年の集計方法の変わり目（旧→新）の段差
o, n_ = series("全国", "旧").loc[2019], series("全国", "新").loc[2019]
main_break = {k: r(100 * (n_[k] / o[k] - 1), 2) for k in ["farms", "parous", "milking"]}
pd.DataFrame(dec).T.to_csv(R / "decomposition.csv")
main["decomposition"] = dec
main["break_2019_new_vs_old_pct"] = main_break

# 年ごとの指数（1985=100）
yrs = [y for y in range(1985, 2025)]
idx = pd.DataFrame({"year": yrs})
idx["milk"] = [pr.loc[y, "milk_t"] for y in yrs]
idx["farms"] = [N.loc[y, "farms"] for y in yrs]
idx["parous"] = [N.loc[y, "parous"] for y in yrs]
idx["cows_per_farm"] = idx["parous"] / idx["farms"]
idx["yield_kg"] = 1000 * idx["milk"] / idx["parous"]
for c in ["milk", "farms", "cows_per_farm", "yield_kg", "parous"]:
    idx[c + "_idx"] = 100 * idx[c] / idx[c].iloc[0]
idx.to_csv(R / "index_series.csv", index=False)
main["peak_milk"] = {"year": int(pr["milk_t"].idxmax()), "t": float(pr["milk_t"].max())}
main["milk_1985_2024_t"] = [float(pr.loc[1985, "milk_t"]), float(pr.loc[2024, "milk_t"])]
main["farms"] = {str(y): float(N.loc[y, "farms"]) for y in [1960, 1985, 2000, 2024, 2025]}
main["farms_decline_rate_pct_per_year"] = {f"{a}-{b}": r(100 * ((N.loc[b, "farms"] / N.loc[a, "farms"]) ** (1 / (b - a)) - 1), 2)
                                           for a, b in [(1985, 2000), (2000, 2015), (2015, 2025)]}

# H2：経産牛の減少率と戸数の減少率（1985→2025）
pc = 100 * (N.loc[2025, "parous"] / N.loc[1985, "parous"] - 1); fc = 100 * (N.loc[2025, "farms"] / N.loc[1985, "farms"] - 1)
main["h2"] = {"parous_change_pct": r(pc), "farms_change_pct": r(fc), "ratio": r(pc / fc, 3)}

# H3：北海道の割合と、地域ごとの分解（経産牛 = 戸数 × 1戸あたり）
reg = {}
for g in ["全国", "北海道", "都府県"]:
    S = series(g)
    a, b = S.loc[1985], S.loc[2025]
    reg[g] = {"farms": [float(a.farms), float(b.farms)], "parous": [float(a.parous), float(b.parous)],
              "farms_change_pct": r(100 * (b.farms / a.farms - 1)), "parous_change_pct": r(100 * (b.parous / a.parous - 1)),
              "per_farm": [r(a.parous / a.farms), r(b.parous / b.farms)]}
main["region"] = reg
H = series("北海道"); T = series("都府県")
share = pd.DataFrame({"year": N.index, "hokkaido_share_parous_pct": 100 * H["parous"].reindex(N.index) / N["parous"],
                      "hokkaido_share_farms_pct": 100 * H["farms"].reindex(N.index) / N["farms"],
                      "per_farm_hokkaido": H["parous"].reindex(N.index) / H["farms"].reindex(N.index),
                      "per_farm_tofuken": T["parous"].reindex(N.index) / T["farms"].reindex(N.index)})
share.to_csv(R / "region_share.csv", index=False)
sh = share.set_index("year")
main["hokkaido_share_parous_pct"] = {str(y): r(sh.loc[y, "hokkaido_share_parous_pct"]) for y in [1960, 1985, 2000, 2025]}
main["hokkaido_share_farms_pct"] = {str(y): r(sh.loc[y, "hokkaido_share_farms_pct"]) for y in [1985, 2025]}
cross = sh["hokkaido_share_parous_pct"]
main["hokkaido_parous_exceeds_tofuken_year"] = int(cross[cross > 50].index.min()) if (cross > 50).any() else None

# H4：規模
s2 = sz[(sz.version.isna()) | (sz.version == "旧")].set_index("year") if "version" in sz else sz.set_index("year")
s2 = s2[~s2.index.duplicated()]
s2["ge100_share_pct"] = 100 * s2["ge100"] / s2["adults_total"]
s2[["adults_total", "ge100", "ge100_share_pct"]].to_csv(R / "size_share.csv")
main["ge100_share_pct"] = {str(int(y)): r(v) for y, v in s2["ge100_share_pct"].dropna().items() if int(y) in (1996, 2005, 2015, 2019, 2025)}
f2 = fs[(fs.version.isna()) | (fs.version == "旧")].set_index("year")
main["farms_ge100"] = {str(y): float(f2.loc[y, "farms_ge100"]) for y in [2005, 2015, 2025] if y in f2.index}
main["farms_ge100_share_2025_pct"] = r(100 * f2.loc[2025, "farms_ge100"] / f2.loc[2025, "farms_with_adults"])

m = dec["main_1985_2024"]
main["hypotheses"] = {
    "H1": {"log_scale": m["log_scale"], "log_yield": m["log_yield"], "verdict": "支持" if m["log_scale"] > m["log_yield"] else "外れ"},
    "H2": {"ratio": main["h2"]["ratio"], "verdict": "支持" if main["h2"]["ratio"] <= 0.5 else "外れ"},
    "H3": {"value": main["hokkaido_share_parous_pct"]["2025"], "verdict": "支持" if main["hokkaido_share_parous_pct"]["2025"] > 55 else "外れ"},
    "H4": {"value": r(s2.loc[2025, "ge100_share_pct"]), "verdict": "支持" if s2.loc[2025, "ge100_share_pct"] > 50 else "外れ"},
}
with open(R / "main.json", "w", encoding="utf-8") as f:
    json.dump(main, f, ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=0)[:6000])
