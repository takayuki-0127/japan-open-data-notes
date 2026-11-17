"""年の値・1店あたり・実質・人口あたり・仮説の判定・頑健性（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
REG_EN = ["hokkaido", "tohoku", "kanto", "chubu", "kinki", "chugoku", "shikoku", "kyushu_okinawa"]
REG_JA = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
ITEMS = ["total", "goods", "ff_daily", "processed", "nonfood", "service"]


def r(x, k=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def annual(nat, suffix):
    full = nat.groupby("year").filter(lambda g: len(g) == 12)
    g = full.groupby("year", sort=True)
    out = pd.DataFrame({c: g[c + suffix].sum() for c in ITEMS})
    out["stores_dec"] = g.apply(lambda x: x.loc[x["month"] == 12, "stores" + suffix].iloc[0], include_groups=False)
    out["stores_avg"] = g["stores" + suffix].mean()
    return out.reset_index()


def main():
    nat = pd.read_csv(D / "national_monthly.csv")
    cpi = pd.read_csv(D / "cpi_annual.csv").set_index("year")
    a = annual(nat, "_link")
    a_raw = annual(nat, "")
    for df in (a, a_raw):
        df["per_store_nom"] = df["total"] / df["stores_avg"]          # 百万円/店
        df["per_store_goods_nom"] = df["goods"] / df["stores_avg"]
        df["per_store_dec_nom"] = df["total"] / df["stores_dec"]
        df["cpi_all"] = df["year"].map(cpi["cpi_all"])
        df["cpi_food"] = df["year"].map(cpi["cpi_food"])
        df["per_store_real"] = df["per_store_nom"] / df["cpi_all"] * 100
        df["per_store_real_food"] = df["per_store_nom"] / df["cpi_food"] * 100
        df["per_store_goods_real"] = df["per_store_goods_nom"] / df["cpi_all"] * 100
        df["per_store_dec_real"] = df["per_store_dec_nom"] / df["cpi_all"] * 100
        df["total_real"] = df["total"] / df["cpi_all"] * 100
        for c in ITEMS[1:]:
            df["share_" + c] = df[c] / df["total"] * 100
    a.to_csv(R / "annual_national.csv", index=False, float_format="%.4f")
    A = a.set_index("year")
    Araw = a_raw.set_index("year")

    def pct(s, y0, y1):
        return (s.loc[y1] / s.loc[y0] - 1) * 100

    # 店舗数が最も多い年（12月末）と、増加が止まった年の目安
    peak_year = int(A["stores_dec"].idxmax())
    diff = A["stores_dec"].diff()
    main = {
        "years": [int(A.index.min()), int(A.index.max())],
        "stores_dec": {str(y): r(A.loc[y, "stores_dec"], 1) for y in [2000, 2010, 2016, 2019, 2025]},
        "stores_peak_year": peak_year,
        "stores_peak": r(A.loc[peak_year, "stores_dec"], 1),
        "stores_net_change_avg_2010_2016": r(diff.loc[2011:2016].mean(), 1),
        "stores_net_change_avg_2017_2025": r(diff.loc[2017:2025].mean(), 1),
        "sales_total_oku": {str(y): r(A.loc[y, "total"] / 100, 1) for y in [2010, 2016, 2019, 2025]},
        "sales_real_oku_2025yen": {str(y): r(A.loc[y, "total_real"] / 100, 1) for y in [2010, 2016, 2019, 2025]},
        "per_store_nom_man": {str(y): r(A.loc[y, "per_store_nom"] * 100, 1) for y in [2010, 2016, 2019, 2025]},
        "per_store_real_man": {str(y): r(A.loc[y, "per_store_real"] * 100, 1) for y in [2010, 2016, 2019, 2025]},
        "per_store_real_peak_year": int(A["per_store_real"].idxmax()),
        "cpi_all_2019_2025_pct": r(pct(A["cpi_all"], 2019, 2025), 2),
        "cpi_food_2019_2025_pct": r(pct(A["cpi_food"], 2019, 2025), 2),
    }
    # 仮説
    h1 = pct(A["stores_dec"], 2016, 2025)
    h2 = pct(A["per_store_nom"], 2019, 2025)
    h3 = pct(A["per_store_real"], 2019, 2025)
    main["H1_stores_2016_2025_pct"] = r(h1, 2)
    main["H1_judge"] = "支持" if abs(h1) <= 3 else "外れ"
    main["H2_per_store_nom_2019_2025_pct"] = r(h2, 2)
    main["H2_judge"] = "支持" if h2 >= 5 else "外れ"
    main["H3_per_store_real_2019_2025_pct"] = r(h3, 2)
    main["H3_judge"] = "支持" if h3 < 0 else "外れ"
    main["per_store_nom_2010_2016_pct"] = r(pct(A["per_store_nom"], 2010, 2016), 2)
    main["per_store_real_2010_2016_pct"] = r(pct(A["per_store_real"], 2010, 2016), 2)
    main["per_store_real_2016_2019_pct"] = r(pct(A["per_store_real"], 2016, 2019), 2)
    main["per_store_real_2010_2025_pct"] = r(pct(A["per_store_real"], 2010, 2025), 2)
    main["sales_real_2019_2025_pct"] = r(pct(A["total_real"], 2019, 2025), 2)
    main["sales_nom_2019_2025_pct"] = r(pct(A["total"], 2019, 2025), 2)
    main["per_store_real_2020_pct_vs_2019"] = r(pct(A["per_store_real"], 2019, 2020), 2)

    # 商品の構成比
    main["share"] = {str(y): {c: r(A.loc[y, "share_" + c], 2) for c in ITEMS[1:]} for y in [2010, 2016, 2019, 2025]}

    # 地域（経済産業局の区域）
    reg = pd.read_csv(D / "region_monthly.csv")
    pop = pd.read_csv(D / "region_population.csv")
    dec = reg[reg["month"] == 12][["region", "year", "stores_link", "stores"]]
    rows = []
    for e, j in zip(REG_EN, REG_JA):
        s = dec[dec["region"] == e].set_index("year")
        p = pop[pop["region"] == e].set_index("year")["pop_thousand"]
        rec = {"region": e, "region_ja": j}
        for y in [2010, 2016, 2019, 2024]:
            rec[f"stores_{y}"] = s.loc[y, "stores_link"]
            rec[f"pop_{y}_thousand"] = p.loc[y]
            rec[f"per100k_{y}"] = s.loc[y, "stores_link"] / (p.loc[y] * 1000) * 1e5
        rec["stores_raw_2010"] = s.loc[2010, "stores"]
        rec["stores_raw_2019"] = s.loc[2019, "stores"]
        rec["growth_2010_2019_pct"] = (s.loc[2019, "stores_link"] / s.loc[2010, "stores_link"] - 1) * 100
        rec["growth_raw_2010_2019_pct"] = (s.loc[2019, "stores"] / s.loc[2010, "stores"] - 1) * 100
        rec["growth_2019_2024_pct"] = (s.loc[2024, "stores_link"] / s.loc[2019, "stores_link"] - 1) * 100
        rows.append(rec)
    rg = pd.DataFrame(rows)
    rg.to_csv(R / "region_per_capita.csv", index=False, float_format="%.4f")
    rho = stats.pearsonr(rg["per100k_2010"], rg["growth_2010_2019_pct"])[0]
    rs = stats.spearmanr(rg["per100k_2010"], rg["growth_2010_2019_pct"])[0]
    rho_ex = stats.pearsonr(rg.loc[rg.region != "shikoku", "per100k_2010"], rg.loc[rg.region != "shikoku", "growth_2010_2019_pct"])[0]
    rho_raw = stats.pearsonr(rg["stores_raw_2010"] / (rg["pop_2010_thousand"] * 10), rg["growth_raw_2010_2019_pct"])[0]
    main["H4_corr_pearson"] = r(rho, 3)
    main["H4_judge"] = "支持" if rho < 0 else "外れ"
    main["region_per100k"] = {j: {"2010": r(a_, 1), "2024": r(b_, 1)} for j, a_, b_ in zip(rg["region_ja"], rg["per100k_2010"], rg["per100k_2024"])}
    main["region_per100k_range_2010"] = [r(rg["per100k_2010"].min(), 1), r(rg["per100k_2010"].max(), 1)]
    main["region_per100k_range_2024"] = [r(rg["per100k_2024"].min(), 1), r(rg["per100k_2024"].max(), 1)]
    main["region_cv_2010"] = r(rg["per100k_2010"].std(ddof=0) / rg["per100k_2010"].mean() * 100, 2)
    main["region_cv_2024"] = r(rg["per100k_2024"].std(ddof=0) / rg["per100k_2024"].mean() * 100, 2)
    main["national_per100k"] = {}
    natpop = pop.groupby("year")["pop_thousand"].sum()
    for y in [2010, 2016, 2019, 2024]:
        main["national_per100k"][str(y)] = r(A.loc[y, "stores_dec"] / (natpop.loc[y] * 1000) * 1e5, 1)

    # 頑健性
    rb = []
    def add(name, h, val, judge, note=""):
        rb.append({"check": name, "hypothesis": h, "value": r(val, 2), "judge": judge, "note": note})
    add("基本（リンク係数でつなぐ）", "H1", h1, main["H1_judge"], "店舗数 2016→2025 %")
    add("基本（リンク係数でつなぐ）", "H2", h2, main["H2_judge"], "名目1店あたり 2019→2025 %")
    add("基本（リンク係数でつなぐ）", "H3", h3, main["H3_judge"], "実質1店あたり 2019→2025 %")
    add("基本（リンク係数でつなぐ）", "H4", rho, main["H4_judge"], "相関（ピアソン、8区域）")
    v = pct(Araw["stores_dec"], 2016, 2025); add("1. リンク係数を使わない", "H1", v, "支持" if abs(v) <= 3 else "外れ")
    v = pct(Araw["per_store_nom"], 2019, 2025); add("1. リンク係数を使わない", "H2", v, "支持" if v >= 5 else "外れ")
    v = pct(Araw["per_store_real"], 2019, 2025); add("1. リンク係数を使わない", "H3", v, "支持" if v < 0 else "外れ")
    add("1. リンク係数を使わない", "H4", rho_raw, "支持" if rho_raw < 0 else "外れ", "相関（ピアソン、8区域）")
    v = pct(A["per_store_real_food"], 2019, 2025); add("2. 物価を食料にする", "H3", v, "支持" if v < 0 else "外れ")
    v = pct(A["per_store_dec_nom"], 2019, 2025); add("3. 年末の店舗数で割る", "H2", v, "支持" if v >= 5 else "外れ")
    v = pct(A["per_store_dec_real"], 2019, 2025); add("3. 年末の店舗数で割る", "H3", v, "支持" if v < 0 else "外れ")
    v = pct(A["per_store_nom"], 2018, 2025); add("4. 比べる年を2018年にする", "H2", v, "支持" if v >= 5 else "外れ")
    v = pct(A["per_store_real"], 2018, 2025); add("4. 比べる年を2018年にする", "H3", v, "支持" if v < 0 else "外れ")
    v = pct(A["per_store_goods_nom"], 2019, 2025); add("5. サービスを除く商品販売額", "H2", v, "支持" if v >= 5 else "外れ")
    v = pct(A["per_store_goods_real"], 2019, 2025); add("5. サービスを除く商品販売額", "H3", v, "支持" if v < 0 else "外れ")
    add("6. 順位の相関（スピアマン）", "H4", rs, "支持" if rs < 0 else "外れ", "8区域")
    add("7. 四国を除く（2012年のリンク係数が1.57と大きい）", "H4", rho_ex, "支持" if rho_ex < 0 else "外れ", "7区域、計画にない追加")
    pd.DataFrame(rb).to_csv(R / "robustness.csv", index=False)
    main["H4_corr_spearman"] = r(rs, 3)
    main["H4_corr_ex_shikoku"] = r(rho_ex, 3)
    main["H4_corr_raw"] = r(rho_raw, 3)
    main["robust_H3_food_pct"] = r(pct(A["per_store_real_food"], 2019, 2025), 2)
    main["robust_H3_2018_pct"] = r(pct(A["per_store_real"], 2018, 2025), 2)
    main["robust_H3_goods_pct"] = r(pct(A["per_store_goods_real"], 2019, 2025), 2)
    main["robust_H3_raw_pct"] = r(pct(Araw["per_store_real"], 2019, 2025), 2)
    main["robust_H2_raw_pct"] = r(pct(Araw["per_store_nom"], 2019, 2025), 2)
    main["robust_H1_raw_pct"] = r(pct(Araw["stores_dec"], 2016, 2025), 2)
    (R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(main, ensure_ascii=False, indent=1)[:4000])
    print(pd.DataFrame(rb).to_string())


if __name__ == "__main__":
    main()
