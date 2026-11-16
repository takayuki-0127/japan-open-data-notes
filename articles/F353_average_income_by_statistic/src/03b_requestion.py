"""問い直し（結果を見てから足した）。
中央値は平均より67万円低く、6割の人が平均より下だった。この差は年によって変わるのか（2016〜2025年分、国税庁の累年比較）。"""
import pathlib, json, importlib.util
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
spec = importlib.util.spec_from_file_location("ana", ROOT / "src" / "03_analysis.py")
ana = importlib.util.module_from_spec(spec); spec.loader.exec_module(ana)


def main():
    yrs = pd.read_csv(ROOT / "data" / "nta_brackets_years.csv")
    rows = []
    for (y, sx), g in yrs.groupby(["year", "sex"]):
        t = g[g.bracket == "計"].iloc[0]; b = g[g.bracket != "計"]
        mean = float(t.total_million / t.persons_thousand / 10)
        med = ana.median_from_brackets(b, "persons_thousand")
        rows.append(dict(year=int(y), sex=sx, mean=mean, median=med, gap=mean - med, ratio=med / mean, share_below_mean=ana.share_below(b, "persons_thousand", mean)))
    t = pd.DataFrame(rows)
    t.round(4).to_csv(RES / "requestion_mean_median_years.csv", index=False)
    a = t[t.sex == "計"].set_index("year")
    out = dict(gap_2016=float(a.loc[2016, "gap"]), gap_2025=float(a.loc[2025, "gap"]), gap_min=float(a.gap.min()), gap_max=float(a.gap.max()),
               ratio_2016=float(a.loc[2016, "ratio"]), ratio_2025=float(a.loc[2025, "ratio"]), mean_2016=float(a.loc[2016, "mean"]), median_2016=float(a.loc[2016, "median"]),
               mean_2025=float(a.loc[2025, "mean"]), median_2025=float(a.loc[2025, "median"]),
               mean_growth=float(a.loc[2025, "mean"] / a.loc[2016, "mean"] - 1), median_growth=float(a.loc[2025, "median"] / a.loc[2016, "median"] - 1),
               share_below_min=float(a.share_below_mean.min()), share_below_max=float(a.share_below_mean.max()))
    (RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(a.round(2).to_string())


if __name__ == "__main__":
    main()
