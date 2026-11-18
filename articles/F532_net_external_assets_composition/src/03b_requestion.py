"""03b 問い直し（結果を見てから足した）：
2019〜2025年の財務省の試算で、為替で増えた純資産を「その他調整」が打ち消していた。
その他調整（主に株価・債券価格などの変化）と為替を、項目ごとに「資産の分−負債の分」の純額で見る。
あわせて、外貨建ての資産・負債（試算の注記）から、外貨建ての純額を年ごとに出す。
出力：results/requestion_net_by_item.csv、results/requestion_fx_position.csv、results/requestion.json
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, X = ROOT / "data", ROOT / "results", ROOT / "data" / "extracted"
fac = pd.read_csv(D / "factors.csv")
m = json.load(open(R / "main.json", encoding="utf-8"))
ITEMS = ["直接投資", "証券投資", "金融派生商品", "その他投資", "外貨準備"]


def main():
    g = fac[fac["item"] != "合計"].groupby(["item", "side"])[["flow", "fx", "other", "change"]].sum() / 1000
    rows = []
    for it in ITEMS:
        a = g.loc[(it, "assets")]
        l = g.loc[(it, "liabilities")] if (it, "liabilities") in g.index else pd.Series(0.0, index=a.index)
        rows.append({"item": it, **{f"net_{k}_tn": round(float(a[k] - l[k]), 1) for k in ["flow", "fx", "other", "change"]},
                     "assets_other_tn": round(float(a["other"]), 1), "liab_other_tn": round(float(l["other"]), 1),
                     "assets_fx_tn": round(float(a["fx"]), 1), "liab_fx_tn": round(float(l["fx"]), 1)})
    df = pd.DataFrame(rows)
    tot = fac[(fac.side == "net") & (fac.item == "合計")][["flow", "fx", "other", "change"]].sum() / 1000
    df.to_csv(R / "requestion_net_by_item.csv", index=False)
    fxp = pd.read_csv(X / "fx_denominated.csv")
    fxp["net_fx_tn"] = (fxp["assets_fx_tn"] - fxp["liab_fx_tn"]).round(1)
    fxp["fx_share_assets_pct"] = (fxp["assets_fx_tn"] / fxp["assets_tn"] * 100).round(1)
    fxp["fx_share_liab_pct"] = (fxp["liab_fx_tn"] / fxp["liab_tn"] * 100).round(1)
    fxp.to_csv(R / "requestion_fx_position.csv", index=False)
    q = {"period": "2019〜2025年（財務省の試算の累計、兆円）",
         "net_total": {k: round(float(v), 1) for k, v in tot.items()},
         "sum_items_net_other_tn": round(float(df["net_other_tn"].sum()), 1),
         "portfolio_assets_other_tn": float(df.set_index("item").loc["証券投資", "assets_other_tn"]),
         "portfolio_liab_other_tn": float(df.set_index("item").loc["証券投資", "liab_other_tn"]),
         "portfolio_net_other_tn": float(df.set_index("item").loc["証券投資", "net_other_tn"]),
         "di_net_other_tn": float(df.set_index("item").loc["直接投資", "net_other_tn"]),
         "net_fx_position_2025_tn": float(fxp.set_index("year").loc[2025, "net_fx_tn"]),
         "net_fx_position_2019_tn": float(fxp.set_index("year").loc[2019, "net_fx_tn"]),
         "fx_share_assets_2025_pct": float(fxp.set_index("year").loc[2025, "fx_share_assets_pct"]),
         "fx_share_liab_2025_pct": float(fxp.set_index("year").loc[2025, "fx_share_liab_pct"]),
         "net_fx_position_vs_net_iip_2025_pct": round(float(fxp.set_index("year").loc[2025, "net_fx_tn"]) / m["net_2025_tn"] * 100, 1),
         "yen_net_position_2025_tn": round(m["net_2025_tn"] - float(fxp.set_index("year").loc[2025, "net_fx_tn"]), 1)}
    json.dump(q, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(df.to_string()); print(fxp.to_string()); print(q)


if __name__ == "__main__":
    main()
