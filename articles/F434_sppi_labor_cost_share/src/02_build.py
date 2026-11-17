"""02 整形：月次の表（消費税を除く・含む）を作る。出力：data/extax.csv, data/intax.csv"""
import pathlib
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
NAMES = {"PRCS20_4200000000": "all", "PRCS20_42B0000000": "all_ex_intl", "PRCS20_42S0000002": "high_labor", "PRCS20_42S0000003": "low_labor",
         "PRCS20_4200010001": "finance", "PRCS20_4200010002": "real_estate", "PRCS20_4200010003": "transport", "PRCS20_4200010004": "ict",
         "PRCS20_4200010005": "leasing", "PRCS20_4200010006": "advertising", "PRCS20_4200010007": "other_services",
         "PRCS20_5200000000": "all", "PRCS20_52S0000002": "high_labor", "PRCS20_52S0000003": "low_labor"}


def main():
    for f, out in [("boj_sppi_extax_monthly.json", "extax.csv"), ("boj_sppi_intax_monthly.json", "intax.csv")]:
        d = load(RAW / f).rename(columns=NAMES)
        d.index.name = "ym"
        d.to_csv(D / out)
        print(out, d.shape, d.index.min(), d.index.max())


if __name__ == "__main__":
    main()
