"""03b 問い直し：コアとコアコアの差は、どれだけエネルギーで説明でき、長い目で見ると打ち消し合うのか。
(1) 差（コア−コアコア）と、エネルギーの前年比×ウエイトの割合（近似の寄与）の関係（2000年〜）。
(2) 2021年平均→2026年9月の水準の上がり方（累積）を比べる。
出力：results/requestion.json
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    d = pd.read_csv(D / "cpi.csv").set_index("ym")
    y = pd.read_csv(R / "yoy.csv").set_index("ym").loc[200001:].dropna(subset=["gap", "energy_contrib"])
    b = np.polyfit(y.energy_contrib, y.gap, 1)
    r = float(np.corrcoef(y.energy_contrib, y.gap)[0, 1])
    a21 = d.loc[202101:202112].mean(); last = d.index[-1]
    cum = (d.loc[last] / a21 - 1) * 100
    out = dict(corr_gap_energy=r, r2_gap_energy=r * r, slope=float(b[0]),
               cum_core=float(cum.core), cum_corecore=float(cum.corecore), cum_headline=float(cum.headline), cum_us_core=float(cum.us_core), cum_energy=float(cum.energy))
    json.dump({k: round(v, 4) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
