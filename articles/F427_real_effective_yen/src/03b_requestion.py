"""03b 問い直し：物価の差（相対物価）の下がり方は、日本の物価が上がり始めた2022年以降に止まったのか。
相対物価の前年比（年平均）を1996〜2025年で並べ、期間ごとの平均を比べる。
最新12か月（2025年10月〜2026年9月）の前年同期比も出す。
出力：results/requestion.json, results/relprice_yoy.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    a = pd.read_csv(R / "annual.csv").set_index("year")
    e = pd.read_csv(D / "monthly.csv").set_index("ym")
    yoy = (a.relprice / a.relprice.shift(1) - 1) * 100
    t = pd.DataFrame({"relprice_yoy_pct": yoy, "neer_yoy_pct": (a.neer / a.neer.shift(1) - 1) * 100, "reer_yoy_pct": (a.reer / a.reer.shift(1) - 1) * 100}).loc[1971:2025]
    t.round(4).to_csv(R / "relprice_yoy.csv")
    last12 = e.relprice.iloc[-12:].mean(); prev12 = e.relprice.iloc[-24:-12].mean()
    out = dict(relprice_yoy_mean_1996_2012=float(t.loc[1996:2012, "relprice_yoy_pct"].mean()),
               relprice_yoy_mean_2013_2021=float(t.loc[2013:2021, "relprice_yoy_pct"].mean()),
               relprice_yoy_mean_2022_2025=float(t.loc[2022:2025, "relprice_yoy_pct"].mean()),
               relprice_yoy_2025=float(t.loc[2025, "relprice_yoy_pct"]), relprice_last12_vs_prev12=float((last12 / prev12 - 1) * 100),
               neer_yoy_mean_2022_2025=float(t.loc[2022:2025, "neer_yoy_pct"].mean()),
               years_relprice_up_since_1996=[int(y) for y in t.loc[1996:2025].index[t.loc[1996:2025, "relprice_yoy_pct"] > 0]])
    json.dump({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
