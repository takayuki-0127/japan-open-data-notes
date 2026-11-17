"""03b 問い直し：流れの合計が残高の増加より大きいのはなぜか、流れの中身は何か。
年ごとの流れ（株式資本・収益の再投資・負債性資本）と、残高の増加との差（評価の変化など）を並べる。
出力：results/requestion.json, results/yearly_flows.csv
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    t = pd.DataFrame({"increase": a.inward.diff(), "flow": a.flow, "flow_equity": a.flow_equity, "flow_reinv": a.flow_reinv, "flow_debt": a.flow_debt})
    t["other"] = t.increase - t.flow
    t = t.loc[2015:2025]
    t.round(4).to_csv(R / "yearly_flows.csv")
    s = t.sum()
    out = dict(reinv_share_of_flows=float(s.flow_reinv / s.flow * 100), equity_share_of_flows=float(s.flow_equity / s.flow * 100),
               debt_share_of_flows=float(s.flow_debt / s.flow * 100),
               years_other_negative=[int(y) for y in t.index[t.other < 0]], other_min_year=int(t.other.idxmin()), other_min=float(t.other.min()),
               flow_2025=float(t.loc[2025, "flow"]), equity_2025=float(t.loc[2025, "flow_equity"]), reinv_2025=float(t.loc[2025, "flow_reinv"]), debt_2025=float(t.loc[2025, "flow_debt"]),
               increase_2025=float(t.loc[2025, "increase"]))
    json.dump({k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(t.round(2)); print(out)


if __name__ == "__main__":
    main()
