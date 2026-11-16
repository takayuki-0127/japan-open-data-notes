"""03b 問い直し：再投資収益を除くと、「所得収支が貿易収支を上回った年」はいつになるか。
また、再投資の割合はドル円の動きとどう並ぶか（円安の年に配当で戻す割合が上がるか）。
出力：results/requestion.json
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"


def main():
    s = pd.read_csv(R / "annual_shares.csv").set_index("year")
    above = s.primary_ex_reinv > s.trade
    first_cash = int(min(y for y in s.index if above.loc[y:].all()))
    first_book = int(min(y for y in s.index if (s.primary > s.trade).loc[y:].all()))
    dfx = np.log(s.usdjpy).diff() * 100
    up = s.index[dfx > 5]; down = s.index[dfx < -5]
    dsh = s.reinv_share_rec.diff()
    out = dict(first_year_cash=first_cash, first_year_book=first_book,
               yen_weak_years=[int(y) for y in up], yen_strong_years=[int(y) for y in down],
               share_change_yen_weak_mean=float(dsh.loc[up].mean()), share_change_yen_strong_mean=float(dsh.loc[down].mean()),
               ca_ex_reinv_2022=float(s.loc[2022, "ca_ex_reinv"]), ca_2022=float(s.loc[2022, "ca"]),
               reinv_share_2021=float(s.loc[2021, "reinv_share_rec"]), reinv_share_2025=float(s.loc[2025, "reinv_share_rec"]),
               usdjpy_2021=float(s.loc[2021, "usdjpy"]), usdjpy_2025=float(s.loc[2025, "usdjpy"]))
    json.dump({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out)


if __name__ == "__main__":
    main()
