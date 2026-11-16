"""03_analysis.py : 名目と実質（物価を除いた）売上の 2019年比、頑健性、仮説の判定（オフライン）。"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

# 中分類 → 価格指数（PLAN.md の対応表）
DEFL = {
    "37": "SPPI_5201220001", "38": "SPPI_5201320001", "39": "SPPI_5201420001",
    "40": "SPPI_5201520001", "41": "SPPI_5201620001",
    "42": "SPPI_5200530001", "43": "SPPI_5200530002", "44": "SPPI_5200630002",
    "45": "SPPI_5200720001", "47": "SPPI_5200930001", "48": "SPPI_5200920001",
    "4*": "SPPI_5200010003",
    "68": "SPPI_5200320001", "69": "SPPI_5200420001", "70": "SPPI_5200010005",
    "72": "SPPI_5202220001", "73": "SPPI_5201920001", "74": "SPPI_5202320001",
    "75": "CPI_0139", "76": "CPI_0042", "77": "CPI_0042",
    "78": "CPI_0146", "79": "CPI_0242", "80": "CPI_0138",
    "82": "CPI_0121",
    "88": "SPPI_5202020001", "89": "SPPI_5202120001", "90": "SPPI_5202120001",
    "91": "SPPI_5202420001", "92": "SPPI_5200010007", "95": "SPPI_5200010007",
}
FACE = ["43", "75", "76", "77", "78", "79", "80"]       # 対面で家計向け（H3）
EDU = ["82"]
BIZ = [c for c in DEFL if c not in FACE + EDU]          # 事業所向け（SPPI で割る、道路旅客を除く）
DIV_ORDER = ["情報通信", "運輸・郵便", "不動産・物品賃貸", "専門・技術サービス", "宿泊・飲食",
             "生活関連・娯楽", "教育・学習支援", "その他のサービス"]
LATEST = list(range(202509, 202513)) + list(range(202601, 202609))


def load():
    s = pd.read_csv(DATA / "sales_monthly.csv", dtype={"code": str})
    p = pd.read_csv(DATA / "prices_monthly.csv").set_index("ym")
    return s, p


def deflate(s, p, defl, base_year):
    """実質売上 = 名目 ÷ (価格 ÷ 基準年の平均価格)。"""
    s = s[s.code.isin(list(defl))].copy()
    base = p.loc[(p.index // 100) == base_year].mean()
    rel = p / base
    s["defl"] = [rel.at[ym, defl[c]] for ym, c in zip(s.ym, s.code)]
    s["real"] = s.sales_mil_yen / s.defl
    return s


def period_sum(d, months, codes):
    x = d[d.ym.isin(months) & d.code.isin(codes)]
    return x.sales_mil_yen.sum(), x.real.sum()


def months_of(y):
    return [y * 100 + m for m in range(1, 13)]


def ratios(d, codes, base_m, comp_m):
    n0, r0 = period_sum(d, base_m, codes)
    n1, r1 = period_sum(d, comp_m, codes)
    nom, real = 100 * n1 / n0, 100 * r1 / r0
    return {"nominal": round(nom, 2), "real": round(real, 2), "price_gap": round(nom - real, 2),
            "base_nominal_tril_yen": round(n0 / 1e6, 2), "comp_nominal_tril_yen": round(n1 / 1e6, 2)}


def main():
    s, p = load()
    allc = list(DEFL)
    d = deflate(s, p, DEFL, 2019)
    d.to_csv(RES / "monthly_nominal_real.csv", index=False, float_format="%.3f")

    B, C = months_of(2019), months_of(2025)
    main_res = {"base": "2019年1〜12月", "comp": "2025年1〜12月"}
    groups = {"total": allc, "face": FACE, "biz": BIZ, "edu": EDU}
    for g, codes in groups.items():
        main_res[g] = ratios(d, codes, B, C)
    main_res["latest12"] = {g: ratios(d, codes, B, LATEST) for g, codes in groups.items()}
    main_res["latest12_period"] = "2025年9月〜2026年8月（2026年6〜8月は速報）"

    # 統計表の「サービス産業計」との照合（名目）
    sv = s[s.code == "SV"]
    sv19 = sv[sv.ym.isin(B)].sales_mil_yen.sum()
    sv25 = sv[sv.ym.isin(C)].sales_mil_yen.sum()
    main_res["check_service_total_table_nominal_2025_vs_2019"] = round(100 * sv25 / sv19, 2)
    main_res["target_share_of_table_total_2019"] = round(100 * main_res["total"]["base_nominal_tril_yen"] * 1e6 / sv19, 1)
    main_res["n_industries"] = len(allc)

    # 業種別
    meta = s[s.code.isin(allc)].drop_duplicates("code")[["code", "industry", "division"]]
    rows = []
    for _, m in meta.iterrows():
        r = ratios(d, [m.code], B, C)
        r12 = ratios(d, [m.code], B, LATEST)
        grp = "対面・家計向け" if m.code in FACE else ("教育" if m.code in EDU else "事業所向け")
        rows.append({"code": m.code, "industry": m.industry, "division": m.division, "group": grp,
                     "deflator": DEFL[m.code], "sales2019_tril_yen": r["base_nominal_tril_yen"],
                     "nominal_2025": r["nominal"], "real_2025": r["real"], "price_gap_2025": r["price_gap"],
                     "nominal_latest12": r12["nominal"], "real_latest12": r12["real"]})
    ind = pd.DataFrame(rows)
    ind["div_order"] = ind.division.map({k: i for i, k in enumerate(DIV_ORDER)})
    ind = ind.sort_values(["div_order", "code"], kind="mergesort").drop(columns="div_order")
    ind.to_csv(RES / "industry_ratios.csv", index=False)

    # 大分類別
    drows = []
    for dv in DIV_ORDER:
        codes = ind[ind.division == dv].code.tolist()
        r = ratios(d, codes, B, C)
        drows.append({"division": dv, **{k: r[k] for k in ("nominal", "real", "price_gap", "base_nominal_tril_yen")}})
    pd.DataFrame(drows).to_csv(RES / "division_ratios.csv", index=False)

    # 年ごとの比（2019年=100）
    yrows = []
    for y in range(2013, 2026):
        for g, codes in groups.items():
            r = ratios(d, codes, B, months_of(y))
            yrows.append({"year": y, "group": g, "nominal": r["nominal"], "real": r["real"]})
    pd.DataFrame(yrows).to_csv(RES / "annual_index_2019eq100.csv", index=False)

    # 12か月移動合計（2019年=100）
    mm = []
    for g, codes in groups.items():
        x = d[d.code.isin(codes)].groupby("ym", sort=True)[["sales_mil_yen", "real"]].sum()
        roll = x.rolling(12).sum()
        b = x.loc[B].sum()
        roll = roll.dropna()
        for ym, v in roll.iterrows():
            mm.append({"ym": int(ym), "group": g, "nominal": round(100 * v.sales_mil_yen / b.sales_mil_yen, 3),
                       "real": round(100 * v.real / b.real, 3)})
    mm = pd.DataFrame(mm)
    mm.to_csv(RES / "rolling12_index.csv", index=False)
    # 実質で 2019年を初めて上回った12か月合計の終わりの月（2021年以降）
    first = {}
    for g in groups:
        x = mm[(mm.group == g) & (mm.ym >= 202101)]
        for col in ("nominal", "real"):
            y = x[x[col] >= 100]
            first[f"{g}_{col}"] = int(y.ym.iloc[0]) if len(y) else None
        z2 = mm[(mm.group == g) & (mm.ym >= 202001)].set_index("ym")
        first[f"{g}_real_min"] = round(float(z2.real.min()), 2)
        first[f"{g}_real_min_ym"] = int(z2.real.idxmin())
        first[f"{g}_nominal_min"] = round(float(z2.nominal.min()), 2)
        first[f"{g}_nominal_min_ym"] = int(z2.nominal.idxmin())
        first[f"{g}_last_nominal"] = round(float(z2.nominal.iloc[-1]), 2)
        first[f"{g}_last_real"] = round(float(z2.real.iloc[-1]), 2)
    main_res["rolling12_first_ge100"] = first

    # 価格の上がり方（2025年平均 ÷ 2019年平均）
    pr = {}
    for k in sorted(set(DEFL.values())) + ["SPPI_5200000000", "CPI_0242"]:
        a = p.loc[(p.index // 100) == 2019, k].mean()
        b2 = p.loc[(p.index // 100) == 2025, k].mean()
        pr[k] = round(100 * b2 / a, 2)
    main_res["price_2025_vs_2019"] = pr

    # 頑健性
    rob = []

    def add(name, dd, codes, base_m, comp_m, note=""):
        r = ratios(dd, codes, base_m, comp_m)
        rob.append({"check": name, "nominal": r["nominal"], "real": r["real"], "price_gap": r["price_gap"],
                    "face_real": ratios(dd, FACE, base_m, comp_m)["real"] if set(FACE) <= set(codes) else np.nan,
                    "note": note})

    add("主（業種ごとの価格、2025年÷2019年）", d, allc, B, C)
    d_a = deflate(s, p, {c: "SPPI_5200000000" for c in allc}, 2019)
    add("1a 全業種を SPPI 総平均で割る", d_a, allc, B, C)
    d_b = deflate(s, p, {c: "CPI_0242" for c in allc}, 2019)
    add("1b 全業種を CPI 持家の帰属家賃を除くサービスで割る", d_b, allc, B, C)
    d18 = deflate(s, p, DEFL, 2018)
    add("2 基準年を2018年にする", d18, allc, months_of(2018), C)
    add("3 最新12か月（2025年9月〜2026年8月）", d, allc, B, LATEST, "うち3か月は速報")
    alt = dict(DEFL)
    alt["79"] = "CPI_0138"
    alt["82"] = "CPI_0242"
    d_c = deflate(s, p, alt, 2019)
    add("4 その他の生活関連→教養娯楽サービス、教育→サービス全体", d_c, allc, B, C)
    no75 = [c for c in allc if c != "75"]
    r5 = ratios(d, no75, B, C)
    rob.append({"check": "5 宿泊業を除く", "nominal": r5["nominal"], "real": r5["real"],
                "price_gap": r5["price_gap"], "face_real": ratios(d, [c for c in FACE if c != "75"], B, C)["real"],
                "note": "face_real は宿泊業を除く対面6業種"})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    main_res["robustness"] = rob.to_dict(orient="records")

    # 仮説の判定
    t, f, b = main_res["total"], main_res["face"], main_res["biz"]
    hyp = {
        "H1": {"rule": "合計の名目 2025/2019 > 100", "value": t["nominal"],
               "judge": "支持" if t["nominal"] > 100 else "外れ"},
        "H2": {"rule": "実質の伸び ≦ 名目の伸び×0.5", "value": [round(t["real"] - 100, 2), round(t["nominal"] - 100, 2)],
               "judge": "支持" if (t["real"] - 100) <= 0.5 * (t["nominal"] - 100) else "外れ"},
        "H3": {"rule": "対面・家計向け7業種の実質 < 100", "value": f["real"],
               "judge": "支持" if f["real"] < 100 else "外れ"},
        "H4": {"rule": "物価の寄与：対面・家計向け > 事業所向け", "value": [f["price_gap"], b["price_gap"]],
               "judge": "支持" if f["price_gap"] > b["price_gap"] else "外れ"},
    }
    main_res["hypotheses"] = hyp

    # 問い直し：事業従事者規模別の売上の構成比（2019年→2023年、名目）
    z = pd.read_csv(DATA / "size_annual.csv", dtype={"code": str})
    z = z[z.code.isin(allc)]
    piv = z.pivot_table(index=["year", "size"], values="sales_mil_yen_monthly_avg", aggfunc="sum")
    sizes = ["10人未満", "10〜29人", "30〜99人", "100〜299人", "300人以上"]
    srows = []
    for y in (2018, 2019, 2023):
        tot = piv.loc[(y, "総数")].iloc[0]
        for sz in sizes:
            v = piv.loc[(y, sz)].iloc[0]
            srows.append({"year": y, "size": sz, "sales_mil_yen_monthly_avg": v, "share_pct": round(100 * v / tot, 2)})
    sz_df = pd.DataFrame(srows)
    sz_df.to_csv(RES / "size_share_target.csv", index=False)
    sh = sz_df.pivot(index="size", columns="year", values="share_pct").loc[sizes]
    small = sh.loc[["10人未満", "10〜29人"]].sum()
    # 業種ごと：10人未満＋10〜29人 の構成比の変化
    zr = []
    for c in allc:
        x = z[z.code == c].pivot_table(index="year", columns="size", values="sales_mil_yen_monthly_avg", aggfunc="sum")
        if not set([2019, 2023]) <= set(x.index):
            continue
        sm = (x["10人未満"] + x["10〜29人"]) / x["総数"] * 100
        zr.append({"code": c, "industry": meta.set_index("code").industry[c],
                   "small_share_2018": round(sm.get(2018, np.nan), 2), "small_share_2019": round(sm[2019], 2),
                   "small_share_2023": round(sm[2023], 2), "change_19_23": round(sm[2023] - sm[2019], 2),
                   "change_18_19": round(sm[2019] - sm.get(2018, np.nan), 2)})
    zr = pd.DataFrame(zr)
    zr["div_order"] = zr.code.map(ind.set_index("code").division).map({k: i for i, k in enumerate(DIV_ORDER)})
    zr = zr.sort_values(["div_order", "code"], kind="mergesort").drop(columns="div_order")
    zr.to_csv(RES / "size_small_share_by_industry.csv", index=False)
    # 名目の伸びを規模別に（年報の値は段差の調整なし）
    gr = {sz: round(100 * piv.loc[(2023, sz)].iloc[0] / piv.loc[(2019, sz)].iloc[0], 2) for sz in sizes + ["総数"]}
    ts23 = ratios(d, allc, B, months_of(2023))["nominal"]
    main_res["size"] = {
        "small_share_2018": round(small[2018], 2), "small_share_2019": round(small[2019], 2),
        "small_share_2023": round(small[2023], 2),
        "share_by_size": {str(y): {sz: float(sh.loc[sz, y]) for sz in sizes} for y in (2018, 2019, 2023)},
        "nominal_2023_vs_2019_by_size_annual_table": gr,
        "nominal_2023_vs_2019_timeseries_adjusted": ts23,
        "n_industries_small_share_down_19_23": int((zr.change_19_23 < 0).sum()),
        "n_industries_small_share_up_19_23": int((zr.change_19_23 > 0).sum()),
        "n_industries": int(len(zr)),
        "median_change_19_23": round(float(zr.change_19_23.median()), 2),
        "median_change_18_19": round(float(zr.change_18_19.median()), 2),
        "face_small_share_2019": None, "face_small_share_2023": None,
    }
    fz = z[z.code.isin(FACE)].pivot_table(index="year", columns="size", values="sales_mil_yen_monthly_avg", aggfunc="sum")
    fs = (fz["10人未満"] + fz["10〜29人"]) / fz["総数"] * 100
    main_res["size"]["face_small_share_2019"] = round(float(fs[2019]), 2)
    main_res["size"]["face_small_share_2023"] = round(float(fs[2023]), 2)
    main_res["size"]["face_nominal_2023_vs_2019_small"] = round(float(
        100 * (fz.loc[2023, "10人未満"] + fz.loc[2023, "10〜29人"]) / (fz.loc[2019, "10人未満"] + fz.loc[2019, "10〜29人"])), 2)
    main_res["size"]["face_nominal_2023_vs_2019_large"] = round(float(
        100 * (fz.loc[2023, "100〜299人"] + fz.loc[2023, "300人以上"]) / (fz.loc[2019, "100〜299人"] + fz.loc[2019, "300人以上"])), 2)

    with open(RES / "main.json", "w", encoding="utf-8") as fp:
        json.dump(main_res, fp, ensure_ascii=False, indent=1, sort_keys=True, default=float)
    print(json.dumps({k: main_res[k] for k in ("total", "face", "biz", "edu", "hypotheses", "size")},
                     ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
