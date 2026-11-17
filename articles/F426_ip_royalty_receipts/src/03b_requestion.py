"""03b 問い直し：著作権等使用料は受取が伸びたが、支払も伸びている。赤字は縮んだのか。
受取 ÷ 支払（カバー率）と、受取・支払の伸び（2014→2025年、円とドル）を比べる。
出力：results/requestion.json
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    cov = a.cr_rec / a.cr_pay * 100
    out = dict(cover_2014=float(cov.loc[2014]), cover_2019=float(cov.loc[2019]), cover_2025=float(cov.loc[2025]),
               cr_pay_growth_2014_2025=float((a.loc[2025, "cr_pay"] / a.loc[2014, "cr_pay"] - 1) * 100),
               cr_rec_growth_2014_2025=float((a.loc[2025, "cr_rec"] / a.loc[2014, "cr_rec"] - 1) * 100),
               cr_pay_usd_growth=float((a.loc[2025, "cr_pay_usd"] / a.loc[2014, "cr_pay_usd"] - 1) * 100),
               cr_rec_usd_growth=float((a.loc[2025, "cr_rec_usd"] / a.loc[2014, "cr_rec_usd"] - 1) * 100),
               cr_net_2014=float(a.loc[2014, "cr_net"] / 1e4), cr_net_2025=float(a.loc[2025, "cr_net"] / 1e4),
               cr_net_usd_2014=float((a.loc[2014, "cr_rec_usd"] - a.loc[2014, "cr_pay_usd"])), cr_net_usd_2025=float((a.loc[2025, "cr_rec_usd"] - a.loc[2025, "cr_pay_usd"])),
               cr_rec_2024_2025_pct=float((a.loc[2025, "cr_rec"] / a.loc[2024, "cr_rec"] - 1) * 100))
    json.dump({k: round(v, 3) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
