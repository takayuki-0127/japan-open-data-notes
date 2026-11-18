"""問い直し（結果を見てから足した）：ぶどうの産出額と1kg あたり産出額の伸びは、いつ起きたのか。
2004→2014年と2014→2024年の年率（幾何平均）で、主な7品目をくらべる。2024年はみかんの収穫が特に少ない年なので、2023年で終える場合も出す。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"
MAIN = ["みかん", "ぶどう", "りんご", "日本なし", "もも", "かき", "おうとう"]


def cagr(a, b, n):
    return round(float(((b / a) ** (1 / n) - 1) * 100), 1)


def main():
    s = pd.read_csv(R / "national_series.csv").set_index(["item", "year"])
    rows = []
    for it in MAIN:
        g = s.loc[it]
        rows.append({"item": it,
                     "value_cagr_2004_2014": cagr(g.value_oku[2004], g.value_oku[2014], 10), "value_cagr_2014_2024": cagr(g.value_oku[2014], g.value_oku[2024], 10),
                     "unit_cagr_2004_2014": cagr(g.unit_value_yen_kg[2004], g.unit_value_yen_kg[2014], 10),
                     "unit_cagr_2014_2024": cagr(g.unit_value_yen_kg[2014], g.unit_value_yen_kg[2024], 10),
                     "unit_cagr_2014_2023": cagr(g.unit_value_yen_kg[2014], g.unit_value_yen_kg[2023], 9),
                     "harvest_cagr_2014_2024": cagr(g.harvest_t[2014], g.harvest_t[2024], 10)})
    df = pd.DataFrame(rows)
    df.to_csv(R / "requestion_cagr.csv", index=False)
    b = s.loc["ぶどう"]
    jumps = (b.value_oku.pct_change() * 100).loc[2004:2024].round(1)
    big = {str(int(y)): float(v) for y, v in jumps.items() if v >= 10}
    out = {"cagr": {r.item: {k: getattr(r, k) for k in df.columns if k != "item"} for r in df.itertuples()},
           "budou_value_jump_years_ge10pct": big,
           "budou_value_2014_2020": {"2014": float(b.value_oku[2014]), "2017": float(b.value_oku[2017]), "2020": float(b.value_oku[2020])},
           "budou_share_of_fruit_value": {str(y): round(float(b.share_of_fruit_value_pct[y]), 1) for y in [2004, 2014, 2020, 2024]},
           "mikan_share_of_fruit_value": {str(y): round(float(s.loc["みかん"].share_of_fruit_value_pct[y]), 1) for y in [2004, 2014, 2020, 2024]}}
    json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
    print(df.to_string()); print(json.dumps({k: out[k] for k in list(out)[1:]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
