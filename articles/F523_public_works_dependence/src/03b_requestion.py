"""問い直し：差（ポイント）は縮まったが、倍率で見るとどうか。建設の中での公共の割合は下がったのか。
1) 地方圏の中央値÷三大都市圏の中央値（倍）を年度ごとに。2) 建設の出来高に占める公共の割合（地方圏・三大都市圏の中央値）。
3) 2015→2023年度の全国の割合の戻りを、公共工事の額の伸びと県内総生産の伸びに分ける。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
ar = pd.read_csv(R / "by_area.csv").set_index(["year", "area"])
nat = pd.read_csv(R / "national.csv").set_index("year")
Y = [1996, 2005, 2015, 2023]
rows = []
for y in Y:
    a, m = ar.loc[(y, "地方圏")], ar.loc[(y, "三大都市圏")]
    rows.append({"year": y, "local_median": a["median"], "metro_median": m["median"], "gap_pt": round(a["median"] - m["median"], 3),
                 "times": round(a["median"] / m["median"], 3), "local_share_total": a.share_median, "metro_share_total": m.share_median})
t = pd.DataFrame(rows)
t.to_csv(R / "requestion_relative.csv", index=False)
p15, p23 = nat.loc[2015], nat.loc[2023]
out = {"question": "差は倍率で見ても縮まったか。建設の中で公共の割合は下がったか",
       "times": {str(y): float(v) for y, v in zip(t.year, t.times)},
       "local_share_total": {str(y): round(float(v), 1) for y, v in zip(t.year, t.local_share_total)},
       "metro_share_total": {str(y): round(float(v), 1) for y, v in zip(t.year, t.metro_share_total)},
       "public_growth_2015_2023_pct": round(float(100 * (p23.public / p15.public - 1)), 1),
       "gdp_growth_2015_2023_pct": round(float(100 * (p23.gdp / p15.gdp - 1)), 1),
       "total_growth_2015_2023_pct": round(float(100 * (p23.total / p15.total - 1)), 1)}
m = json.loads((R / "main.json").read_text(encoding="utf-8"))
m["requestion"] = out
(R / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(t.to_string()); print(out)
