"""全国の推移、本館・分館、都道府県の減少率と市町村数の減少率の順位相関、地方別、利用者。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"; RES.mkdir(exist_ok=True)
SEED = 20261116
nat = pd.read_csv(BASE / "data" / "national.csv", index_col="year")
pref = pd.read_csv(BASE / "data" / "pref.csv", index_col="pref")
P = pref.drop(index="全国")


def pct(a, b):
    return round((b / a - 1) * 100, 1)


main = {}
# H1 全国（類似を含む）
fac = nat["facilities_incl_similar"].dropna()
peak_y = int(fac.idxmax())
main["H1"] = {"peak_year": peak_y, "peak": int(fac.max()), "y2024": int(fac.loc[2024]), "change_pct": pct(fac.max(), fac.loc[2024]),
              "peak_since_1960_year": int(fac.loc[1960:].idxmax()), "peak_since_1960": int(fac.loc[1960:].max()),
              "change_since_1960_peak_pct": pct(fac.loc[1960:].max(), fac.loc[2024]),
              "y1999": int(fac.loc[1999]), "change_since_1999_pct": pct(fac.loc[1999], fac.loc[2024]),
              "y2002": int(fac.loc[2002]), "change_since_2002_pct": pct(fac.loc[2002], fac.loc[2024])}
main["H1"]["judge"] = "支持" if main["H1"]["change_pct"] <= -25 else "外れ"
main["national_series"] = {str(int(y)): int(v) for y, v in fac.items()}

# H2 本館・分館（類似を除く公民館、全国）
z = pref.loc["全国"]
main["H2"] = {"honkan_2002": int(z.honkan_2002), "honkan_2024": int(z.honkan_2024), "honkan_pct": pct(z.honkan_2002, z.honkan_2024),
              "bunkan_2002": int(z.bunkan_2002), "bunkan_2024": int(z.bunkan_2024), "bunkan_pct": pct(z.bunkan_2002, z.bunkan_2024),
              "total_2002": int(z.total_2002), "total_2024": int(z.total_2024), "total_pct": pct(z.total_2002, z.total_2024),
              "honkan_2005": int(z.honkan_2005), "bunkan_2005": int(z.bunkan_2005), "total_2005": int(z.total_2005),
              "bunkan_share_of_decline": round((z.bunkan_2002 - z.bunkan_2024) / (z.total_2002 - z.total_2024), 3)}
main["H2"]["judge"] = "支持" if main["H2"]["bunkan_pct"] < main["H2"]["honkan_pct"] else "外れ"
main["muni"] = {"muni_2002": int(z.muni_2002), "muni_2024": int(z.muni_2024), "muni_pct": pct(z.muni_2002, z.muni_2024),
                "towns_villages_2002": int(z.town_2002 + z.village_2002), "towns_villages_2024": int(z.town_2024 + z.village_2024),
                "kominkan_per_muni_2002": round(z.total_2002 / z.muni_2002, 2), "kominkan_per_muni_2024": round(z.total_2024 / z.muni_2024, 2)}

# 都道府県の表（北から南の順のまま）
t = pd.DataFrame(index=P.index)
t["region"] = P["region"]
for c in ["total", "honkan", "bunkan", "muni"]:
    t[f"{c}_2002"] = P[f"{c}_2002"]; t[f"{c}_2024"] = P[f"{c}_2024"]
    t[f"{c}_chg_pct"] = (P[f"{c}_2024"] / P[f"{c}_2002"] - 1) * 100
t["tv_chg_pct"] = ((P.town_2024 + P.village_2024) / (P.town_2002 + P.village_2002) - 1) * 100
t["total_chg_2005_pct"] = (P.total_2024 / P.total_2005 - 1) * 100
t["muni_chg_2005_pct"] = (P.muni_2024 / P.muni_2005 - 1) * 100
t.round(2).to_csv(RES / "pref_changes.csv")


def spear(x, y):
    r, p = stats.spearmanr(x, y)
    return float(r), float(p)


rng = np.random.default_rng(SEED)
x, y = t["muni_chg_pct"].to_numpy(), t["total_chg_pct"].to_numpy()
r0, p0 = spear(x, y)
bs = []
for _ in range(2000):
    i = rng.integers(0, len(x), len(x))
    bs.append(spear(x[i], y[i])[0])
main["H3"] = {"spearman": round(r0, 3), "p": round(p0, 4), "boot_ci": [round(float(np.quantile(bs, 0.025)), 3), round(float(np.quantile(bs, 0.975)), 3)],
              "n": int(len(x)), "judge": "支持" if r0 >= 0.3 else "外れ"}

# 頑健性
rob = []
def add(name, xx, yy, note=""):
    r, p = spear(xx, yy)
    rob.append({"check": name, "rho": round(r, 3), "p": round(p, 4), "n": int(len(xx)), "ge_0.3": bool(r >= 0.3), "note": note})
add("主（公民館計、2002→2024年度、スピアマン）", t.muni_chg_pct, t.total_chg_pct)
add("本館だけ", t.muni_chg_pct, t.honkan_chg_pct)
add("分館だけ（2002年に分館が10館以上の県）", t[t.bunkan_2002 >= 10].muni_chg_pct, t[t.bunkan_2002 >= 10].bunkan_chg_pct)
pr, pp = stats.pearsonr(t.muni_chg_pct, t.total_chg_pct)
rob.append({"check": "ピアソンの相関", "rho": round(float(pr), 3), "p": round(float(pp), 4), "n": 47, "ge_0.3": bool(pr >= 0.3), "note": "順位でなく値"})
nh = t.drop(index="北海道")
add("北海道を除く", nh.muni_chg_pct, nh.total_chg_pct)
add("2005→2024年度", t.muni_chg_2005_pct, t.total_chg_2005_pct, "合併の途中の年から")
add("市町村数の代わりに町と村の数", t.tv_chg_pct, t.total_chg_pct)
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
main["robustness"] = rob.to_dict(orient="records")

# 地方別
reg_order = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
g = P.groupby("region")[["total_2002", "total_2024", "honkan_2002", "honkan_2024", "bunkan_2002", "bunkan_2024", "muni_2002", "muni_2024"]].sum().loc[reg_order]
for c in ["total", "honkan", "bunkan", "muni"]:
    g[f"{c}_chg_pct"] = (g[f"{c}_2024"] / g[f"{c}_2002"] - 1) * 100
g.round(2).to_csv(RES / "region_changes.csv")
main["region"] = {r: {"total_2002": int(g.loc[r, "total_2002"]), "total_2024": int(g.loc[r, "total_2024"]),
                      "total_chg_pct": round(g.loc[r, "total_chg_pct"], 1), "muni_chg_pct": round(g.loc[r, "muni_chg_pct"], 1),
                      "bunkan_chg_pct": round(g.loc[r, "bunkan_chg_pct"], 1)} for r in reg_order}
main["pref_counts"] = {"n_decreased": int((t.total_chg_pct < 0).sum()), "n_increased_or_same": int((t.total_chg_pct >= 0).sum()),
                       "n_muni_unchanged": int((t.muni_chg_pct == 0).sum()),
                       "median_total_chg_pct": round(float(t.total_chg_pct.median()), 1),
                       "median_total_chg_pct_muni_unchanged": round(float(t[t.muni_chg_pct == 0].total_chg_pct.median()), 1) if (t.muni_chg_pct == 0).any() else None,
                       "muni_unchanged_prefs": list(t[t.muni_chg_pct == 0].index)}

# H4 利用者（類似を含む、千人、年度間）÷次の調査年度の館数
u = nat["users_thousand_fy"].dropna()
pairs = []
for fy in u.index:
    nxt = [y for y in fac.index if y > fy]
    if nxt:
        pairs.append({"users_fy": int(fy), "facility_year": int(min(nxt)), "users_thousand": float(u.loc[fy]), "facilities": float(fac.loc[min(nxt)]),
                      "users_per_facility_thousand": float(u.loc[fy]) / float(fac.loc[min(nxt)])})
up = pd.DataFrame(pairs)
up.round(3).to_csv(RES / "users_per_facility.csv", index=False)
a = up[up.users_fy == 2007].iloc[0]; b = up[up.users_fy == 2023].iloc[0]; c17 = up[up.users_fy == 2017].iloc[0]
main["H4"] = {"users_2007": int(a.users_thousand), "users_2023": int(b.users_thousand), "users_chg_pct": pct(a.users_thousand, b.users_thousand),
              "fac_2008": int(a.facilities), "fac_2024": int(b.facilities), "fac_chg_pct": pct(a.facilities, b.facilities),
              "per_fac_2007": round(a.users_per_facility_thousand, 2), "per_fac_2023": round(b.users_per_facility_thousand, 2),
              "per_fac_chg_pct": pct(a.users_per_facility_thousand, b.users_per_facility_thousand),
              "per_fac_2017": round(c17.users_per_facility_thousand, 2), "per_fac_2007_2017_chg_pct": pct(a.users_per_facility_thousand, c17.users_per_facility_thousand)}
main["H4"]["judge"] = "外れ" if main["H4"]["per_fac_chg_pct"] < 0 else "支持"

(RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
print(json.dumps({k: main[k] for k in ["H1", "H2", "muni", "H3", "H4", "region", "pref_counts"]}, ensure_ascii=False, indent=1))
print(rob.to_string())
