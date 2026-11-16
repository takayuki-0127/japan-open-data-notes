"""02 整形：NIES の Excel（計算済みの値）から年度別の表を作る（オフライン）。
出力：data/series.csv（year と各系列の列）。単位：CO2 は Mt（百万トン）、人口は千人、GDP は十億円（実質、支出側）。"""
import pathlib, re
import pandas as pd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "nies_ghg_1990_2024_L5-7gas_2026_gioweb_ver1.0.xlsx"

def clean(x):
    return re.sub(r"\s", "", str(x)) if x is not None else ""

def main():
    wb = openpyxl.load_workbook(str(RAW), read_only=True, data_only=True)
    def rows(name):
        return [list(r) for r in wb[name].iter_rows(values_only=True)]
    S = rows("1.Summary")
    years = [int(y) for y in S[3][26:] if isinstance(y, (int, float))]
    cols = list(range(26, 26 + len(years)))
    def get(R, i, scale=1.0):
        return [float(R[i][c]) * scale for c in cols]
    out = {"year": years}
    lab = {clean(r[18]) + "|" + clean(r[19]): i for i, r in enumerate(S[:16])}
    out["co2_energy_Mt"] = get(S, 5); out["co2_nonenergy_Mt"] = get(S, 6)
    out["co2_total_Mt"] = get(S, 4); out["ghg_total_Mt"] = get(S, 14)
    P = rows("9.GHG-capita"); out["pop_k"] = get(P, 10)
    G = rows("10.GHG-GDP"); out["gdp_real_bn"] = get(G, 10)
    A = rows("3.Allocated_CO2-sector")
    for key, name in [("エネルギー転換部門", "sec_conversion"), ("産業部門", "sec_industry"), ("業務その他部門", "sec_commercial"),
                      ("運輸部門", "sec_transport"), ("家庭部門", "sec_residential")]:
        i = next(k for k, r in enumerate(A) if clean(r[17]) == key)
        out[name + "_Mt"] = get(A, i, 1e-3)
    F = rows("5.CO2-fuel")
    for i, name in [(5, "fuel_coal"), (6, "fuel_coalprod"), (7, "fuel_crude"), (8, "fuel_oilprod"), (9, "fuel_natgas"), (10, "fuel_citygas")]:
        assert clean(F[4][17]) == "合計"
        out[name + "_Mt"] = get(F, i, 1e-3)
    # 電気の使用に伴う排出（各部門の「電気熱配分後」の「電力」の行の合計）
    elec = [0.0] * len(years)
    for i, r in enumerate(F):
        if clean(r[19]) == "電力":
            v = get(F, i, 1e-3)
            elec = [a + b for a, b in zip(elec, v)]
    out["electricity_alloc_Mt"] = elec
    D = pd.DataFrame(out)
    chk = D[["sec_conversion_Mt", "sec_industry_Mt", "sec_commercial_Mt", "sec_transport_Mt", "sec_residential_Mt"]].sum(axis=1) - D.co2_energy_Mt
    print("部門の合計とエネルギー起源 CO2 の差（Mt）の最大", round(float(chk.abs().max()), 3))
    D.to_csv(ROOT / "data" / "series.csv", index=False)
    print(D[["year", "co2_energy_Mt", "pop_k", "gdp_real_bn", "electricity_alloc_Mt"]].iloc[[0, 23, -1]])

if __name__ == "__main__":
    main()
