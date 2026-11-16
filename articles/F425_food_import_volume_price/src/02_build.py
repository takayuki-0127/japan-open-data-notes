"""02 整形：輸入の金額・数量（5品目と食料品計）、ドル円の年平均・年末、輸入物価指数の年平均。
出力：data/food_annual.csv, data/fx_prices_annual.csv
"""
import csv, io, pathlib
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
ITEMS = {"'0'+'1'": ("food_total", None), "'007'": ("fish", 1.0), "'003'": ("meat", 1.0), "'009'": ("cereals", 1.0),
         "'01103'": ("vegetables", 1e-3), "'01101'": ("fruit", 1e-3), "'20307'": ("soybeans", 1.0)}


def main():
    rows = list(csv.reader(io.StringIO((RAW / "d61ca.csv").read_bytes().decode("cp932"))))
    code = rows[4]
    pos = {code[j].strip(): j for j in range(2, len(code)) if code[j].strip()}
    out = []
    for r in rows[7:]:
        if not r or not r[0].strip().isdigit():
            continue
        y = int(r[0])
        for c, (k, to_t) in ITEMS.items():
            j = pos[c]
            q = r[j].strip(); v = r[j + 1].strip()
            out.append(dict(year=y, item=k, value_thousand_yen=None if v in ("", "-") else int(v),
                            quantity_t=None if (to_t is None or q in ("", "-")) else round(int(q) * to_t, 3)))
    pd.DataFrame(out).to_csv(D / "food_annual.csv", index=False)
    fx = load(RAW / "boj_usdjpy_monthly.json")["FXERM07"]
    pr = load(RAW / "boj_import_prices_monthly.json")
    y = fx.index // 100
    a = pd.DataFrame({"usdjpy_avg": fx.groupby(y).mean(), "usdjpy_dec": fx[fx.index % 100 == 12].set_axis(y[fx.index % 100 == 12])})
    names = {"PRCG20_2600120001": "ipi_food_yen", "PRCG20_2500120001": "ipi_food_contract", "PRCG20_2600000000": "ipi_all_yen", "PRCG20_2500000000": "ipi_all_contract"}
    for c, n in names.items():
        a[n] = pr[c].groupby(pr.index // 100).mean()
    a.index.name = "year"
    a.round(4).to_csv(D / "fx_prices_annual.csv")


if __name__ == "__main__":
    main()
