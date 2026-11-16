"""問い直し（結果を見てから足した）。
2019年から2025年に、有効求人倍率は1.60から1.22に下がったのに、失業率は2.4%から2.5%でほとんど動いていない。
→ 倍率の下がりを、有効求人数の変化と有効求職者数の変化に分ける（対数）。あわせて、ハローワークを通じた就職件数の長い流れを見る。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"


def split(d, a, b):
    dl = np.log(d.loc[b, "ratio"] / d.loc[a, "ratio"])
    do = np.log(d.loc[b, "openings"] / d.loc[a, "openings"]); dap = -np.log(d.loc[b, "applicants"] / d.loc[a, "applicants"])
    return dict(start=a, end=b, ratio_start=float(d.loc[a, "ratio"]), ratio_end=float(d.loc[b, "ratio"]), u_start=float(d.loc[a, "u_rate"]), u_end=float(d.loc[b, "u_rate"]),
                openings_pct=float((d.loc[b, "openings"] / d.loc[a, "openings"] - 1) * 100), applicants_pct=float((d.loc[b, "applicants"] / d.loc[a, "applicants"] - 1) * 100),
                unemployed_pct=float((d.loc[b, "unemployed"] / d.loc[a, "unemployed"] - 1) * 100),
                share_openings=float(do / (do + dap)) if (do + dap) != 0 else np.nan, share_applicants=float(dap / (do + dap)) if (do + dap) != 0 else np.nan,
                log_ratio_check=float(dl - (do + dap)))


def main():
    d = pd.read_csv(RES / "annual_indicators.csv").set_index("year")
    rows = [split(d, 2009, 2018), split(d, 2019, 2025), split(d, 2018, 2025)]
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "requestion_ratio_split.csv", index=False)
    d["placements_per_10k_employed"] = d.placements * 12 / (d.employed * 1e4) * 1e4
    d[["placements", "placements_per_10k_employed", "applicants", "unemployed", "openings"]].round(4).to_csv(RES / "requestion_hw_long.csv")
    out = dict(splits=t.round(4).to_dict(orient="records"), placements_peak_year=int(d.placements.idxmax()), placements_peak=float(d.placements.max()),
               placements_2025=float(d.loc[2025, "placements"]), placements_rate_1990=float(d.loc[1990, "placements_per_10k_employed"]),
               placements_rate_2025=float(d.loc[2025, "placements_per_10k_employed"]))
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(t.round(3).to_string()); print({k: v for k, v in out.items() if k != "splits"})


if __name__ == "__main__":
    main()
