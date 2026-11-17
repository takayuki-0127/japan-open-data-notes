"""03_analysis.py : 家具・インテリアの支出を、年齢別の移動率・月別の移動者数と比べる。"""
import json
import pathlib

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
RES.mkdir(exist_ok=True)
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]
INTERIOR = ["一般家具", "室内装備・装飾品", "寝具類"]
AGE5 = {"29歳以下": ["20歳~24歳", "25歳~29歳"], "30〜39歳": ["30歳~34歳", "35歳~39歳"], "40〜49歳": ["40歳~44歳", "45歳~49歳"],
        "50〜59歳": ["50歳~54歳", "55歳~59歳"], "60〜69歳": ["60歳~64歳", "65歳~69歳"],
        "70歳以上": ["70歳~74歳", "75歳~79歳", "80歳~84歳", "85歳以上"]}
AGE5_25 = {"再掲25~34歳": ["25歳~29歳", "30歳~34歳"], "再掲35~44歳": ["35歳~39歳", "40歳~44歳"],
           "再掲45~54歳": ["45歳~49歳", "50歳~54歳"], "再掲55~64歳": ["55歳~59歳", "60歳~64歳"],
           "再掲65歳以上": ["65歳~69歳", "70歳~74歳", "75歳~79歳", "80歳~84歳", "85歳以上"]}


def r3(x):
    return None if x is None or pd.isna(x) else round(float(x), 3)


def corr(a, b):
    return float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])


