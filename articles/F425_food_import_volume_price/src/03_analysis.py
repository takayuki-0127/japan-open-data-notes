"""03 分析：金額＝数量×ドル単価×ドル円 の対数分解（品目別・5品目合計）、輸入物価指数での分解、頑健性。
出力：results/main.json, results/decomp_items.csv, results/robustness.csv, results/item_levels.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
ITEMS = ["fish", "meat", "cereals", "vegetables", "fruit"]
JP = {"fish": "魚介類", "meat": "肉類", "cereals": "穀物類", "vegetables": "野菜", "fruit": "果実", "soybeans": "大豆", "total5": "5品目の合計"}


def decomp(f, fx, y0, y1, items, fxcol="usdjpy_avg"):
    rows = []
    for it in items:
        g = f[f.item == it].set_index("year")
        v0, v1 = g.loc[y0, "value_thousand_yen"], g.loc[y1, "value_thousand_yen"]
        q0, q1 = g.loc[y0, "quantity_t"], g.loc[y1, "quantity_t"]
        lv = np.log(v1 / v0); lq = np.log(q1 / q0); lfx = np.log(fx.loc[y1, fxcol] / fx.loc[y0, fxcol])
        lp = lv - lq - lfx
        rows.append(dict(item=it, value0=v0 / 1e9, value1=v1 / 1e9, value_g=(np.exp(lv) - 1) * 100, qty_g=(np.exp(lq) - 1) * 100,
                         usd_price_g=(np.exp(lp) - 1) * 100, fx_g=(np.exp(lfx) - 1) * 100, yen_price_g=(np.exp(lp + lfx) - 1) * 100,
                         l_value=lv, l_qty=lq, l_usd_price=lp, l_fx=lfx))
    t = pd.DataFrame(rows)
    sh = (t.value0 / t.value0.sum() + t.value1 / t.value1.sum()) / 2   # ディビジア型の重み
    tot = {k: float((t[k] * sh).sum()) for k in ["l_value", "l_qty", "l_usd_price", "l_fx"]}
    tot_row = dict(item="total5", value0=t.value0.sum(), value1=t.value1.sum(), value_g=(t.value1.sum() / t.value0.sum() - 1) * 100,
                   qty_g=(np.exp(tot["l_qty"]) - 1) * 100, usd_price_g=(np.exp(tot["l_usd_price"]) - 1) * 100, fx_g=(np.exp(tot["l_fx"]) - 1) * 100,
                   yen_price_g=(np.exp(tot["l_usd_price"] + tot["l_fx"]) - 1) * 100, **tot)
    t = pd.concat([t, pd.DataFrame([tot_row])], ignore_index=True)
    for k in ["l_qty", "l_usd_price", "l_fx"]:
        t["share_" + k[2:]] = t[k] / (t.l_qty + t.l_usd_price + t.l_fx) * 100
    return t


def main():
    f = pd.read_csv(D / "food_annual.csv")
    fx = pd.read_csv(D / "fx_prices_annual.csv").set_index("year")
    lv = f.pivot(index="year", columns="item", values="value_thousand_yen") / 1e9   # 兆円
    lq = f.pivot(index="year", columns="item", values="quantity_t") / 1e6           # 百万トン
    lv.join(lq, lsuffix="_value_cho", rsuffix="_qty_mt").round(5).to_csv(R / "item_levels.csv")
    t = decomp(f, fx, 2020, 2025, ITEMS)
    t["name"] = t.item.map(JP)
    t.round(4).to_csv(R / "decomp_items.csv", index=False)
    tt = t.set_index("item")
    cover = float(lv.loc[2025, ITEMS].sum() / lv.loc[2025, "food_total"] * 100)
    ipi = fx[["ipi_food_yen", "ipi_food_contract"]]
    ly = np.log(ipi.loc[2025, "ipi_food_yen"] / ipi.loc[2020, "ipi_food_yen"]); lc = np.log(ipi.loc[2025, "ipi_food_contract"] / ipi.loc[2020, "ipi_food_contract"])
    main = dict(food_total_2020=float(lv.loc[2020, "food_total"]), food_total_2025=float(lv.loc[2025, "food_total"]),
                food_total_g=float((lv.loc[2025, "food_total"] / lv.loc[2020, "food_total"] - 1) * 100), cover_5items_2025=cover,
                usdjpy_2020=float(fx.loc[2020, "usdjpy_avg"]), usdjpy_2025=float(fx.loc[2025, "usdjpy_avg"]),
                **{f"t5_{k}": float(tt.loc["total5", k]) for k in ["value_g", "qty_g", "usd_price_g", "fx_g", "yen_price_g", "share_qty", "share_usd_price", "share_fx"]},
                n_qty_down=int((tt.loc[ITEMS, "qty_g"] < 0).sum()),
                ipi_food_yen_g=float((np.exp(ly) - 1) * 100), ipi_food_contract_g=float((np.exp(lc) - 1) * 100), ipi_fx_share=float((ly - lc) / ly * 100),
                **{f"{it}_{k}": float(tt.loc[it, k]) for it in ITEMS for k in ["value_g", "qty_g", "usd_price_g", "yen_price_g"]})
    main["H1"] = "支持" if main["t5_share_qty"] < 20 else "外れ"
    main["H2"] = "支持" if tt.loc["total5", "l_fx"] > tt.loc["total5", "l_usd_price"] else "外れ"
    main["H3"] = "支持" if main["n_qty_down"] >= 3 else "外れ"
    main["H4"] = "支持" if main["ipi_fx_share"] >= 50 else "外れ"
    rob = []
    for lab, y0, y1, col in [("2020→2025年（本線）", 2020, 2025, "usdjpy_avg"), ("2019→2025年", 2019, 2025, "usdjpy_avg"),
                             ("2012→2025年", 2012, 2025, "usdjpy_avg"), ("2020→2025年・年末のドル円", 2020, 2025, "usdjpy_dec")]:
        x = decomp(f, fx, y0, y1, ITEMS, col).set_index("item").loc["total5"]
        rob.append(dict(check=lab, value_g=x.value_g, qty_g=x.qty_g, usd_price_g=x.usd_price_g, fx_g=x.fx_g, share_qty=x.share_qty, share_usd_price=x.share_usd_price, share_fx=x.share_fx))
    # 単純合計（トンで合わせる）
    s0 = f[(f.year == 2020) & f.item.isin(ITEMS)]; s1 = f[(f.year == 2025) & f.item.isin(ITEMS)]
    lq_ = np.log(s1.quantity_t.sum() / s0.quantity_t.sum()); lv_ = np.log(s1.value_thousand_yen.sum() / s0.value_thousand_yen.sum())
    lfx_ = np.log(fx.loc[2025, "usdjpy_avg"] / fx.loc[2020, "usdjpy_avg"])
    rob.append(dict(check="5品目の単純合計（トン）", value_g=(np.exp(lv_) - 1) * 100, qty_g=(np.exp(lq_) - 1) * 100, usd_price_g=(np.exp(lv_ - lq_ - lfx_) - 1) * 100,
                    fx_g=(np.exp(lfx_) - 1) * 100, share_qty=lq_ / lv_ * 100, share_usd_price=(lv_ - lq_ - lfx_) / lv_ * 100, share_fx=lfx_ / lv_ * 100))
    rob.append(dict(check="輸入物価指数（飲食料品・食料用農水産物）", value_g=np.nan, qty_g=np.nan, usd_price_g=main["ipi_food_contract_g"], fx_g=np.nan,
                    share_qty=np.nan, share_usd_price=100 - main["ipi_fx_share"], share_fx=main["ipi_fx_share"]))
    pd.DataFrame(rob).round(3).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print(t[["name", "value_g", "qty_g", "usd_price_g", "fx_g", "share_qty", "share_usd_price", "share_fx"]].round(1).to_string())


if __name__ == "__main__":
    main()
