"""03b 問い直し：2005年からの第一次所得収支の増え方は、円安でどこまで説明できるか。どの収益が増やしたか。
- 2012年（円高の終わり）→2025年と、2005→2025年で、円とドル建ての伸びを比べ、円での伸び（対数）のうちドル円の変化にあたる割合を出す。
- 2005→2025年の増加を、直接投資収益・証券投資収益・その他に分ける。
出力：results/requestion.json, results/growth_contrib.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    out = {}
    for y0 in (2005, 2012):
        gy = a.loc[2025, "primary"] / a.loc[y0, "primary"]
        gu = a.loc[2025, "primary_usd"] / a.loc[y0, "primary_usd"]
        out[f"primary_yen_growth_{y0}_pct"] = float((gy - 1) * 100)
        out[f"primary_usd_growth_{y0}_pct"] = float((gu - 1) * 100)
        out[f"fx_share_of_log_growth_{y0}_pct"] = float((np.log(gy) - np.log(gu)) / np.log(gy) * 100)
        out[f"usdjpy_{y0}"] = float(a.loc[y0, "usdjpy"])
        out[f"primary_usd_{y0}"] = float(a.loc[y0, "primary_usd"])
    out["usdjpy_2025"] = float(a.loc[2025, "usdjpy"]); out["primary_usd_2025"] = float(a.loc[2025, "primary_usd"])
    a = a.drop(columns=["source"])
    d = a.loc[2025] - a.loc[2005]
    rows = []
    for c, lab in [("di_dividends", "直接投資収益：配当金等"), ("di_reinvested", "直接投資収益：再投資収益"), ("di_interest", "直接投資収益：利子"),
                   ("pf_dividends", "証券投資収益：配当金"), ("pf_bond_interest", "証券投資収益：債券利子"),
                   ("other_invest_income", "その他投資収益"), ("comp_employees", "雇用者報酬")]:
        rows.append(dict(item=lab, change_cho=float(d[c] / 1e4), share_pct=float(d[c] / d["primary"] * 100)))
    oth = d["primary"] - sum(d[c] for c in ["di_dividends", "di_reinvested", "di_interest", "pf_dividends", "pf_bond_interest", "other_invest_income", "comp_employees"])
    rows.append(dict(item="その他第一次所得", change_cho=float(oth / 1e4), share_pct=float(oth / d["primary"] * 100)))
    g = pd.DataFrame(rows)
    g.round(4).to_csv(R / "growth_contrib.csv", index=False)
    out["primary_change_2005_2025_cho"] = float(d["primary"] / 1e4)
    out["di_change_share_pct"] = float(g[g.item.str.startswith("直接")].share_pct.sum())
    out["pf_change_share_pct"] = float(g[g.item.str.startswith("証券")].share_pct.sum())
    json.dump({k: round(v, 3) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(g)


if __name__ == "__main__":
    main()
