"""03b 問い直し（結果を見てから足した）：
夏の長さの延びは、6〜9月の平均気温の上がり方でどこまで説明できるか。
地点ごとに「その年の夏の長さ」を「その年の6〜9月の平均気温」に直線で当てはめ（年ごとの上下から求めた1℃あたりの日数）、
1901〜1930年→1996〜2025年の6〜9月の気温の上がり方に掛けて、見込まれる延びと実際の延びを比べる。
さらに、年ごとの上下だけから求めた関係が長期の変化にも当てはまるかを見るため、長期の傾き（年）を除いた残差どうしでも当てはめる。
出力：results/requestion.csv, results/requestion.json
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"


def main():
    d = pd.read_csv(DATA / "daily_summary.csv")
    d = d[d["missing_apr_nov"] <= 5]
    main_st = json.loads((RES / "main.json").read_text(encoding="utf-8"))["stations_main"]
    out = []
    for s in main_st:
        x = d[d.station == s].dropna(subset=["tmean_jjas"]).sort_values("year")
        T, L, yr = x.tmean_jjas.values, x.abs25_w7_len.values.astype(float), x.year.values.astype(float)
        b_raw = np.polyfit(T, L, 1)[0]
        # 年の直線を除いた残差どうし（年ごとの上下だけの関係）
        rT = T - np.polyval(np.polyfit(yr, T, 1), yr)
        rL = L - np.polyval(np.polyfit(yr, L, 1), yr)
        b_detr = np.polyfit(rT, rL, 1)[0]
        a, b = x[x.year.between(1901, 1930)], x[x.year.between(1996, 2025)]
        dT = b.tmean_jjas.mean() - a.tmean_jjas.mean()
        dL = b.abs25_w7_len.mean() - a.abs25_w7_len.mean()
        out.append({"station": s, "days_per_degC": b_raw, "days_per_degC_detrended": b_detr, "dT_jjas": dT,
                    "dL_actual": dL, "dL_expected_detrended": b_detr * dT, "ratio_actual_to_expected": dL / (b_detr * dT)})
    t = pd.DataFrame(out)
    t.round(3).to_csv(RES / "requestion.csv", index=False)
    med = lambda v: float(np.round(np.nanmedian(v), 2))
    r = {"days_per_degC_median": med(t.days_per_degC), "days_per_degC_detrended_median": med(t.days_per_degC_detrended),
         "dT_jjas_median": med(t.dT_jjas), "dL_actual_median": med(t.dL_actual),
         "dL_expected_detrended_median": med(t.dL_expected_detrended), "ratio_median": med(t.ratio_actual_to_expected),
         "ratio_min": float(np.round(t.ratio_actual_to_expected.min(), 2)), "ratio_max": float(np.round(t.ratio_actual_to_expected.max(), 2))}
    (RES / "requestion.json").write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(t.round(2).to_string())
    print(r)


if __name__ == "__main__":
    main()
