"""問い直し（結果を見てから足した）。
1. 7月だけの上乗せが大きく減った（26%に）のは、お中元の時期が6月に早まったからか？ 月ごとの上乗せの割合を見る。
2. 上乗せの中身（食べ物か、それ以外の物か）は変わったか？
3. 2020年（感染症で帰省・訪問が減った年）に、贈答品の上乗せはどう動いたか？"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
BASE_MONTHS = [2, 3, 4, 5, 9, 10]
SEASON = [6, 7, 8, 11, 12]


def month_excess(m, col):
    rows = []
    for y, g in m.groupby("year"):
        g = g.set_index("month")[col]
        base = float(g.reindex(BASE_MONTHS).mean())  # 2026年は10月がまだないので、ある月だけの平均
        rec = dict(year=int(y))
        for mo in SEASON:
            rec[f"m{mo}"] = float(g.loc[mo] - base) if mo in g.index else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def main():
    m = pd.read_csv(ROOT / "data" / "gift_monthly.csv")
    e = month_excess(m, "gift_goods")
    e["summer"] = e[["m6", "m7", "m8"]].sum(axis=1)
    e["june_share_of_summer"] = e["m6"] / e["summer"]
    e["july_share_of_summer"] = e["m7"] / e["summer"]
    e["winter"] = e[["m11", "m12"]].sum(axis=1)
    e["nov_share_of_winter"] = e["m11"] / e["winter"]
    e.loc[e.year == 2026, ["m11", "m12", "winter", "nov_share_of_winter"]] = np.nan
    e.round(4).to_csv(RES / "requestion_month_excess.csv", index=False)

    # 中身：食べ物（交際費の食料）とそれ以外の物
    f = month_excess(m, "gift_food")
    comp = pd.DataFrame(dict(year=e.year, season_food=f[["m6", "m7", "m8", "m11", "m12"]].sum(axis=1), season_all=e["summer"] + e["winter"]))
    comp = comp[comp.year <= 2025]
    comp["food_share"] = comp["season_food"] / comp["season_all"]
    comp.round(4).to_csv(RES / "requestion_food_share.csv", index=False)

    g = lambda d, y, c: float(d.loc[d.year == y, c].iloc[0])
    avg = lambda d, ys, c: float(d.loc[d.year.isin(ys), c].mean())
    # 5年ずつの平均で、6月・7月の割合の変化を見る（1年の揺れをならす）
    out = dict(
        june_share_2000_04=avg(e, range(2000, 2005), "june_share_of_summer"), june_share_2021_25=avg(e, range(2021, 2026), "june_share_of_summer"),
        july_share_2000_04=avg(e, range(2000, 2005), "july_share_of_summer"), july_share_2021_25=avg(e, range(2021, 2026), "july_share_of_summer"),
        nov_share_2000_04=avg(e, range(2000, 2005), "nov_share_of_winter"), nov_share_2021_25=avg(e, range(2021, 2025 + 1), "nov_share_of_winter"),
        m6_2000=g(e, 2000, "m6"), m6_2025=g(e, 2025, "m6"), m7_2000=g(e, 2000, "m7"), m7_2025=g(e, 2025, "m7"),
        m8_2000=g(e, 2000, "m8"), m8_2025=g(e, 2025, "m8"), m11_2000=g(e, 2000, "m11"), m11_2025=g(e, 2025, "m11"),
        m12_2000=g(e, 2000, "m12"), m12_2025=g(e, 2025, "m12"),
        summer_2026=g(e, 2026, "summer"), summer_2025=g(e, 2025, "summer"),
        food_share_2000_04=avg(comp, range(2000, 2005), "food_share"), food_share_2021_25=avg(comp, range(2021, 2026), "food_share"),
    )
    # 2020年：前の3年（2017〜2019）の平均と比べる
    s = pd.read_csv(RES / "season_by_year.csv")
    for c in ["summer_excess", "winter_excess", "base_month", "other_social_annual", "money_gifts_annual"]:
        out[f"{c}_2020_vs_2017_19"] = float(s.loc[s.year == 2020, c].iloc[0] / s.loc[s.year.between(2017, 2019), c].mean())
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
