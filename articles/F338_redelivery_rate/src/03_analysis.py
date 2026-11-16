"""03 分析：再配達率の下がり方、地域・季節の違い、3社と6社の差"""
import json, pathlib
import numpy as np, pandas as pd
from scipy.stats import theilslopes

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)


def t(p):
    return int(p[:4]) + (int(p[5:]) - 1) / 12


def main():
    d = pd.read_csv(ROOT / "data" / "series.csv")
    S3 = d[(d.base == "3社")].pivot(index="period", columns="area", values="rate")
    S6 = d[(d.base == "6社")].pivot(index="period", columns="area", values="rate")
    S3.round(4).to_csv(RES / "rate_3sha.csv"); S6.round(4).to_csv(RES / "rate_6sha.csv")
    tot = S3["総計"].dropna()

    def slope(s, drop2020=True):
        s = s.dropna()
        if drop2020:
            s = s.drop("2020-04", errors="ignore")
        return float(theilslopes(s.values, [t(p) for p in s.index])[0])

    first, last = tot.index[0], tot.index[-1]
    areas = ["都市部", "都市部近郊", "地方"]
    ar = {a: dict(r0=float(S3.loc["2017-10", a]), r1=float(S3.loc["2024-10", a]),
                  pt=float(S3.loc["2024-10", a] - S3.loc["2017-10", a]),
                  pct=float(100 * (S3.loc["2024-10", a] / S3.loc["2017-10", a] - 1)),
                  slope=slope(S3[a])) for a in areas}
    urban_gt_rural = bool((S3["都市部"].dropna() > S3["地方"].dropna()).all())
    n_rural_higher = int((S3["都市部"].dropna() < S3["地方"].dropna()).sum())
    # 季節：同じ年度の4月と10月（10月−同じ年の4月）
    pairs = []
    for y in range(2018, 2026):
        a, b = f"{y}-04", f"{y}-10"
        if a in tot.index and b in tot.index and a != "2020-04":
            pairs.append((y, float(tot[b] - tot[a])))
    # 3社と6社の差
    both = pd.concat([S3["総計"], S6["総計"]], axis=1, keys=["s3", "s6"]).dropna()
    both["diff"] = both.s3 - both.s6
    both.round(4).to_csv(RES / "base_diff.csv")
    # 問い直し：再配達数そのもの（3社の総計、配達総数との関係）
    cnt = d[(d.base == "3社") & (d.area == "総計")].set_index("period")[["total", "redelivered"]]
    cnt.to_csv(RES / "counts_3sha.csv")
    m = dict(first=first, last=last, r_first=float(tot[first]), r_last=float(tot[last]),
             drop_pt=float(tot[last] - tot[first]), drop_pct=float(100 * (tot[last] / tot[first] - 1)),
             slope_per_year=slope(tot), slope_with2020=slope(tot, False),
             slope_to_2024_10=slope(tot.loc[:"2024-10"]),
             pre_covid_mean=float(tot.loc["2017-10":"2019-10"].mean()),
             r_2019_04=float(tot["2019-04"]), r_2020_04=float(tot["2020-04"]), r_2020_10=float(tot["2020-10"]),
             areas=ar, urban_gt_rural_all=urban_gt_rural, n_rural_higher=n_rural_higher,
             season_pairs=pairs, season_mean=float(np.mean([p[1] for p in pairs])),
             n_oct_higher=int(sum(p[1] > 0 for p in pairs)), n_pairs=len(pairs),
             s6_first=float(S6["総計"].dropna().iloc[0]), s6_last=float(S6["総計"].dropna().iloc[-1]),
             s6_first_period=S6["総計"].dropna().index[0], base_diff_mean=float(both["diff"].mean()),
             base_diff_min=float(both["diff"].min()), base_diff_max=float(both["diff"].max()),
             s6_areas_2026=S6.loc["2026-04", areas].round(2).to_dict())
    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1))
    print(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
