"""02 整形：4つの CSV を、年月×資産×部門×（取得・処分・ネット）の長い表にする（億円）。
年は1月の行にだけ書かれているので、下へ引き継ぐ。値のない月（将来の月）は除く。
出力：data/flows_long.csv
"""
import csv, io, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
ASSETS = {"monthb1": "total", "monthb2": "equity", "monthb3": "longbond", "monthb4": "shortbond"}
SECT = {3: "all", 6: "public", 9: "central_bank", 12: "general_gov", 15: "deposit_taking", 18: "banks", 21: "trust_banks_own",
        24: "other_sectors", 27: "other_financial", 30: "trust_accounts", 33: "banks_trust", 36: "trust_banks_trust",
        39: "securities_firms", 42: "life_insurers", 45: "nonlife_insurers", 48: "investment_trusts", 51: "others"}


def num(s):
    s = s.strip().replace(",", "")
    if s in ("", "-"):
        return 0.0
    return float(s)


def main():
    out = []
    for f, asset in ASSETS.items():
        rows = list(csv.reader(io.StringIO((RAW / f"{f}.csv").read_bytes().decode("cp932"))))
        year = None
        for r in rows[10:]:
            if len(r) < 54 or not r[1].strip().endswith("月"):
                continue
            if r[0].strip().isdigit():
                year = int(r[0])
            if all(x.strip() == "" for x in r[3:6]):
                continue
            ym = year * 100 + int(r[1].strip()[:-1])
            for j, s in SECT.items():
                out.append((ym, asset, s, num(r[j]), num(r[j + 1]), num(r[j + 2])))
    d = pd.DataFrame(out, columns=["ym", "asset", "sector", "acq", "disp", "net"]).sort_values(["asset", "sector", "ym"])
    d.to_csv(D / "flows_long.csv", index=False)
    print(d.ym.min(), d.ym.max(), len(d))


if __name__ == "__main__":
    main()
