"""03 分析：財とサービスの上昇率（期間別）、2021年からの上昇、前月から動かなかった月の割合、頑健性。
出力：results/main.json, results/periods.csv, results/since2021.csv, results/zero_change.csv, results/robustness.csv, results/yoy.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
SERIES = ["all", "goods", "goods_ex_fresh", "services", "services_ex_rent", "public_services", "general_services", "eating_out", "private_rent", "imputed_rent", "other_services", "industrial", "food_products"]
TAX = [198904, 199704, 201404, 201910]
PERIODS = [(1971, 1990), (1991, 2012), (1995, 2012), (2013, 2021), (2022, 2025)]


def main():
    d = pd.read_csv(D / "cpi_monthly.csv").set_index("ym")
    yr = d.index // 100
    ann = d.groupby(yr).mean()
    yoy = (d / d.shift(12) - 1) * 100
    yoy.round(4).to_csv(R / "yoy.csv")
    ay = (ann / ann.shift(1) - 1) * 100
    per = pd.DataFrame({f"{a}-{b}": ay.loc[a:b, SERIES].mean() for a, b in PERIODS}).T
    per.round(4).to_csv(R / "periods.csv")
    last = d.index[-1]
    def since(base):
        return (d.loc[last, SERIES] / ann.loc[base, SERIES] - 1) * 100
    s21 = since(2021)
    pd.DataFrame({"since_2021": s21, "since_2020": since(2020), "since_2019": since(2019)}).round(3).to_csv(R / "since2021.csv")
    mom = d.diff()
    def zero_share(col, a, b, drop_tax=False):
        m = mom.loc[a:b, col].dropna()
        if drop_tax:
            m = m.drop([t for t in TAX if t in m.index])
        return float((m.abs() < 1e-9).mean() * 100)
    zc = []
    for col in ["goods", "goods_ex_fresh", "services", "services_ex_rent", "public_services", "general_services", "eating_out", "private_rent"]:
        zc.append(dict(series=col, z_1995_2026=zero_share(col, 199501, last), z_1995_2012=zero_share(col, 199501, 201212),
                       z_2013_2026=zero_share(col, 201301, last), z_1995_2026_notax=zero_share(col, 199501, last, True)))
    zc = pd.DataFrame(zc).set_index("series"); zc.round(3).to_csv(R / "zero_change.csv")
    sx25 = float(ay.loc[2025, "services_ex_rent"])
    main = dict(last=int(last), goods_since2021=float(s21.goods), services_since2021=float(s21.services), goods_ex_fresh_since2021=float(s21.goods_ex_fresh),
                services_ex_rent_since2021=float(s21.services_ex_rent), eating_out_since2021=float(s21.eating_out), public_since2021=float(s21.public_services),
                private_rent_since2021=float(s21.private_rent), imputed_rent_since2021=float(s21.imputed_rent), all_since2021=float(s21["all"]),
                ratio_goods_services=float(s21.goods / s21.services),
                services_1995_2012=float(per.loc["1995-2012", "services"]), goods_1995_2012=float(per.loc["1995-2012", "goods"]),
                services_1971_1990=float(per.loc["1971-1990", "services"]), goods_1971_1990=float(per.loc["1971-1990", "goods"]),
                services_2013_2021=float(per.loc["2013-2021", "services"]), goods_2013_2021=float(per.loc["2013-2021", "goods"]),
                services_2022_2025=float(per.loc["2022-2025", "services"]), goods_2022_2025=float(per.loc["2022-2025", "goods"]),
                services_ex_rent_2025=sx25, services_2025=float(ay.loc[2025, "services"]), goods_2025=float(ay.loc[2025, "goods"]),
                eating_out_2025=float(ay.loc[2025, "eating_out"]), public_2025=float(ay.loc[2025, "public_services"]),
                zero_services=float(zc.loc["services", "z_1995_2026"]), zero_goods_ex_fresh=float(zc.loc["goods_ex_fresh", "z_1995_2026"]),
                zero_services_ex_rent=float(zc.loc["services_ex_rent", "z_1995_2026"]), zero_goods=float(zc.loc["goods", "z_1995_2026"]),
                services_yoy_latest=float(yoy.loc[last, "services"]), goods_yoy_latest=float(yoy.loc[last, "goods"]),
                services_ex_rent_yoy_latest=float(yoy.loc[last, "services_ex_rent"]))
    main["H1"] = "支持" if main["ratio_goods_services"] >= 2 else "外れ"
    main["H2"] = "支持" if abs(main["services_1995_2012"]) <= 0.5 else "外れ"
    main["H3"] = "支持" if main["zero_services"] > main["zero_goods_ex_fresh"] else "外れ"
    main["H4"] = "支持" if sx25 > 2 else "外れ"
    rob = [dict(check="基準 2021年平均→最新（本線）", goods=float(s21.goods), services=float(s21.services), ratio=float(s21.goods / s21.services))]
    for b in (2020, 2019):
        s = since(b); rob.append(dict(check=f"基準 {b}年平均→最新", goods=float(s.goods), services=float(s.services), ratio=float(s.goods / s.services)))
    rob.append(dict(check="生鮮食品を除く財 対 帰属家賃を除くサービス（2021年→最新）", goods=float(s21.goods_ex_fresh), services=float(s21.services_ex_rent), ratio=float(s21.goods_ex_fresh / s21.services_ex_rent)))
    for col in ["goods_ex_fresh", "services", "services_ex_rent"]:
        rob.append(dict(check=f"動かなかった月の割合 {col}：1995〜2012 / 2013〜最新 / 税率改定の月を除く", goods=float(zc.loc[col, "z_1995_2012"]), services=float(zc.loc[col, "z_2013_2026"]), ratio=float(zc.loc[col, "z_1995_2026_notax"])))
    pd.DataFrame(rob).round(3).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(per.round(2).T); print(zc.round(1)); print(pd.read_csv(R / "robustness.csv").to_string())


if __name__ == "__main__":
    main()
