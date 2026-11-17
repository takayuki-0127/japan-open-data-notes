"""03b 問い直し：端末の指数とドル円は、どれくらいの遅れで、どれくらいの大きさで並ぶのか。
ドル円を0〜18か月先行させたときの前年比どうしの相関を並べ、最も強い遅れで傾き（ドル円1%あたりの端末の指数の%）を出す。
期間は2013年1月〜2026年9月。
出力：results/requestion.json, results/lead_corr.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    d = pd.read_csv(D / "monthly.csv").set_index("ym")
    y = (np.log(d.phone_device) - np.log(d.phone_device.shift(12))) * 100
    f = (np.log(d.usdjpy) - np.log(d.usdjpy.shift(12))) * 100
    rows = []
    for lead in range(0, 19):
        s = pd.concat([y, f.shift(lead)], axis=1).loc[201301:202609].dropna()
        rows.append(dict(lead=lead, corr=float(np.corrcoef(s.iloc[:, 0], s.iloc[:, 1])[0, 1]), slope=float(np.polyfit(s.iloc[:, 1], s.iloc[:, 0], 1)[0]), n=len(s)))
    t = pd.DataFrame(rows); t.round(4).to_csv(R / "lead_corr.csv", index=False)
    best = t.loc[t["corr"].idxmax()]
    fee = d.mobile_fee
    out = dict(best_lead=int(best.lead), best_corr=float(best["corr"]), best_slope=float(best.slope),
               fee_2022_min=float(fee.loc[202201:].min()), fee_min_month=int(fee.loc[202201:].idxmin()),
               fee_rise_from_min=float((fee.iloc[-1] / fee.loc[202201:].min() - 1) * 100))
    json.dump({k: round(v, 4) if isinstance(v, float) else v for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t.round(2).to_string()); print(out)


if __name__ == "__main__":
    main()
