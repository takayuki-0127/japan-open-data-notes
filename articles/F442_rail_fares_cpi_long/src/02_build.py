"""e-Stat の CPI（cp932）から、使う品目だけの月次表と年次（暦年）表を作る（オフライン）。"""
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ITEMS = {"0001": "all_items", "0179": "jr_class", "7527": "jr_regular", "7029": "jr_school", "7030": "jr_commuter",
         "0180": "pr_class", "7008": "pr_regular", "7009": "pr_school", "7010": "pr_commuter",
         "7050": "bus", "7060": "taxi"}
GS = {"0220": "services", "0221": "public_services"}


def pick(name, codes):
    d = pd.read_csv(RAW / name, encoding="cp932", header=None, dtype=str)
    code = d.iloc[2].tolist(); nm = d.iloc[0].tolist()
    out = pd.DataFrame({"period": d.iloc[6:, 0].str.strip().values})
    for c, k in codes.items():
        i = code.index(c)
        out[k] = pd.to_numeric(d.iloc[6:, i].str.strip(), errors="coerce").values
    names = {k: nm[code.index(c)] for c, k in codes.items()}
    return out, names


def main():
    m, names = pick("cpi2025_item_monthly.csv", ITEMS)
    g, gn = pick("cpi2025_goods_services_monthly.csv", GS)
    m = m.merge(g, on="period"); names.update(gn)
    m["period"] = m.period.astype(int)
    m.to_csv(ROOT / "data" / "monthly.csv", index=False)
    a, _ = pick("cpi2025_item_annual_cy.csv", ITEMS)
    ga, _ = pick("cpi2025_goods_services_annual_cy.csv", GS)
    a = a.merge(ga, on="period"); a["period"] = a.period.astype(int)
    a.rename(columns={"period": "year"}).to_csv(ROOT / "data" / "annual.csv", index=False)
    pd.Series(names).to_csv(ROOT / "data" / "item_names.csv", header=["name"], index_label="key")
    print(m.shape, m.period.min(), m.period.max(), a.shape)
    print(m.notna().idxmax().to_dict())


if __name__ == "__main__":
    main()