def main():
    a = pd.read_csv(BASE / "data" / "fies_age.csv")
    m = pd.read_csv(BASE / "data" / "fies_month.csv")
    f25 = pd.read_csv(BASE / "data" / "fies_2025_age5.csv")
    mr = pd.read_csv(BASE / "data" / "move_rate_age.csv").set_index("age5")
    mm = pd.read_csv(BASE / "data" / "moves_month.csv")
    mr["total"] = mr["within_pref"] + mr["out_pref"]

    # 年齢別（2013〜2025年の平均、名目）
    ai = a[a.item.isin(INTERIOR)].groupby(["year", "age"]).amount.sum().rename("家具・インテリア").reset_index()
    wide = a.pivot_table(index=["year", "age"], columns="item", values="amount").reset_index().merge(ai, on=["year", "age"])
    wide.to_csv(RES / "age_by_year.csv", index=False)
    items = ["家具・インテリア"] + INTERIOR + ["テーブル・ソファー", "カーテン", "ベッド", "家具・家事用品"]
    prof = wide.groupby("age")[items].mean().loc[["平均"] + AGES].round(1)
    prof.to_csv(RES / "age_profile_mean_2013_2025.csv")
    rate = pd.DataFrame({g: {k: mr.loc[v, k].mean() for k in ["within_pref", "out_pref", "total"]} for g, v in AGE5.items()}).T
    rate.round(3).to_csv(RES / "move_rate_10y.csv")
    ranks = prof.loc[AGES, "家具・インテリア"].sort_values(ascending=False)
    c_main = corr(prof.loc[AGES, "家具・インテリア"], rate.loc[AGES, "total"])
    c_furn = corr(prof.loc[AGES, "一般家具"], rate.loc[AGES, "total"])
    c_in = corr(prof.loc[AGES, "家具・インテリア"], rate.loc[AGES, "within_pref"])
    c_out = corr(prof.loc[AGES, "家具・インテリア"], rate.loc[AGES, "out_pref"])
    corr_items = {it: r3(corr(prof.loc[AGES, it], rate.loc[AGES, "total"])) for it in items}
    # 2025年の5歳ずらしの区分
    w25 = f25.pivot_table(index="age", columns="item", values="value")
    w25.index = [i.replace("~", "〜") if not i.startswith("再掲") else i for i in w25.index]
    w25["家具・インテリア"] = w25[INTERIOR].sum(axis=1)
    rate25 = pd.Series({g: mr.loc[v, "total"].mean() for g, v in AGE5_25.items()})
    c25 = corr(w25.loc[list(AGE5_25), "家具・インテリア"], rate25)
    # 問い直し：世帯数を掛けた総額の割合（2025年）
    sh = w25.loc[AGES, ["世帯数分布", "家具・インテリア", "一般家具"]].copy()
    sh["total_interior"] = sh["世帯数分布"] * sh["家具・インテリア"]
    sh["share_interior_pct"] = sh["total_interior"] / sh["total_interior"].sum() * 100
    sh["share_households_pct"] = sh["世帯数分布"] / sh["世帯数分布"].sum() * 100
    sh["total_furn"] = sh["世帯数分布"] * sh["一般家具"]
    sh["share_furn_pct"] = sh["total_furn"] / sh["total_furn"].sum() * 100
    sh.round(2).to_csv(RES / "share_2025.csv")

    # 月別（各年の月平均=1、2013〜2024年の平均）
    mi = m[m.item.isin(INTERIOR)].groupby(["year", "month"]).amount.sum().rename("家具・インテリア").reset_index()
    mw = m.pivot_table(index=["year", "month"], columns="item", values="amount").reset_index().merge(mi, on=["year", "month"])
    mm2 = mm[(mm.year >= 2013) & (mm.year <= 2024)].copy()
    mw = mw.merge(mm2, on=["year", "month"])
    for k in ["家具・インテリア", "一般家具", "カーテン", "ベッド", "テーブル・ソファー", "movers"]:
        mw[k + "_idx"] = mw[k] / mw.groupby("year")[k].transform("mean")
    mw.round(4).to_csv(RES / "monthly_index_by_year.csv", index=False)

    def season(df):
        return df.groupby("month")[[c for c in df.columns if c.endswith("_idx")]].mean()
    s_all = season(mw)
    s_ex = season(mw[~mw.year.isin([2020, 2021])])
    s_all.round(4).to_csv(RES / "season_2013_2024.csv")
    s_ex.round(4).to_csv(RES / "season_excl_2020_2021.csv")
    ma = lambda s: float(s.loc[[3, 4]].mean())
    # 年ごとの3〜4月の比（振れ）
    yr34 = mw[mw.month.isin([3, 4])].groupby("year")[["家具・インテリア_idx", "一般家具_idx", "movers_idx"]].mean().round(3)
    yr34.to_csv(RES / "march_april_by_year.csv")

    res = {
        "age_profile": prof.loc[["平均"] + AGES, ["家具・インテリア", "一般家具", "室内装備・装飾品", "寝具類"]].to_dict("index"),
        "move_rate_total": rate["total"].round(2).to_dict(),
        "H1": {"top2": list(ranks.index[:2]), "ranking": [[k, r3(v)] for k, v in ranks.items()],
               "result": "支持" if set(ranks.index[:2]) == {"29歳以下", "30〜39歳"} else "外れ"},
        "H2": {"corr_interior_total": r3(c_main), "result": "支持" if c_main >= 0.8 else "外れ"},
        "H3": {"mar_apr_interior": r3(ma(s_all["家具・インテリア_idx"])), "result": "支持" if ma(s_all["家具・インテリア_idx"]) >= 1.2 else "外れ"},
        "H4": {"corr_month": r3(corr(s_all["家具・インテリア_idx"], s_all["movers_idx"])),
               "result": "支持" if corr(s_all["家具・インテリア_idx"], s_all["movers_idx"]) >= 0.5 else "外れ"},
        "movers_mar_apr": r3(ma(s_all["movers_idx"])),
        "season_interior": s_all["家具・インテリア_idx"].round(3).to_dict(),
        "season_movers": s_all["movers_idx"].round(3).to_dict(),
        "robust": {
            "R1_furn_top2": list(prof.loc[AGES, "一般家具"].sort_values(ascending=False).index[:2]),
            "R1_furn_corr_age": r3(c_furn),
            "R1_furn_mar_apr": r3(ma(s_all["一般家具_idx"])),
            "R1_furn_corr_month": r3(corr(s_all["一般家具_idx"], s_all["movers_idx"])),
            "R2_corr_2025_shifted": r3(c25),
            "R3_mar_apr_excl": r3(ma(s_ex["家具・インテリア_idx"])),
            "R3_corr_month_excl": r3(corr(s_ex["家具・インテリア_idx"], s_ex["movers_idx"])),
            "R4_corr_within": r3(c_in), "R4_corr_out": r3(c_out),
            "curtain_mar_apr": r3(ma(s_all["カーテン_idx"])), "curtain_corr_month": r3(corr(s_all["カーテン_idx"], s_all["movers_idx"])),
            "bed_mar_apr": r3(ma(s_all["ベッド_idx"])), "bed_corr_month": r3(corr(s_all["ベッド_idx"], s_all["movers_idx"])),
            "sofa_mar_apr": r3(ma(s_all["テーブル・ソファー_idx"])),
        },
        "corr_age_by_item": corr_items,
        "share_2025": sh[["share_households_pct", "share_interior_pct", "share_furn_pct"]].round(1).to_dict("index"),
        "share_60plus_interior": r3(sh.loc[["60〜69歳", "70歳以上"], "share_interior_pct"].sum()),
        "share_u40_interior": r3(sh.loc[["29歳以下", "30〜39歳"], "share_interior_pct"].sum()),
        "share_60plus_households": r3(sh.loc[["60〜69歳", "70歳以上"], "share_households_pct"].sum()),
        "share_u40_households": r3(sh.loc[["29歳以下", "30〜39歳"], "share_households_pct"].sum()),
        "march_april_by_year_range": [r3(yr34["家具・インテリア_idx"].min()), r3(yr34["家具・インテリア_idx"].max())],
    }
    (RES / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
