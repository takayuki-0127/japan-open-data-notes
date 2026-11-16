"""03b 問い直し：旅行の黒字が2.5倍になったのに、サービス収支の赤字はなぜ縮まらなかったのか。
2019→2025年の変化を、旅行・輸送・その他サービスに分ける。
出力：results/requestion.json, results/services_change.csv
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"


def main():
    t = pd.read_csv(R / "annual_table.csv").set_index("year")
    rows = []
    for c, lab in [("travel", "旅行"), ("transport", "輸送"), ("other_services", "その他サービス"), ("services", "サービス収支 計")]:
        rows.append(dict(item=lab, y2019=float(t.loc[2019, c]), y2025=float(t.loc[2025, c]), change=float(t.loc[2025, c] - t.loc[2019, c])))
    g = pd.DataFrame(rows)
    g.round(4).to_csv(R / "services_change.csv", index=False)
    out = {f"{r['item']}_change": r["change"] for r in rows}
    out["travel_offset_pct"] = float(g.loc[0, "change"] / -g.loc[2, "change"] * 100)
    json.dump({k: round(v, 3) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(g, out)


if __name__ == "__main__":
    main()
