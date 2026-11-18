"""全国・地方・都道府県の B（再生利用が困難）の割合、仮説の判定、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "data"; R = ROOT / "results"
REG_ORDER = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]


def r1(x, n=1):
    return float(round(float(x), n))


def main():
    p = pd.read_csv(D / "panel.csv")
    nat = p.groupby("year", sort=True)[["total", "A", "B", "reclaimed", "new", "total_n", "A_n", "B_n", "reclaimed_n", "new_n"]].sum(min_count=1)
    nat["B_share"] = nat.B / nat.total * 100
    nat["B_share_n"] = nat.B_n / nat.total_n * 100
    nat.to_csv(R / "national_by_year.csv", float_format="%.3f")

    reg = p.groupby(["region", "year"], sort=True)[["total", "A", "B", "total_n", "B_n"]].sum(min_count=1).reset_index()
    reg["B_share"] = reg.B / reg.total * 100
    reg["region"] = pd.Categorical(reg.region, REG_ORDER, ordered=True)
    reg = reg.sort_values(["region", "year"]).reset_index(drop=True)
    reg.to_csv(R / "region_by_year.csv", index=False, float_format="%.3f")

    p["B_share"] = p.B / p.total * 100
    w = p.pivot(index="pref_code", columns="year", values="B_share")
    prefw = p[p.year == 2024][["pref_code", "pref", "region"]].set_index("pref_code")
    for y in [2011, 2013, 2020, 2021, 2024]:
        prefw[f"B_share_{y}"] = w[y]
    for y in [2013, 2020, 2021, 2024]:
        prefw[f"B_{y}"] = p[p.year == y].set_index("pref_code").B
        prefw[f"total_{y}"] = p[p.year == y].set_index("pref_code").total
    prefw["d_share_2013_2020"] = prefw.B_share_2020 - prefw.B_share_2013
    prefw["d_B_2021_2024"] = prefw.B_2024 - prefw.B_2021
    prefw.to_csv(R / "pref_B_share.csv", float_format="%.3f")

    s = nat.B_share
    main = {"national": {str(y): {"total_ha": int(nat.total[y]), "A_ha": int(nat.A[y]), "B_ha": int(nat.B[y]),
                                   "B_share_pct": r1(s[y]), "reclaimed_ha": int(nat.reclaimed[y]),
                                   "new_ha": (None if pd.isna(nat.new[y]) else int(nat.new[y]))} for y in nat.index}}
    # H1
    h1 = s[2020] - s[2011]
    main["H1"] = {"B_share_2011": r1(s[2011]), "B_share_2020": r1(s[2020]), "diff_pt": r1(h1), "judge": "支持" if h1 >= 15 else "外れ"}
    # H2
    dB = int(nat.B[2024] - nat.B[2021])
    main["H2"] = {"B_2021": int(nat.B[2021]), "B_2024": int(nat.B[2024]), "diff_ha": dB, "pct": r1((nat.B[2024] / nat.B[2021] - 1) * 100), "judge": "支持" if dB < 0 else "外れ"}
    # H3
    rs = reg.pivot(index="region", columns="year", values="B_share")
    up = {str(k): r1(rs.loc[k, 2020] - rs.loc[k, 2013]) for k in REG_ORDER}
    n_up = sum(v > 0 for v in up.values())
    main["H3"] = {"diff_pt_2013_2020": up, "n_up": int(n_up), "judge": "支持" if n_up >= 8 else "外れ"}
    # H4
    h4 = {k: r1(rs.loc[k, 2024]) for k in REG_ORDER}
    ok = all(h4[k] > s[2024] for k in ["中国", "四国", "九州"])
    main["H4"] = {"B_share_2024_by_region": h4, "national_2024": r1(s[2024]), "judge": "支持" if ok else "外れ"}
    main["region_share"] = {k: {str(y): r1(rs.loc[k, y]) for y in [2013, 2020, 2021, 2024]} for k in REG_ORDER}
    # 2021年度からのフロー
    fl = nat.loc[2021:2024, ["new", "reclaimed", "total", "A", "B"]]
    main["flow_2021_2024"] = {"new_mean_ha": int(round(fl.new.mean())), "reclaimed_mean_ha": int(round(fl.reclaimed.mean())),
                              "new_over_reclaimed": r1(fl.new.sum() / fl.reclaimed.sum(), 2),
                              "total_change_2021_2024": int(nat.total[2024] - nat.total[2021])}
    # 頑健性
    rob = {}
    sn = nat.B_share_n
    rob["R1_noyo_only"] = {"2013": r1(sn[2013]), "2020": r1(sn[2020]), "2021": r1(sn[2021]), "2024": r1(sn[2024]),
                           "diff_2013_2020": r1(sn[2020] - sn[2013]), "diff_2021_2024": r1(sn[2024] - sn[2021])}
    rob["R2_start_2013"] = {"2013": r1(s[2013]), "2020": r1(s[2020]), "diff_pt": r1(s[2020] - s[2013])}
    rob["R3_2016_2020"] = {"2015": r1(s[2015]), "2016": r1(s[2016]), "2020": r1(s[2020]), "jump_2015_2016": r1(s[2016] - s[2015]),
                           "diff_2016_2020": r1(s[2020] - s[2016]), "diff_2011_2015": r1(s[2015] - s[2011])}
    med = w.median(axis=0)
    rob["R4_pref_median"] = {str(y): r1(med[y]) for y in [2011, 2013, 2020, 2021, 2024]}
    rob["R4_pref_median"]["diff_2011_2020"] = r1(med[2020] - med[2011])
    n_dec = int((prefw.d_B_2021_2024 < 0).sum())
    top5 = prefw.d_B_2021_2024.sort_values().head(5)
    rob["R5_B_decrease_prefs"] = {"n_pref_B_decreased_2021_2024": n_dec, "n_pref": 47,
                                  "national_decrease_ha": dB, "share_of_5_largest_decreases_pct": r1(top5.sum() / dB * 100)}
    n_up_pref = int((prefw.d_share_2013_2020 > 0).sum())
    rob["R6_pref_share_up_2013_2020"] = {"n_pref_up": n_up_pref}
    main["robustness"] = rob
    json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps({k: main[k] for k in ["H1", "H2", "H3", "H4", "flow_2021_2024"]}, ensure_ascii=False, indent=1))
    print(json.dumps(rob, ensure_ascii=False, indent=1))
    print(json.dumps(main["region_share"], ensure_ascii=False))


if __name__ == "__main__":
    main()
