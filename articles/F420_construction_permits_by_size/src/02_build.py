"""02 整形：抜き出した表から、分析用の表を作る。
出力：data/capital_long.csv（年×階層）、data/total.csv（年、総数、前年比）、data/types_per_firm.csv
"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
LABEL = {"individual": "個人", "lt2m": "法人 200万円未満", "2m_5m": "法人 200万〜500万円", "5m_10m": "法人 500万〜1,000万円",
         "10m_50m": "法人 1,000万〜5,000万円", "50m_100m": "法人 5,000万〜1億円", "100m_1b": "法人 1億〜10億円", "ge1b": "法人 10億円以上"}


def main():
    t5 = pd.read_csv(RAW / "table5_capital.csv")
    long = t5.melt(id_vars=["year", "total"], var_name="cls", value_name="firms")
    long["label"] = long.cls.map(LABEL)
    long["order"] = long.cls.map({k: i for i, k in enumerate(LABEL)})
    long.sort_values(["order", "year"])[["year", "cls", "label", "firms", "total"]].to_csv(D / "capital_long.csv", index=False)
    t1 = pd.read_csv(RAW / "table1_total.csv")
    t1["yoy_pct"] = (t1.total / t1.total.shift(1) - 1) * 100
    t1.round(4).to_csv(D / "total.csv", index=False)
    t3 = pd.read_csv(RAW / "table3_by_type.csv").set_index("type")
    tot = t3.loc["合計"]
    no_demo = tot - t3.loc["解体"].fillna(0)
    firms = t1.set_index("year").total
    rows = []
    for y in t3.columns:
        f = int(firms.loc[int(y)])
        rows.append((int(y), int(tot[y]), int(no_demo[y]), f, tot[y] / f, no_demo[y] / f))
    pd.DataFrame(rows, columns=["year", "permits", "permits_ex_demolition", "firms", "types_per_firm", "types_per_firm_ex_demolition"]).round(4).to_csv(D / "types_per_firm.csv", index=False)


if __name__ == "__main__":
    main()
