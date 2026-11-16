"""仮説 H1〜H4 と頑健性。結果は results/main.json と表 CSV に書く。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "managers_by_size.csv")
SIX = ["5,000人以上", "1,000~4,999人", "300~999人", "100~299人", "30~99人", "10~29人"]
ROLES = ["kacho_up", "kakari_up", "yakuin", "bucho", "kacho", "kakari"]
RJ = {"kacho_up": "課長相当職以上（役員含む）", "kakari_up": "係長相当職以上（役員含む）", "yakuin": "役員",
      "bucho": "部長相当職", "kacho": "課長相当職", "kakari": "係長相当職"}
P = d.pivot_table(index=["role", "year"], columns="size", values="pct")


def v(role, y, s):
    return float(P.loc[(role, y), s])


def r2(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 2)


def spearman(a, b):
    ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


S, L = "10~29人", "5,000人以上"
main = {"source": "厚生労働省「雇用均等基本調査」企業調査 役職別女性管理職（等）割合", "years": sorted(d.year.unique().tolist())}

# 2025年度の表
t25 = pd.DataFrame({RJ[r]: [v(r, 2025, s) for s in SIX + ["10人以上"]] for r in ROLES}, index=SIX + ["10人以上"])
t25.index.name = "企業規模"
t25.round(2).to_csv(R / "table_2025.csv")
main["table_2025"] = {s: {r: r2(v(r, 2025, s)) for r in ROLES} for s in SIX + ["10人以上"]}

# 推移の表（課長相当職以上と係長相当職）
for role in ["kacho_up", "kakari"]:
    tt = P.loc[role][SIX + ["10人以上"]].dropna(how="all")
    tt.round(2).to_csv(R / f"series_{role}.csv")

# H1
ratio = v("kacho_up", 2025, S) / v("kacho_up", 2025, L)
main["H1"] = {"small": r2(v("kacho_up", 2025, S)), "large": r2(v("kacho_up", 2025, L)), "ratio": r2(ratio),
              "result": "当たり" if ratio >= 2 else "外れ"}

# H2
g11 = v("kacho_up", 2011, S) - v("kacho_up", 2011, L)
g25 = v("kacho_up", 2025, S) - v("kacho_up", 2025, L)
main["H2"] = {"gap_2011": r2(g11), "gap_2025": r2(g25),
              "ratio_2011": r2(v("kacho_up", 2011, S) / v("kacho_up", 2011, L)), "ratio_2025": r2(ratio),
              "small_2011": r2(v("kacho_up", 2011, S)), "large_2011": r2(v("kacho_up", 2011, L)),
              "result": "当たり" if g25 < g11 else "外れ"}

# H3
rat = {r: v(r, 2025, S) / v(r, 2025, L) for r in ["yakuin", "bucho", "kacho", "kakari"]}
main["H3"] = {"ratio_by_role_2025": {r: r2(x) for r, x in rat.items()},
              "result": "当たり" if rat["bucho"] > rat["kakari"] else "外れ"}

# H4
up_l = v("kakari", 2025, L) - v("kakari", 2009, L); up_s = v("kakari", 2025, S) - v("kakari", 2009, S)
main["H4"] = {"large_2009": r2(v("kakari", 2009, L)), "large_2025": r2(v("kakari", 2025, L)), "large_up": r2(up_l),
              "small_2009": r2(v("kakari", 2009, S)), "small_2025": r2(v("kakari", 2025, S)), "small_up": r2(up_s),
              "result": "当たり" if up_l > up_s else "外れ"}

# 頑健性
rob = {}
# 1. 役員を除く役職ごとの差（2011→2025）
rob["R1_roles_gap"] = {r: {"gap_2011": r2(v(r, 2011, S) - v(r, 2011, L)), "gap_2025": r2(v(r, 2025, S) - v(r, 2025, L)),
                           "ratio_2011": r2(v(r, 2011, S) / v(r, 2011, L)), "ratio_2025": r2(v(r, 2025, S) / v(r, 2025, L))}
                       for r in ["bucho", "kacho", "kakari"]}
# 2. 3年平均
def avg(role, ys, s):
    return float(np.mean([v(role, y, s) for y in ys]))
E, Lt = [2011, 2013, 2015], [2023, 2024, 2025]
rob["R2_3yr_avg_kacho_up"] = {"early_years": E, "late_years": Lt,
    "small_early": r2(avg("kacho_up", E, S)), "large_early": r2(avg("kacho_up", E, L)),
    "small_late": r2(avg("kacho_up", Lt, S)), "large_late": r2(avg("kacho_up", Lt, L)),
    "gap_early": r2(avg("kacho_up", E, S) - avg("kacho_up", E, L)), "gap_late": r2(avg("kacho_up", Lt, S) - avg("kacho_up", Lt, L)),
    "ratio_early": r2(avg("kacho_up", E, S) / avg("kacho_up", E, L)), "ratio_late": r2(avg("kacho_up", Lt, S) / avg("kacho_up", Lt, L))}
E9 = [2009, 2011, 2013]
rob["R2_3yr_avg_kakari"] = {"early_years": E9, "late_years": Lt,
    "large_up": r2(avg("kakari", Lt, L) - avg("kakari", E9, L)), "small_up": r2(avg("kakari", Lt, S) - avg("kakari", E9, S))}
# 3. 順位相関（規模の小ささ と 割合）
sp = []
for y in sorted(P.loc["kacho_up"].dropna(how="all").index):
    vals6 = [v("kacho_up", y, s) for s in SIX]
    sp.append({"year": int(y), "rho_6sizes": r2(spearman(range(6), vals6)), "rho_5sizes_30plus": r2(spearman(range(5), vals6[:5]))})
rob["R3_spearman_kacho_up"] = sp
pd.DataFrame(sp).to_csv(R / "spearman_kacho_up.csv", index=False)
# 4. 年ごとの向き
yrs = sorted(P.loc["kacho_up"].dropna(how="all").index)
rob["R4_small_gt_large_years"] = {"kacho_up": f"{sum(v('kacho_up', y, S) > v('kacho_up', y, L) for y in yrs)}/{len(yrs)}",
    "kakari": f"{sum(v('kakari', y, S) > v('kakari', y, L) for y in sorted(P.loc['kakari'].dropna(how='all').index) if y != 2003)}/{len([y for y in P.loc['kakari'].dropna(how='all').index if y != 2003])}"}
# 5. 2003年度（30〜99人まで）
rob["R5_2003_kakari_up"] = {s: r2(v("kakari_up", 2003, s)) for s in SIX[:5]}
rob["R5_2025_kakari_up"] = {s: r2(v("kakari_up", 2025, s)) for s in SIX[:5]}
main["robustness"] = rob
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("H1", main["H1"]["result"], "H2", main["H2"]["result"], "H3", main["H3"]["result"], "H4", main["H4"]["result"])
