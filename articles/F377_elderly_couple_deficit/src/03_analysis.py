"""03_analysis.py : 高齢夫婦無職世帯の不足分（実支出 − 実収入）の推移・分け方・埋め方・収入区分の違いと頑健性（オフライン）。
出力：results/series.csv, results/decomposition.csv, results/fill.csv, results/income_class.csv,
      results/robustness.csv, results/multiply.csv, results/main.json
"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

MAIN = "couple_6560"


def r0(x):
    return int(round(float(x)))


def r1(x):
    return round(float(x), 1)


def load():
    df = pd.read_csv(DATA / "kakei_elderly_long.csv")
    cpi = pd.read_csv(DATA / "cpi_annual.csv")
    w = df.pivot_table(index=["group", "year"], columns="item", values="value").reset_index()
    w = w.merge(cpi[["year", "deflator_to_2025"]], on="year", how="left")
    w["deficit"] = w["実支出"] - w["実収入"]
    w["deficit_regular"] = w["実支出"] - w["経常収入"]  # 特別収入を除いた不足分
    w["work"] = w["勤め先収入"] + w["事業・内職収入"]
    w["inc_other"] = (w["実収入"] - w["公的年金給付"] - w["他の社会保障給付"] - w["work"]
                      - w["財産収入"] - w["特別収入"])
    # 埋め方（実支出 − 実収入 ＝ 以下の合計）
    w["fill_deposit"] = w["預貯金引出"] - w["預貯金"]
    w["fill_insurance"] = w["保険金"] - w["保険料"]
    w["fill_securities"] = w["有価証券売却"] - w["有価証券購入"]
    w["fill_cash"] = w["繰入金"] - w["繰越金"]
    w["fill_other"] = ((w["実収入以外の受取(繰入金を除く)"] - w["預貯金引出"] - w["保険金"] - w["有価証券売却"])
                       - (w["実支出以外の支払(繰越金を除く)"] - w["預貯金"] - w["保険料"] - w["有価証券購入"]))
    return w.sort_values(["group", "year"]).reset_index(drop=True)


def period_mean(g, cols, y0, y1, real=False, drop=()):
    s = g[(g["year"] >= y0) & (g["year"] <= y1) & (~g["year"].isin(drop))]
    out = {}
    for c in cols:
        v = s[c] * (s["deflator_to_2025"] if real else 1.0)
        out[c] = float(v.mean())
    return out


DEC_COLS = ["deficit", "実収入", "消費支出", "非消費支出", "公的年金給付", "他の社会保障給付", "work",
            "財産収入", "特別収入", "inc_other"]


def decompose(g, a, b, real=True, drop=()):
    A = period_mean(g, DEC_COLS, a[0], a[1], real, drop)
    B = period_mean(g, DEC_COLS, b[0], b[1], real, drop)
    d = {c: B[c] - A[c] for c in DEC_COLS}
    contrib = {
        "消費支出の増減": d["消費支出"],
        "非消費支出の増減": d["非消費支出"],
        "実収入の増減（符号を反転）": -d["実収入"],
    }
    inc = {
        "公的年金給付": -d["公的年金給付"],
        "他の社会保障給付": -d["他の社会保障給付"],
        "勤め先・事業収入": -d["work"],
        "財産収入": -d["財産収入"],
        "特別収入": -d["特別収入"],
        "その他の収入": -d["inc_other"],
    }
    return A, B, d, contrib, inc


def main():
    w = load()
    g = w[w["group"] == MAIN].copy()

    # 1) 推移
    ser = g[["year", "集計世帯数", "世帯主の年齢", "実収入", "公的年金給付", "可処分所得", "消費支出", "非消費支出",
             "実支出", "deficit", "deficit_regular", "特別収入", "deflator_to_2025"]].copy()
    ser["deficit_real2025"] = ser["deficit"] * ser["deflator_to_2025"]
    ser["income_real2025"] = ser["実収入"] * ser["deflator_to_2025"]
    ser["consumption_real2025"] = ser["消費支出"] * ser["deflator_to_2025"]
    ser["pension_real2025"] = ser["公的年金給付"] * ser["deflator_to_2025"]
    ser["deficit_share_of_consumption_pct"] = ser["deficit"] / ser["消費支出"] * 100
    ser["pension_share_of_income_pct"] = ser["公的年金給付"] / ser["実収入"] * 100
    ser.to_csv(RES / "series.csv", index=False, float_format="%.2f")

    # 定義の違う世帯も並べる
    alt = w[w["group"].isin(["couple_6560", "couple_65", "head65_nojob", "elder_nojob"])][
        ["group", "year", "集計世帯数", "世帯人員", "実収入", "消費支出", "deficit"]]
    alt.to_csv(RES / "series_by_definition.csv", index=False, float_format="%.2f")

    y = g.set_index("year")
    m = {"main_group": "夫65歳以上・妻60歳以上の夫婦一組の無職世帯（高齢夫婦無職世帯）"}
    m["y2017"] = {"実収入": r0(y.loc[2017, "実収入"]), "実支出": r0(y.loc[2017, "実支出"]),
                  "消費支出": r0(y.loc[2017, "消費支出"]), "非消費支出": r0(y.loc[2017, "非消費支出"]),
                  "不足分": r0(y.loc[2017, "deficit"]), "集計世帯数": r0(y.loc[2017, "集計世帯数"])}
    for yr in (2000, 2005, 2010, 2015, 2019, 2020, 2021, 2022, 2023, 2024, 2025):
        m[f"deficit_{yr}"] = r0(y.loc[yr, "deficit"])
    m["deficit_2025_real"] = r0(y.loc[2025, "deficit"])
    m["deficit_max"] = {"year": int(y["deficit"].idxmax()), "value": r0(y["deficit"].max())}
    m["deficit_min"] = {"year": int(y["deficit"].idxmin()), "value": r0(y["deficit"].min())}
    m["deficit_mean_2000_2025"] = r0(y["deficit"].mean())
    m["deficit_median_2000_2025"] = r0(y["deficit"].median())
    m["years_deficit_ge_50000"] = [int(i) for i in y.index[y["deficit"] >= 50000]]
    m["n_years_deficit_ge_50000"] = len(m["years_deficit_ge_50000"])
    m["sample_households_range"] = [r0(y["集計世帯数"].min()), r0(y["集計世帯数"].max())]
    m["head_age_2000"] = r1(y.loc[2000, "世帯主の年齢"])
    m["head_age_2025"] = r1(y.loc[2025, "世帯主の年齢"])
    for yr in (2000, 2017, 2025):
        m[f"income_{yr}"] = r0(y.loc[yr, "実収入"])
        m[f"pension_{yr}"] = r0(y.loc[yr, "公的年金給付"])
        m[f"consumption_{yr}"] = r0(y.loc[yr, "消費支出"])
        m[f"nonconsumption_{yr}"] = r0(y.loc[yr, "非消費支出"])
        m[f"pension_share_{yr}_pct"] = r1(y.loc[yr, "公的年金給付"] / y.loc[yr, "実収入"] * 100)
    m["special_income_2020"] = r0(y.loc[2020, "特別収入"])
    m["special_income_2019"] = r0(y.loc[2019, "特別収入"])
    m["deficit_regular_2020"] = r0(y.loc[2020, "deficit_regular"])
    dif = y["deficit"].diff().dropna()
    m["deficit_yoy_abs_median"] = r0(dif.abs().median())

    # H1：2021〜2025年平均 vs 2017年（名目）
    h1_mean = float(y.loc[2021:2025, "deficit"].mean())
    m["H1"] = {"deficit_2017": r0(y.loc[2017, "deficit"]), "mean_2021_2025": r0(h1_mean),
               "diff_2017_minus_mean": r0(y.loc[2017, "deficit"] - h1_mean)}
    m["H1"]["verdict"] = "支持" if m["H1"]["diff_2017_minus_mean"] >= 10000 else "外れ"

    # H2：実質の分け方 2000〜2004 → 2021〜2025
    A, B, d, contrib, inc = decompose(g, (2000, 2004), (2021, 2025), real=True)
    rows = []
    for k, v in contrib.items():
        rows.append(("main", "3つの寄与", k, v))
    for k, v in inc.items():
        rows.append(("main", "実収入の中身（符号を反転）", k, v))
    rows.append(("main", "合計", "不足分の変化", d["deficit"]))
    dec = pd.DataFrame(rows, columns=["case", "level", "component", "yen_real2025"])
    dec.to_csv(RES / "decomposition.csv", index=False, float_format="%.2f")
    m["H2"] = {"deficit_2000_2004_real": r0(A["deficit"]), "deficit_2021_2025_real": r0(B["deficit"]),
               "change": r0(d["deficit"]),
               "contrib_consumption": r0(contrib["消費支出の増減"]),
               "contrib_nonconsumption": r0(contrib["非消費支出の増減"]),
               "contrib_income": r0(contrib["実収入の増減（符号を反転）"]),
               "income_2000_2004_real": r0(A["実収入"]), "income_2021_2025_real": r0(B["実収入"]),
               "consumption_2000_2004_real": r0(A["消費支出"]), "consumption_2021_2025_real": r0(B["消費支出"]),
               "pension_2000_2004_real": r0(A["公的年金給付"]), "pension_2021_2025_real": r0(B["公的年金給付"]),
               "inc_parts": {k: r0(v) for k, v in inc.items()}}
    # 実収入が減って（寄与が正）、その大きさが消費支出の寄与を上回れば支持
    m["H2"]["verdict"] = ("支持" if (contrib["実収入の増減（符号を反転）"] > 0 and
                                   abs(contrib["実収入の増減（符号を反転）"]) > abs(contrib["消費支出の増減"])) else "外れ")
    # 名目での同じ分け方
    An, Bn, dn, cn, _ = decompose(g, (2000, 2004), (2021, 2025), real=False)
    m["H2_nominal"] = {"change": r0(dn["deficit"]), "contrib_consumption": r0(cn["消費支出の増減"]),
                       "contrib_nonconsumption": r0(cn["非消費支出の増減"]),
                       "contrib_income": r0(cn["実収入の増減（符号を反転）"]),
                       "deficit_2000_2004": r0(An["deficit"]), "deficit_2021_2025": r0(Bn["deficit"])}

    # H3：埋め方 2015〜2025年
    fc = ["fill_deposit", "fill_insurance", "fill_securities", "fill_other", "fill_cash"]
    fill = g[["year", "deficit"] + fc].copy()
    fill.to_csv(RES / "fill.csv", index=False, float_format="%.2f")
    s = fill[(fill["year"] >= 2015) & (fill["year"] <= 2025)]
    shares = {c: float(s[c].sum() / s["deficit"].sum() * 100) for c in fc}
    m["H3"] = {"period": "2015-2025", "deficit_mean": r0(s["deficit"].mean()),
               "deposit_net_withdraw_mean": r0(s["fill_deposit"].mean()),
               "shares_pct": {k: r1(v) for k, v in shares.items()}}
    m["H3"]["verdict"] = "支持" if shares["fill_deposit"] >= 70 else "外れ"
    s2 = fill[(fill["year"] >= 2000) & (fill["year"] <= 2014)]
    m["fill_2000_2014_deposit_share_pct"] = r1(s2["fill_deposit"].sum() / s2["deficit"].sum() * 100)
    m["fill_deposit_share_by_year_min"] = r1((fill["fill_deposit"] / fill["deficit"] * 100).min())
    m["fill_deposit_share_by_year_max"] = r1((fill["fill_deposit"] / fill["deficit"] * 100).max())

    # H4：年間収入3区分（男65歳以上・女60歳以上の者のみの無職世帯）
    ic = w[w["group"].isin(["elder_inc_lt250", "elder_inc_250_349", "elder_inc_ge350", "elder_nojob"])][
        ["group", "year", "集計世帯数", "実収入", "公的年金給付", "消費支出", "非消費支出", "deficit", "deflator_to_2025"]]
    ic.to_csv(RES / "income_class.csv", index=False, float_format="%.2f")
    p = ic[(ic["year"] >= 2015) & (ic["year"] <= 2025)].groupby("group", sort=True)[
        ["集計世帯数", "実収入", "消費支出", "deficit"]].mean()
    m["H4"] = {k: {"n_mean": r0(p.loc[k, "集計世帯数"]), "income": r0(p.loc[k, "実収入"]),
                   "consumption": r0(p.loc[k, "消費支出"]), "deficit": r0(p.loc[k, "deficit"])}
               for k in ["elder_inc_lt250", "elder_inc_250_349", "elder_inc_ge350", "elder_nojob"]}
    m["H4"]["verdict"] = ("支持" if p.loc["elder_inc_ge350", "deficit"] >= p.loc["elder_inc_lt250", "deficit"]
                          else "外れ")
    yrs_ge = ic.pivot_table(index="year", columns="group", values="deficit")
    m["H4"]["years_ge350_gt_lt250"] = int((yrs_ge["elder_inc_ge350"] > yrs_ge["elder_inc_lt250"]).sum())
    m["H4"]["years_total"] = int(len(yrs_ge))

    # 参考：報告書と同じ掛け算（不足分×12か月×20年・30年）を年ごとに
    mul = g[["year", "deficit"]].copy()
    mul["x20y_man"] = mul["deficit"] * 12 * 20 / 10000
    mul["x30y_man"] = mul["deficit"] * 12 * 30 / 10000
    mul.to_csv(RES / "multiply.csv", index=False, float_format="%.1f")
    mm = mul.set_index("year")
    m["multiply"] = {"x30_2017_man": r0(mm.loc[2017, "x30y_man"]), "x20_2017_man": r0(mm.loc[2017, "x20y_man"]),
                     "x30_min_man": r0(mm["x30y_man"].min()), "x30_max_man": r0(mm["x30y_man"].max()),
                     "x30_min_year": int(mm["x30y_man"].idxmin()), "x30_max_year": int(mm["x30y_man"].idxmax()),
                     "x30_2025_man": r0(mm.loc[2025, "x30y_man"])}

    # 頑健性
    rob = []
    yb = y
    rob.append(("基本", "高齢夫婦無職世帯・名目／実質", m["H1"]["diff_2017_minus_mean"], m["H2"]["contrib_income"],
                m["H2"]["contrib_consumption"], m["H3"]["shares_pct"]["fill_deposit"]))
    # R1 定義の変更
    g2 = w[w["group"] == "couple_65"].set_index("year")
    A2, B2, d2, c2, _ = decompose(w[w["group"] == "couple_65"], (2000, 2004), (2021, 2025), real=True)
    f2 = w[(w["group"] == "couple_65") & (w["year"].between(2015, 2025))]
    rob.append(("R1", "65歳以上の夫婦一組の無職世帯", r0(g2.loc[2017, "deficit"] - g2.loc[2021:2025, "deficit"].mean()),
                r0(c2["実収入の増減（符号を反転）"]), r0(c2["消費支出の増減"]),
                r1(f2["fill_deposit"].sum() / f2["deficit"].sum() * 100)))
    # R2 名目
    rob.append(("R2", "名目（物価を引かない）", m["H1"]["diff_2017_minus_mean"], r0(cn["実収入の増減（符号を反転）"]),
                r0(cn["消費支出の増減"]), m["H3"]["shares_pct"]["fill_deposit"]))
    # R3 2020〜2021年を除く
    A3, B3, d3, c3, _ = decompose(g, (2000, 2004), (2021, 2025), real=True, drop=(2020, 2021))
    s3 = s[~s["year"].isin([2020, 2021])]
    rob.append(("R3", "2020〜2021年を除く（2017年 − 2022〜2025年平均）",
                r0(yb.loc[2017, "deficit"] - yb.loc[2022:2025, "deficit"].mean()),
                r0(c3["実収入の増減（符号を反転）"]), r0(c3["消費支出の増減"]),
                r1(s3["fill_deposit"].sum() / s3["deficit"].sum() * 100)))
    # R4 特別収入を除いた不足分
    gg = g.copy()
    gg["deficit"] = gg["deficit_regular"]
    gg["実収入"] = gg["経常収入"]
    gg["特別収入"] = 0.0
    gg["inc_other"] = (gg["実収入"] - gg["公的年金給付"] - gg["他の社会保障給付"] - gg["work"] - gg["財産収入"])
    A4, B4, d4, c4, _ = decompose(gg, (2000, 2004), (2021, 2025), real=True)
    yr4 = gg.set_index("year")
    rob.append(("R4", "特別収入を除いた不足分（実支出 − 経常収入）",
                r0(yr4.loc[2017, "deficit"] - yr4.loc[2021:2025, "deficit"].mean()),
                r0(c4["実収入の増減（符号を反転）"]), r0(c4["消費支出の増減"]), None))
    # R5 期間の区切り
    A5, B5, d5, c5, _ = decompose(g, (2005, 2009), (2021, 2025), real=True)
    rob.append(("R5a", "比べる期間 2005〜2009 → 2021〜2025", None, r0(c5["実収入の増減（符号を反転）"]),
                r0(c5["消費支出の増減"]), None))
    A6, B6, d6, c6, _ = decompose(g, (2000, 2004), (2023, 2025), real=True)
    rob.append(("R5b", "比べる期間 2000〜2004 → 2023〜2025（2017年 − 2023〜2025年平均）",
                r0(yb.loc[2017, "deficit"] - yb.loc[2023:2025, "deficit"].mean()),
                r0(c6["実収入の増減（符号を反転）"]), r0(c6["消費支出の増減"]), None))
    rb = pd.DataFrame(rob, columns=["id", "condition", "H1_2017_minus_recent", "H2_contrib_income",
                                    "H2_contrib_consumption", "H3_deposit_share_pct"])
    rb["H1_verdict"] = rb["H1_2017_minus_recent"].apply(lambda v: "" if pd.isna(v) else ("支持" if v >= 10000 else "外れ"))
    rb["H2_verdict"] = np.where((rb["H2_contrib_income"] > 0) &
                                (rb["H2_contrib_income"].abs() > rb["H2_contrib_consumption"].abs()), "支持", "外れ")
    rb["H3_verdict"] = rb["H3_deposit_share_pct"].apply(lambda v: "" if pd.isna(v) else ("支持" if v >= 70 else "外れ"))
    rb.to_csv(RES / "robustness.csv", index=False)
    m["robustness"] = rb.where(pd.notna(rb), None).to_dict(orient="records")

    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
