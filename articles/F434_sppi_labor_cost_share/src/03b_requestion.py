"""03b 問い直し：2021年からは低人件費率の方が上がった。それは2021〜22年の一時の動きで、その後は逆転したのか。
年ごとの前年比（年平均）の差（高−低）と、各年の12か月のうち高人件費率の前年比の方が高かった月の数を数える。
あわせて、2023年平均→最新の上昇率を比べる。
出力：results/requestion.json, results/yearly_gap.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    e = pd.read_csv(D / "extax.csv").set_index("ym")
    ae = pd.read_csv(R / "annual.csv").set_index("year")
    yoy = pd.read_csv(R / "yoy.csv").set_index("ym")
    ay = (ae / ae.shift(1) - 1) * 100
    gap_m = (yoy.high_labor - yoy.low_labor).dropna()
    rows = []
    for y in range(2001, 2027):
        g = gap_m[(gap_m.index // 100) == y]
        rows.append(dict(year=y, high_yoy=float(ay.loc[y, "high_labor"]) if y in ay.index else np.nan, low_yoy=float(ay.loc[y, "low_labor"]) if y in ay.index else np.nan,
                         months_high_above=int((g > 0).sum()), months=int(len(g))))
    t = pd.DataFrame(rows); t["gap"] = t.high_yoy - t.low_yoy
    t.round(4).to_csv(R / "yearly_gap.csv", index=False)
    last = int(e.index[-1])
    out = dict(high_since2023=float((e.loc[last, "high_labor"] / ae.loc[2023, "high_labor"] - 1) * 100),
               low_since2023=float((e.loc[last, "low_labor"] / ae.loc[2023, "low_labor"] - 1) * 100),
               gap_2021=float(t.set_index("year").loc[2021, "gap"]), gap_2022=float(t.set_index("year").loc[2022, "gap"]),
               gap_2024=float(t.set_index("year").loc[2024, "gap"]), gap_2025=float(t.set_index("year").loc[2025, "gap"]),
               years_high_above_2001_2020=int((t[(t.year <= 2020)].gap > 0).sum()), n_years_2001_2020=20,
               months_high_above_2026=int(t.set_index("year").loc[2026, "months_high_above"]), months_2026=int(t.set_index("year").loc[2026, "months"]))
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t.round(2).to_string()); print(out)


if __name__ == "__main__":
    main()
