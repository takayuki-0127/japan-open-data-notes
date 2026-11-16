"""03b 問い直し：二つの花の早まり方の違いは、咲く前の月の気温の上がり方の違いで説明できるか。
- 日本の月平均気温偏差（15地点平均）から、うめは1〜2月、さくらは2〜3月の平均偏差をとる。
- 年ごとの開花の偏差（両方そろう地点の平均）を、その気温偏差に回帰して「1℃あたりの日数」を出す。
- 気温の傾き（10年あたり℃）を、1961〜2025年と1991〜2025年で比べる。
出力：results/requestion.json, results/temp_months.csv
"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
WIN = {"ume": ["1月", "2月"], "sakura": ["2月", "3月"]}


def main():
    t = pd.read_csv(D / "raw" / "mon_jpn.csv", encoding="cp932")
    t = t.rename(columns={"年": "year"}).set_index("year").apply(pd.to_numeric, errors="coerce")
    ym = pd.read_csv(R / "yearly_mean.csv")
    out, rows = {}, []
    for k, months in WIN.items():
        temp = t[months].mean(axis=1).rename("temp")
        s = ym[ym.kind == k].set_index("year")["mean"].rename("anom").to_frame().join(temp, how="inner")
        s = s.loc[1961:2025]
        b = np.polyfit(s.temp, s.anom, 1)[0]
        r = float(np.corrcoef(s.temp, s.anom)[0, 1])
        out[f"{k}_days_per_degC"] = float(b)
        out[f"{k}_r_temp"] = r
        for y0 in (1961, 1991):
            tt = temp.loc[y0:2025]
            out[f"{k}_temp_slope10_{y0}"] = float(np.polyfit(tt.index, tt.values, 1)[0] * 10)
            aa = s.loc[y0:2025]
            out[f"{k}_bloom_slope10_{y0}"] = float(np.polyfit(aa.index, aa.anom, 1)[0] * 10)
            out[f"{k}_implied_slope10_{y0}"] = float(b * out[f"{k}_temp_slope10_{y0}"])
        # レビューで追加：最近の傾きの95%区間と、始まりの年を変えたときの傾き（両方そろう地点の平均の系列）
        for y0 in (1986, 1991, 1995):
            aa = s.loc[y0:2025]
            lr = stats.linregress(aa.index.values.astype(float), aa.anom.values)
            out[f"{k}_rv_slope10_from{y0}"] = float(lr.slope * 10)
            out[f"{k}_rv_ci95_halfwidth10_from{y0}"] = float(1.96 * lr.stderr * 10)
        for y, v in temp.loc[1961:2025].items():
            rows.append((k, "+".join(months), int(y), round(float(v), 4)))
    pd.DataFrame(rows, columns=["kind", "months", "year", "temp_anom"]).to_csv(R / "temp_months.csv", index=False)
    json.dump({k: round(v, 4) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, indent=0))


if __name__ == "__main__":
    main()
