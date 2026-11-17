"""問い直し（結果を見てから足した）：2026年に中国からの訪日客が減った月に、百貨店の商品別の販売額はどう動いたか。
2026年1〜9月と2025年1〜9月を比べ、前年同月比の月ごとの連動も見る。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
JA = {"total": "合計", "accessories": "身の回り品", "other_goods": "その他の商品", "food": "飲食料品", "clothes": "衣料品計",
      "visitors": "訪日外客数（総数）", "visitors_china": "訪日外客数（中国）"}


def main():
    d = pd.read_csv(D / "dept_monthly.csv")
    v = pd.read_csv(D / "visitors_monthly.csv")
    mm = d.merge(v, on=["year", "month"]).sort_values(["year", "month"]).reset_index(drop=True)
    cols = ["total", "accessories", "other_goods", "food", "clothes", "visitors", "visitors_china"]
    out = {"jan_sep_2026_vs_2025_pct": {}}
    s25 = mm[(mm.year == 2025) & (mm.month <= 9)][cols].sum()
    s26 = mm[(mm.year == 2026) & (mm.month <= 9)][cols].sum()
    for c in cols:
        out["jan_sep_2026_vs_2025_pct"][JA[c]] = round(float((s26[c] / s25[c] - 1) * 100), 2)
    yo = mm.copy()
    for c in cols:
        yo[c + "_yoy"] = yo[c].pct_change(12) * 100
    yo = yo[(yo.year * 100 + yo.month >= 202401) & (yo.year * 100 + yo.month <= 202609)]
    yo[["year", "month"] + [c + "_yoy" for c in cols]].to_csv(R / "requestion_yoy.csv", index=False, float_format="%.3f")
    out["n_months"] = int(len(yo))
    out["corr_yoy_china"] = {JA[c]: round(float(stats.pearsonr(yo["visitors_china_yoy"], yo[c + "_yoy"])[0]), 3) for c in ["total", "accessories", "other_goods", "food", "clothes"]}
    out["corr_yoy_total_visitors"] = {JA[c]: round(float(stats.pearsonr(yo["visitors_yoy"], yo[c + "_yoy"])[0]), 3) for c in ["total", "accessories", "other_goods", "food", "clothes"]}
    out["monthly_2026"] = [{"month": int(x.month), "china_yoy": round(float(x.visitors_china_yoy), 1), "visitors_yoy": round(float(x.visitors_yoy), 1),
                            "dept_yoy": round(float(x.total_yoy), 1), "accessories_yoy": round(float(x.accessories_yoy), 1),
                            "other_goods_yoy": round(float(x.other_goods_yoy), 1), "food_yoy": round(float(x.food_yoy), 1)}
                           for x in yo[yo.year == 2026].itertuples()]
    (R / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
