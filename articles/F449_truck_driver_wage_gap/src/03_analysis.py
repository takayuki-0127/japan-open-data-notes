"""差の計算（時間あたり・年間・年齢をそろえた比較）、仮説の判定、頑健性。results/ に CSV と main.json を出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
df = pd.read_csv(ROOT / "data" / "wage_long.csv")
df["hourly_sched"] = df.shoteinai * 1000 / df.hours_sched                 # 円/時間
df["annual_pay"] = df.kimatte * 12 + df.bonus                              # 千円/年
df["annual_hours"] = (df.hours_sched + df.hours_ot) * 12                   # 時間/年
df["hourly_total"] = df.annual_pay * 1000 / df.annual_hours                # 円/時間
df["ot_pay_share"] = (df.kimatte - df.shoteinai) / df.kimatte * 100        # きまって支給のうち所定内以外（主に残業代）の割合

tot = df[df.age_class == "計"].set_index(["year", "who"])
YEARS = list(range(2009, 2026))


def drv(kind, y):
    """運転者の行（2019年までは男、2020年からは男女計を主に使う）。"""
    return tot.loc[(y, f"{kind}_male" if y <= 2019 else f"{kind}_total")]


def gap(a, b):
    return (a / b - 1) * 100


rows = []
for y in YEARS:
    A, M = tot.loc[(y, "all_total")], tot.loc[(y, "all_male")]
    for kind in ["large", "other"]:
        D = drv(kind, y); Dm = tot.loc[(y, f"{kind}_male")]
        rows.append(dict(
            year=y, kind=kind,
            drv_hourly_sched=D.hourly_sched, all_hourly_sched=A.hourly_sched,
            gap_hourly_sched_vs_total=gap(D.hourly_sched, A.hourly_sched),
            gap_hourly_sched_male_vs_male=gap(Dm.hourly_sched, M.hourly_sched),
            gap_annual_pay_vs_total=gap(D.annual_pay, A.annual_pay),
            ratio_annual_hours_vs_total=D.annual_hours / A.annual_hours,
            gap_hourly_total_vs_total=gap(D.hourly_total, A.hourly_total),
            drv_ot_hours=D.hours_ot, all_ot_hours=A.hours_ot,
            drv_sched_hours=D.hours_sched, drv_age=D.age, all_age=A.age,
            drv_ot_pay_share=D.ot_pay_share, all_ot_pay_share=A.ot_pay_share,
        ))
g = pd.DataFrame(rows)

# 年齢をそろえた比較：年齢階級ごとに 運転者 ÷ 産業計の男、運転者の労働者数で重みづけ
ages = df[df.age_class != "計"]
adj = []
for y in YEARS:
    M = ages[(ages.year == y) & (ages.who == "all_male")].set_index("age_class")
    for kind in ["large", "other"]:
        who = f"{kind}_male" if y <= 2019 else f"{kind}_total"
        D = ages[(ages.year == y) & (ages.who == who)].set_index("age_class")
        D = D[(D.workers > 0) & (D.hours_sched > 0) & (D.shoteinai > 0)]
        common = [a for a in D.index if a in M.index and M.loc[a, "hours_sched"] > 0]
        w = D.loc[common, "workers"] / D.loc[common, "workers"].sum()
        ratio = (D.loc[common, "hourly_sched"] / M.loc[common, "hourly_sched"])
        # 運転者の年齢構成で産業計の男の時給を平均したもの（年齢をそろえた相手）
        m_std = (w * M.loc[common, "hourly_sched"]).sum()
        adj.append(dict(year=y, kind=kind, gap_age_matched_male=(np.sum(w * ratio) - 1) * 100,
                        gap_vs_age_std_male=gap(tot.loc[(y, who)].hourly_sched, m_std), n_age=len(common)))
g = g.merge(pd.DataFrame(adj), on=["year", "kind"])
g.to_csv(R / "gap_by_year.csv", index=False, float_format="%.4f")

L = g[g.kind == "large"].set_index("year"); O = g[g.kind == "other"].set_index("year")
avg = lambda s, ys: float(s.loc[ys].mean())
main = {}
for nm, T in [("large", L), ("other", O)]:
    c = "gap_hourly_sched_vs_total"
    main[nm] = dict(
        gap_hourly_2025=round(float(T.loc[2025, c]), 1),
        gap_annual_pay_2025=round(float(T.loc[2025, "gap_annual_pay_vs_total"]), 1),
        hours_ratio_2025=round(float(T.loc[2025, "ratio_annual_hours_vs_total"]), 3),
        gap_hourly_total_2025=round(float(T.loc[2025, "gap_hourly_total_vs_total"]), 1),
        gap_hourly_2009=round(float(T.loc[2009, c]), 1),
        gap_hourly_2019=round(float(T.loc[2019, c]), 1),
        gap_hourly_2020=round(float(T.loc[2020, c]), 1),
        avg_2009_11=round(avg(T[c], [2009, 2010, 2011]), 1), avg_2017_19=round(avg(T[c], [2017, 2018, 2019]), 1),
        avg_2020_21=round(avg(T[c], [2020, 2021]), 1), avg_2024_25=round(avg(T[c], [2024, 2025]), 1),
        gap_male_vs_male_2025=round(float(T.loc[2025, "gap_hourly_sched_male_vs_male"]), 1),
        gap_age_matched_2025=round(float(T.loc[2025, "gap_age_matched_male"]), 1),
        gap_age_matched_2009=round(float(T.loc[2009, "gap_age_matched_male"]), 1),
        gap_age_matched_2019=round(float(T.loc[2019, "gap_age_matched_male"]), 1),
        ot_2022_23=round(avg(T.drv_ot_hours, [2022, 2023]), 1), ot_2024_25=round(avg(T.drv_ot_hours, [2024, 2025]), 1),
        ot_2024=float(T.loc[2024, "drv_ot_hours"]), ot_2025=float(T.loc[2025, "drv_ot_hours"]),
        ot_2019=float(T.loc[2019, "drv_ot_hours"]), all_ot_2025=float(T.loc[2025, "all_ot_hours"]),
        hourly_2025_yen=round(float(T.loc[2025, "drv_hourly_sched"])), all_hourly_2025_yen=round(float(T.loc[2025, "all_hourly_sched"])),
        drv_age_2025=float(T.loc[2025, "drv_age"]), all_age_2025=float(T.loc[2025, "all_age"]),
        ot_pay_share_2025=round(float(T.loc[2025, "drv_ot_pay_share"]), 1), all_ot_pay_share_2025=round(float(T.loc[2025, "all_ot_pay_share"]), 1),
        ot_pay_share_2023=round(float(T.loc[2023, "drv_ot_pay_share"]), 1),
        ot_pay_share_2019=round(float(T.loc[2019, "drv_ot_pay_share"]), 1),
        ot_pay_share_2009=round(float(T.loc[2009, "drv_ot_pay_share"]), 1),
    )
    main[nm]["narrow_old"] = round(main[nm]["avg_2009_11"] * -1 - main[nm]["avg_2017_19"] * -1, 1)  # 正なら縮んだ
    main[nm]["narrow_new"] = round(main[nm]["avg_2020_21"] * -1 - main[nm]["avg_2024_25"] * -1, 1)

l = main["large"]; o = main["other"]
main["hypotheses"] = {
    "H1": "支持" if l["gap_hourly_total_2025"] < l["gap_annual_pay_2025"] else "外れ",
    "H2": "支持" if max(l["narrow_old"], l["narrow_new"]) >= 2 else "外れ",
    "H3": "支持" if (l["gap_age_matched_2025"] - l["gap_hourly_2025"]) <= -5 else "外れ",
    "H4": "支持" if (l["ot_2024_25"] < l["ot_2022_23"] and o["ot_2024_25"] < o["ot_2022_23"]) else "外れ",
}
main["h3_diff_pt"] = round(l["gap_age_matched_2025"] - l["gap_hourly_2025"], 1)

# 頑健性
rb = []
def add(name, val_large, val_other, note):
    rb.append(dict(check=name, large=round(val_large, 1), other=round(val_other, 1), note=note))
c = "gap_hourly_sched_vs_total"
add("基本：所定内の時間あたり、男女計と比較、縮み（2009-11→2017-19）", l["narrow_old"], o["narrow_old"], "ポイント、正は縮み")
add("基本：同、縮み（2020-21→2024-25）", l["narrow_new"], o["narrow_new"], "ポイント、正は縮み")
for nm, col in [("相手を男にする（運転者も男）", "gap_hourly_sched_male_vs_male"), ("年間の総額÷総時間", "gap_hourly_total_vs_total"), ("年齢をそろえた男と比較", "gap_age_matched_male")]:
    add(nm + "、縮み（2009-11→2017-19）", avg(L[col], [2017, 2018, 2019]) - avg(L[col], [2009, 2010, 2011]), avg(O[col], [2017, 2018, 2019]) - avg(O[col], [2009, 2010, 2011]), "ポイント、正は縮み")
    add(nm + "、縮み（2020-21→2024-25）", (avg(L[col], [2024, 2025]) - avg(L[col], [2020, 2021])), (avg(O[col], [2024, 2025]) - avg(O[col], [2020, 2021])), "ポイント、正は縮み")
add("2020年を除く：縮み（2021→2024-25）", avg(L[c], [2024, 2025]) - float(L.loc[2021, c]), avg(O[c], [2024, 2025]) - float(O.loc[2021, c]), "ポイント、正は縮み")
add("端の年1つでなく傾き：2009-2019の1年あたり", float(np.polyfit(L.loc[2009:2019].index, L.loc[2009:2019, c], 1)[0]), float(np.polyfit(O.loc[2009:2019].index, O.loc[2009:2019, c], 1)[0]), "ポイント/年、正は縮み")
add("端の年1つでなく傾き：2020-2025の1年あたり", float(np.polyfit(L.loc[2020:2025].index, L.loc[2020:2025, c], 1)[0]), float(np.polyfit(O.loc[2020:2025].index, O.loc[2020:2025, c], 1)[0]), "ポイント/年、正は縮み")
add("2019→2020年の段差（分類・推計の変更）", float(L.loc[2020, c] - L.loc[2019, c]), float(O.loc[2020, c] - O.loc[2019, c]), "ポイント")
rbd = pd.DataFrame(rb)
rbd.to_csv(R / "robustness.csv", index=False)
rbi = rbd.set_index("check")
main["robust"] = {k: {"large": float(v["large"]), "other": float(v["other"])} for k, v in rbi.iterrows()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(rbd.to_string())
