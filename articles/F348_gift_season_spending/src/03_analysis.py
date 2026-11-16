"""お中元・お歳暮の上乗せを年ごとに出し、仮説 H1〜H4 を判定し、頑健性を確かめる（オフライン、乱数なし）。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
BASE_MONTHS = [2, 3, 4, 5, 9, 10]
Y0, Y1 = 2000, 2025


def season_table(m, col="gift_goods", base_months=BASE_MONTHS, base_fn="mean", summer=(6, 7, 8), winter=(11, 12)):
    rows = []
    for y, g in m.groupby("year"):
        g = g.set_index("month")[col]
        if len(g) < 12:
            continue
        b = g.loc[base_months]
        base = float(b.mean() if base_fn == "mean" else b.median())
        s = float(g.loc[list(summer)].sum() - base * len(summer))
        w = float(g.loc[list(winter)].sum() - base * len(winter))
        rows.append(dict(year=int(y), base_month=base, summer_excess=s, winter_excess=w, season_excess=s + w, annual=float(g.sum())))
    t = pd.DataFrame(rows)
    t["season_share_of_annual"] = t["season_excess"] / t["annual"]
    return t


def ratio(t, c, a=Y0, b=Y1):
    return float(t.loc[t.year == b, c].iloc[0] / t.loc[t.year == a, c].iloc[0])


def slope(t, c, exclude=()):
    u = t[(t.year >= Y0) & (t.year <= Y1) & (~t.year.isin(exclude))]
    return float(np.polyfit(u.year, np.log(u[c]), 1)[0])


def main():
    RES.mkdir(exist_ok=True)
    m = pd.read_csv(ROOT / "data" / "gift_monthly.csv")
    p = pd.read_csv(ROOT / "data" / "price_annual.csv")
    lg = pd.read_csv(ROOT / "data" / "gift_annual_long.csv")
    t = season_table(m)
    pers = m.groupby("year")["persons"].mean().round(4)
    t["persons"] = t.year.map(pers)
    for c in ["summer_excess", "winter_excess", "season_excess", "base_month"]:
        t[c + "_per_person"] = t[c] / t["persons"]
    for c in ["money_gifts", "other_social", "consumption", "gift_food"]:
        t[c + "_annual"] = t.year.map(m.groupby("year")[c].sum())
    t.round(4).to_csv(RES / "season_by_year.csv", index=False)

    r = {k: ratio(t, k) for k in ["summer_excess", "winter_excess", "season_excess", "base_month", "annual", "season_excess_per_person",
                                    "money_gifts_annual", "other_social_annual", "consumption_annual"]}
    v = lambda y, c: float(t.loc[t.year == y, c].iloc[0])
    main_ = dict(
        years=[Y0, Y1],
        season_excess_2000=v(Y0, "season_excess"), season_excess_2025=v(Y1, "season_excess"),
        summer_excess_2000=v(Y0, "summer_excess"), summer_excess_2025=v(Y1, "summer_excess"),
        winter_excess_2000=v(Y0, "winter_excess"), winter_excess_2025=v(Y1, "winter_excess"),
        base_month_2000=v(Y0, "base_month"), base_month_2025=v(Y1, "base_month"),
        annual_gift_goods_2000=v(Y0, "annual"), annual_gift_goods_2025=v(Y1, "annual"),
        season_share_2000=v(Y0, "season_share_of_annual"), season_share_2025=v(Y1, "season_share_of_annual"),
        ratios_2025_vs_2000=r,
        log_slope_per_year=dict(season=slope(t, "season_excess"), summer=slope(t, "summer_excess"), winter=slope(t, "winter_excess"),
                                base=slope(t, "base_month")),
        persons_2000=float(pers[Y0]), persons_2025=float(pers[Y1]),
    )
    dec_hh = 1 - r["season_excess"]
    dec_pp = 1 - r["season_excess_per_person"]
    main_["hypotheses"] = {
        "H1": dict(rule="2025年の上乗せ合計が2000年の50%以下なら支持", value=r["season_excess"], verdict="支持" if r["season_excess"] <= 0.5 else "外れ"),
        "H2": dict(rule="お中元の比（2025/2000）がお歳暮の比より小さければ支持", summer=r["summer_excess"], winter=r["winter_excess"],
                   verdict="支持" if r["summer_excess"] < r["winter_excess"] else "外れ"),
        "H3": dict(rule="上乗せの比が、ふだんの月の比より小さければ支持", season=r["season_excess"], base=r["base_month"],
                   verdict="支持" if r["season_excess"] < r["base_month"] else "外れ"),
        "H4": dict(rule="1人あたりの減り方が1世帯あたりの減り方の半分より大きければ支持", decline_household=dec_hh, decline_per_person=dec_pp,
                   verdict="支持" if dec_pp > 0.5 * dec_hh else "外れ"),
    }
    # 長い流れ（1963〜2007年、年平均1か月 → 年額）
    lg["gift_goods_year"] = lg["gift_goods"] * 12
    pk = lg.loc[lg.gift_goods_year.idxmax()]
    # 2000〜2007年の重なり：月の表の年合計と、長い表の年額
    ov = lg[lg.year.between(2000, 2007)][["year", "gift_goods_year"]].merge(t[["year", "annual"]], on="year")
    ov["diff_pct"] = (ov["annual"] / ov["gift_goods_year"] - 1) * 100
    ov.round(3).to_csv(RES / "overlap_check.csv", index=False)
    lg.round(3).to_csv(RES / "long_annual.csv", index=False)
    main_["long_peak_year"] = int(pk.year)
    main_["long_peak_gift_goods_year"] = float(pk.gift_goods_year)
    main_["long_1963_gift_goods_year"] = float(lg.loc[lg.year == 1963, "gift_goods_year"].iloc[0])
    main_["overlap_max_abs_diff_pct"] = float(ov.diff_pct.abs().max())
    main_["annual_2025_vs_peak"] = float(v(Y1, "annual") / pk.gift_goods_year)

    # 頑健性
    rob = []
    def add(name, tt):
        rob.append(dict(check=name, season_ratio=ratio(tt, "season_excess"), summer_ratio=ratio(tt, "summer_excess"),
                        winter_ratio=ratio(tt, "winter_excess"), base_ratio=ratio(tt, "base_month")))
    add("本線（ふだん＝2〜5・9・10月の平均、夏6〜8月、冬11〜12月）", t)
    add("ふだん＝同じ月の中央値", season_table(m, base_fn="median"))
    add("ふだん＝1・2・3・4・5・9・10月の平均（1月を入れる）", season_table(m, base_months=[1, 2, 3, 4, 5, 9, 10]))
    add("ふだん＝9・10月だけ", season_table(m, base_months=[9, 10]))
    add("窓を狭く（夏＝7月、冬＝12月だけ）", season_table(m, summer=(7,), winter=(12,)))
    tr = t.copy()
    pi = p.set_index("year")["price_index_2000"]
    for c in ["summer_excess", "winter_excess", "season_excess", "base_month"]:
        tr[c] = tr[c] / tr.year.map(pi) * 100
    add("物価で割り引く（消費支出の名目と実質の差、2000年＝100）", tr)
    rb = pd.DataFrame(rob)
    rb.round(4).to_csv(RES / "robustness.csv", index=False)
    main_["robustness"] = rb.round(4).to_dict(orient="records")
    main_["slope_excl_2020_2021"] = slope(t, "season_excess", exclude=(2020, 2021))
    main_["price_index_2025"] = float(pi[Y1])
    # 2018年の様式変更：前年比の変化の大きさを、ほかの年と比べる
    t["yoy_log"] = np.log(t["season_excess"]).diff()
    o = t[(t.year >= 2001) & (t.year <= Y1)]
    z = (float(o.loc[o.year == 2018, "yoy_log"].iloc[0]) - float(o.loc[o.year != 2018, "yoy_log"].mean())) / float(o.loc[o.year != 2018, "yoy_log"].std())
    main_["yoy_2018_log"] = float(o.loc[o.year == 2018, "yoy_log"].iloc[0])
    main_["yoy_2018_z"] = z
    (RES / "main.json").write_text(json.dumps(main_, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps({k: main_[k] for k in ["season_excess_2000", "season_excess_2025", "summer_excess_2000", "summer_excess_2025", "winter_excess_2000",
                                            "winter_excess_2025", "base_month_2000", "base_month_2025", "season_share_2000", "season_share_2025", "long_peak_year",
                                            "long_peak_gift_goods_year", "annual_2025_vs_peak", "overlap_max_abs_diff_pct", "slope_excl_2020_2021", "yoy_2018_z"]}, ensure_ascii=False, indent=0))
    print(json.dumps(main_["hypotheses"], ensure_ascii=False))
    print(json.dumps(main_["log_slope_per_year"]), json.dumps(r))
    print(rb.round(3).to_string())


if __name__ == "__main__":
    main()
