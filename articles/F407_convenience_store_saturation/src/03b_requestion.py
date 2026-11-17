"""問い直し（結果を見てから足した）：店が止まったあと、販売額の伸びは何が支えたのか。
(a) 販売額の変化を「店の数」と「1店あたり」に分ける（対数の差）
(b) 1店あたり販売額の変化を商品別に分ける（2019→2025年）"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
ITEMS = ["ff_daily", "processed", "nonfood", "service"]
JA = {"ff_daily": "FF・日配食品", "processed": "加工食品", "nonfood": "非食品", "service": "サービス"}


def main():
    a = pd.read_csv(R / "annual_national.csv").set_index("year")
    out = {"decomp": [], "items": []}
    for y0, y1 in [(2010, 2016), (2016, 2019), (2019, 2025)]:
        d_tot = np.log(a.loc[y1, "total"] / a.loc[y0, "total"]) * 100
        d_st = np.log(a.loc[y1, "stores_avg"] / a.loc[y0, "stores_avg"]) * 100
        d_ps = np.log(a.loc[y1, "per_store_nom"] / a.loc[y0, "per_store_nom"]) * 100
        d_cpi = np.log(a.loc[y1, "cpi_all"] / a.loc[y0, "cpi_all"]) * 100
        out["decomp"].append({"period": f"{y0}-{y1}", "sales_log_pct": round(d_tot, 2), "stores_log_pct": round(d_st, 2),
                              "per_store_log_pct": round(d_ps, 2), "cpi_log_pct": round(d_cpi, 2),
                              "per_store_real_log_pct": round(d_ps - d_cpi, 2),
                              "stores_share_of_sales_growth_pct": round(d_st / d_tot * 100, 1)})
    y0, y1 = 2019, 2025
    base = a.loc[y0, "per_store_nom"]
    for c in ITEMS:
        p0 = a.loc[y0, c] / a.loc[y0, "stores_avg"]
        p1 = a.loc[y1, c] / a.loc[y1, "stores_avg"]
        out["items"].append({"item": c, "item_ja": JA[c], "per_store_2019_man": round(p0 * 100, 1), "per_store_2025_man": round(p1 * 100, 1),
                             "change_pct": round((p1 / p0 - 1) * 100, 2), "contribution_pt": round((p1 - p0) / base * 100, 2)})
    out["per_store_nom_change_pct_2019_2025"] = round((a.loc[y1, "per_store_nom"] / base - 1) * 100, 2)
    food0 = (a.loc[y0, "ff_daily"] + a.loc[y0, "processed"]) / a.loc[y0, "stores_avg"]
    food1 = (a.loc[y1, "ff_daily"] + a.loc[y1, "processed"]) / a.loc[y1, "stores_avg"]
    out["food_items_per_store_change_pct"] = round((food1 / food0 - 1) * 100, 2)
    out["food_items_per_store_real_food_cpi_pct"] = round((food1 / food0 / (a.loc[y1, "cpi_food"] / a.loc[y0, "cpi_food"]) - 1) * 100, 2)
    out["nonfood_service_per_store_real_all_cpi_pct"] = round(
        ((a.loc[y1, "nonfood"] + a.loc[y1, "service"]) / a.loc[y1, "stores_avg"]) / ((a.loc[y0, "nonfood"] + a.loc[y0, "service"]) / a.loc[y0, "stores_avg"])
        / (a.loc[y1, "cpi_all"] / a.loc[y0, "cpi_all"]) * 100 - 100, 2)
    pd.DataFrame(out["decomp"]).to_csv(R / "requestion_decomp.csv", index=False)
    pd.DataFrame(out["items"]).to_csv(R / "requestion_items.csv", index=False)
    (R / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
