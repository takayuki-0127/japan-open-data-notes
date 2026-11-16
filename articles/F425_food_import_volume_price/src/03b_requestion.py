"""03b 問い直し：5年間で見るとドル単価の寄与は小さいが、年ごとに見るとどうか。
2012→2025年の毎年の前年比を、量・ドル単価・為替に分ける（5品目、ディビジア型）。
あわせて、輸入物価指数（円ベース）と通関の円単価の伸びの差を年ごとに並べる。
出力：results/requestion.json, results/yearly_decomp.csv
"""
import json, pathlib, importlib.util
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
spec = importlib.util.spec_from_file_location("a3", ROOT / "src" / "03_analysis.py"); a3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(a3)


def main():
    f = pd.read_csv(D / "food_annual.csv")
    fx = pd.read_csv(D / "fx_prices_annual.csv").set_index("year")
    rows = []
    for y in range(2013, 2026):
        x = a3.decomp(f, fx, y - 1, y, a3.ITEMS).set_index("item").loc["total5"]
        rows.append(dict(year=y, value_pct=x.value_g, l_qty=x.l_qty * 100, l_usd_price=x.l_usd_price * 100, l_fx=x.l_fx * 100,
                         ipi_food_yen_pct=(fx.loc[y, "ipi_food_yen"] / fx.loc[y - 1, "ipi_food_yen"] - 1) * 100,
                         ipi_food_contract_pct=(fx.loc[y, "ipi_food_contract"] / fx.loc[y - 1, "ipi_food_contract"] - 1) * 100))
    t = pd.DataFrame(rows)
    t.round(4).to_csv(R / "yearly_decomp.csv", index=False)
    s = t.set_index("year")
    out = dict(usd_price_2021_2022=float(s.loc[[2021, 2022], "l_usd_price"].sum()), usd_price_2023_2025=float(s.loc[[2023, 2024, 2025], "l_usd_price"].sum()),
               fx_2021_2025=float(s.loc[2021:2025, "l_fx"].sum()), qty_2021_2025=float(s.loc[2021:2025, "l_qty"].sum()),
               ipi_contract_2021_2022=float(np.log((1 + s.loc[[2021, 2022], "ipi_food_contract_pct"] / 100).prod()) * 100),
               ipi_contract_2023_2025=float(np.log((1 + s.loc[[2023, 2024, 2025], "ipi_food_contract_pct"] / 100).prod()) * 100))
    json.dump({k: round(v, 3) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t.round(1).to_string()); print(out)


if __name__ == "__main__":
    main()
