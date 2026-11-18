"""自給率の推移、生産と消費への分解、地方別・面積と単収への分解、頑健性。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
NORTH_SOUTH = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def period_mean(df, col, a, b, key="fy"):
    s = df[(df[key] >= a) & (df[key] <= b)]
    assert len(s) == b - a + 1
    return s[col].mean()


def decomp(f, a0, a1, b0, b1, cden="C"):
    P0, P1 = period_mean(f, "P", a0, a1), period_mean(f, "P", b0, b1)
    C0, C1 = period_mean(f, cden, a0, a1), period_mean(f, cden, b0, b1)
    s0, s1 = P0 / C0 * 100, P1 / C1 * 100
    dl = np.log(s1 / s0)
    return {"P0": P0, "P1": P1, "C0": C0, "C1": C1, "ssr0": s0, "ssr1": s1, "ssr_diff_pt": s1 - s0,
            "dlog_ssr": dl, "dlog_P": np.log(P1 / P0), "dlog_C": np.log(C1 / C0),
            "share_from_P": np.log(P1 / P0) / dl, "C_change_pct": (C1 / C0 - 1) * 100}


def main():
    f = pd.read_csv(DATA / "fbs_wheat_fy.csv")
    c = pd.read_csv(DATA / "crop_wheat_region_year.csv")
    f["C_nofeed"] = f["C"] - f["feed"]
    f["ssr_nofeed"] = f["P"] / f["C_nofeed"] * 100
    f["P_ma3"] = f["P"].rolling(3, center=True).mean()
    f["ssr_ma3P"] = f["P_ma3"] / f["C"] * 100
    f.to_csv(RES / "ssr_by_fy.csv", index=False, float_format="%.4f")

    main = {"note": "自給率＝国内生産量÷国内消費仕向量（重量、年度）。1960〜2024年度は令和6年度確報の累年表、2025年度は令和7年度概算。"}
    low = f.loc[f.ssr.idxmin()]
    main["ssr_min"] = {"fy": int(low.fy), "ssr": r(low.ssr, 2), "P": r(low.P, 0), "C": r(low.C, 0)}
    for y in [1960, 1973, 1988, 1990, 2000, 2010, 2015, 2020, 2023, 2024, 2025]:
        row = f[f.fy == y].iloc[0]
        main[f"ssr_{y}"] = r(row.ssr, 2)
        main[f"P_{y}"] = r(row.P, 0); main[f"C_{y}"] = r(row.C, 0)
    hi = f[f.fy >= 1975].loc[lambda d: d.ssr.idxmax()]
    main["ssr_max_since1975"] = {"fy": int(hi.fy), "ssr": r(hi.ssr, 2)}
    # 10年ごとの平均
    dec = []
    for a in range(1960, 2030, 10):
        s = f[(f.fy >= a) & (f.fy <= a + 9)]
        dec.append({"decade": f"{a}年度〜", "n": len(s), "ssr_mean": s.ssr.mean(), "P_mean": s.P.mean(), "C_mean": s.C.mean(), "feed_mean": s.feed.mean()})
    pd.DataFrame(dec).to_csv(RES / "decades.csv", index=False, float_format="%.3f")
    main["decades"] = {d["decade"]: r(d["ssr_mean"], 2) for d in dec}

    # H1・H4：2000〜04 → 2020〜24
    d = decomp(f, 2000, 2004, 2020, 2024)
    main["base_2000_04_to_2020_24"] = {k: r(v, 4) for k, v in d.items()}
    feed0, feed1 = period_mean(f, "feed", 2000, 2004), period_mean(f, "feed", 2020, 2024)
    main["feed_2000_04"] = r(feed0, 1); main["feed_2020_24"] = r(feed1, 1)
    main["C_nofeed_change_pct"] = r((period_mean(f, "C_nofeed", 2020, 2024) / period_mean(f, "C_nofeed", 2000, 2004) - 1) * 100, 2)
    # 1970年代の底からの長い変化
    d70 = decomp(f, 1971, 1975, 2020, 2024)
    main["long_1971_75_to_2020_24"] = {k: r(v, 4) for k, v in d70.items()}

    # H2：地方別の増加
    c5 = lambda y0, y1: c[(c.year >= y0) & (c.year <= y1)].groupby("region", sort=False)[["area_ha", "harvest_t"]].mean()
    a, b = c5(2000, 2004), c5(2020, 2024)
    nat_inc = b.loc["全国", "harvest_t"] - a.loc["全国", "harvest_t"]
    reg = []
    for g in NORTH_SOUTH:
        inc = b.loc[g, "harvest_t"] - a.loc[g, "harvest_t"]
        reg.append({"region": g, "harvest_2000_04": a.loc[g, "harvest_t"], "harvest_2020_24": b.loc[g, "harvest_t"],
                    "increase_t": inc, "share_of_national_increase_pct": inc / nat_inc * 100,
                    "share_of_national_2000_04_pct": a.loc[g, "harvest_t"] / a.loc["全国", "harvest_t"] * 100,
                    "share_of_national_2020_24_pct": b.loc[g, "harvest_t"] / b.loc["全国", "harvest_t"] * 100,
                    "area_2000_04": a.loc[g, "area_ha"], "area_2020_24": b.loc[g, "area_ha"]})
    reg = pd.DataFrame(reg)
    reg.to_csv(RES / "region_increase.csv", index=False, float_format="%.3f")
    sum_reg = reg[["harvest_2000_04", "harvest_2020_24"]].sum()
    main["region_sum_check"] = {"sum_2000_04": r(sum_reg.iloc[0], 0), "nat_2000_04": r(a.loc["全国", "harvest_t"], 0),
                                "sum_2020_24": r(sum_reg.iloc[1], 0), "nat_2020_24": r(b.loc["全国", "harvest_t"], 0)}
    main["national_increase_t"] = r(nat_inc, 0)
    main["hokkaido_share_of_increase_pct"] = r(reg.loc[reg.region == "北海道", "share_of_national_increase_pct"].iloc[0], 2)
    main["hokkaido_share_2000_04_pct"] = r(reg.loc[reg.region == "北海道", "share_of_national_2000_04_pct"].iloc[0], 2)
    main["hokkaido_share_2020_24_pct"] = r(reg.loc[reg.region == "北海道", "share_of_national_2020_24_pct"].iloc[0], 2)
    main["region_increase_t"] = {row.region: r(row.increase_t, 0) for row in reg.itertuples()}
    main["region_share_of_increase_pct"] = {row.region: r(row.share_of_national_increase_pct, 2) for row in reg.itertuples()}

    # H3：面積と単収（収穫量÷面積で平均単収を作る）
    ay = []
    for g in ["全国", "北海道", "都府県"]:
        A0, A1 = a.loc[g, "area_ha"], b.loc[g, "area_ha"]
        Q0, Q1 = a.loc[g, "harvest_t"], b.loc[g, "harvest_t"]
        Y0, Y1 = Q0 / A0, Q1 / A1
        dq = np.log(Q1 / Q0)
        ay.append({"region": g, "area_2000_04": A0, "area_2020_24": A1, "yield_t_per_ha_2000_04": Y0, "yield_t_per_ha_2020_24": Y1,
                   "dlog_harvest": dq, "dlog_area": np.log(A1 / A0), "dlog_yield": np.log(Y1 / Y0),
                   "area_share": np.log(A1 / A0) / dq, "yield_share": np.log(Y1 / Y0) / dq})
    ay = pd.DataFrame(ay)
    ay.to_csv(RES / "area_yield_decomp.csv", index=False, float_format="%.4f")
    main["area_yield"] = {row.region: {"area_pct": r((np.exp(row.dlog_area) - 1) * 100, 2), "yield_pct": r((np.exp(row.dlog_yield) - 1) * 100, 2),
                                       "harvest_pct": r((np.exp(row.dlog_harvest) - 1) * 100, 2), "yield_share": r(row.yield_share, 3),
                                       "yield_kg10a_0": r(row.yield_t_per_ha_2000_04 * 100, 1), "yield_kg10a_1": r(row.yield_t_per_ha_2020_24 * 100, 1)}
                          for row in ay.itertuples()}

    # 北海道の単収の振れ（2000〜04年産平均＝1）
    h = c[(c.region == "北海道") & (c.year >= 2000)].set_index("year")
    yi = (h.harvest_t / h.area_ha) / (a.loc["北海道", "harvest_t"] / a.loc["北海道", "area_ha"])
    main["hokkaido_yield_index"] = {"min": r(yi.min(), 3), "min_year": int(yi.idxmin()), "max": r(yi.max(), 3), "max_year": int(yi.idxmax())}

    # 照合：需給表の生産量（千t）と作物統計の全国収穫量
    nat = c[c.region == "全国"].set_index("year")["harvest_t"] / 1000
    j = f.set_index("fy")["P"].to_frame().join(nat.rename("crop"), how="inner")
    j = j[j.index >= 1960]
    j["diff"] = j["P"] - j["crop"]
    j.to_csv(RES / "check_fbs_vs_crop.csv", float_format="%.3f")
    main["check_fbs_vs_crop"] = {"years": int(len(j)), "max_abs_diff_kt": r(j["diff"].abs().max(), 3),
                                 "n_exact": int((j["diff"].abs() < 0.5).sum())}

    # 頑健性
    rows = []
    def add(name, dd, note=""):
        rows.append({"check": name, "ssr0": dd["ssr0"], "ssr1": dd["ssr1"], "diff_pt": dd["ssr_diff_pt"],
                     "share_from_P": dd["share_from_P"], "C_change_pct": dd["C_change_pct"], "note": note})
    add("基本：2000〜04年度平均→2020〜24年度平均", d)
    one = lambda y0, y1: decomp(f, y0, y0, y1, y1)
    add("単年：2000年度→2024年度", one(2000, 2024))
    add("3年平均：2000〜02年度→2022〜24年度", decomp(f, 2000, 2002, 2022, 2024))
    add("2025年度（概算）を含む：2001〜05年度→2021〜25年度", decomp(f, 2001, 2005, 2021, 2025))
    add("飼料用を除く分母", decomp(f, 2000, 2004, 2020, 2024, cden="C_nofeed"), "P÷（C−飼料用）")
    f2 = f.copy(); f2["P"] = f2["P_ma3"]
    add("生産量を中心3か年移動平均に", decomp(f2, 2001, 2005, 2019, 2023), "移動平均が取れる2001〜05→2019〜23")
    add("1990年代を起点：1995〜99年度→2020〜24年度", decomp(f, 1995, 1999, 2020, 2024))
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")
    main["robustness"] = [{k: (r(v, 3) if isinstance(v, float) else v) for k, v in row.items()} for row in rows]
    # 年ごとの振れ（2010年度以降）
    s = f[(f.fy >= 2010) & (f.fy <= 2025)]
    main["ssr_2010_25"] = {"min": r(s.ssr.min(), 2), "min_fy": int(s.loc[s.ssr.idxmin(), "fy"]), "max": r(s.ssr.max(), 2),
                           "max_fy": int(s.loc[s.ssr.idxmax(), "fy"]), "sd_P": r(s.P.std(ddof=1), 1), "sd_C": r(s.C.std(ddof=1), 1)}
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: main[k] for k in ["ssr_min", "base_2000_04_to_2020_24", "hokkaido_share_of_increase_pct", "area_yield", "check_fbs_vs_crop", "region_sum_check", "ssr_2010_25", "decades"]}, ensure_ascii=False, indent=1))
    print(rob.to_string())


if __name__ == "__main__":
    main()
