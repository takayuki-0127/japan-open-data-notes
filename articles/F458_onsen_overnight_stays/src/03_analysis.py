"""温泉地の宿泊施設・収容定員・延べ宿泊の推移、30年の比較、1軒あたり・稼働の目安、仮説の判定、頑健性。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "onsen_trend.csv").set_index("fy")
d["cap_per_fac"] = d.capacity / d.facilities
d["util"] = d.stays / d.capacity / 365 * 100       # 収容定員1人分あたり、1年のうち何%の日に泊まりがあったかの目安
d["stays_per_fac"] = d.stays / d.facilities
d[["facilities", "capacity", "stays", "kokumin_stays", "onsen_areas", "public_baths", "cap_per_fac", "util", "stays_per_fac"]].to_csv(R / "onsen_series.csv", float_format="%.4f")
pct = lambda c, a, b: round(float((d.loc[b, c] / d.loc[a, c] - 1) * 100), 1)
avg = lambda c, ys: float(d.loc[ys, c].mean())
main = {"stays_1994": float(d.loc[1994, "stays"]), "stays_2024": float(d.loc[2024, "stays"]), "stays_2019": float(d.loc[2019, "stays"]),
        "stays_2020": float(d.loc[2020, "stays"]), "stays_pct_1994_2024": pct("stays", 1994, 2024),
        "stays_peak_fy": int(d.stays.idxmax()), "stays_peak": float(d.stays.max()),
        "fac_peak_fy": int(d.facilities.idxmax()), "fac_peak": float(d.facilities.max()), "fac_2024": float(d.loc[2024, "facilities"]),
        "fac_1994": float(d.loc[1994, "facilities"]), "fac_pct_peak_2024": round(float((d.loc[2024, "facilities"] / d.facilities.max() - 1) * 100), 1),
        "fac_min_recent_fy": int(d.loc[2000:, "facilities"].idxmin()), "fac_min_recent": float(d.loc[2000:, "facilities"].min()),
        "cap_1994": float(d.loc[1994, "capacity"]), "cap_2024": float(d.loc[2024, "capacity"]),
        "cap_per_fac_1994": round(float(d.loc[1994, "cap_per_fac"]), 1), "cap_per_fac_2024": round(float(d.loc[2024, "cap_per_fac"]), 1),
        "cap_per_fac_pct": pct("cap_per_fac", 1994, 2024),
        "util_1994": round(float(d.loc[1994, "util"]), 1), "util_2019": round(float(d.loc[2019, "util"]), 1), "util_2024": round(float(d.loc[2024, "util"]), 1),
        "areas_1994": float(d.loc[1994, "onsen_areas"]), "areas_2024": float(d.loc[2024, "onsen_areas"]), "areas_peak_fy": int(d.onsen_areas.idxmax()), "areas_peak": float(d.onsen_areas.max()),
        "baths_1994": float(d.loc[1994, "public_baths"]), "baths_2024": float(d.loc[2024, "public_baths"])}
main["hypotheses"] = {"H1": "支持" if main["stays_pct_1994_2024"] <= -10 else "外れ", "H2": "支持" if main["fac_pct_peak_2024"] <= -10 else "外れ",
                      "H3": "支持" if main["cap_per_fac_pct"] >= 10 else "外れ", "H4": "支持" if main["util_2019"] < main["util_1994"] else "外れ"}
A, B = [1992, 1993, 1994, 1995, 1996], [2022, 2023, 2024]
rb = [dict(check="1992〜96年度平均→2022〜24年度平均：延べ宿泊", value=round((avg("stays", B) / avg("stays", A) - 1) * 100, 1), unit="%"),
      dict(check="1994→2019年度（コロナ前）：延べ宿泊", value=pct("stays", 1994, 2019), unit="%"),
      dict(check=f"いちばん多かった{main['stays_peak_fy']}年度→2024年度：延べ宿泊", value=round(float((d.loc[2024, 'stays'] / d.stays.max() - 1) * 100), 1), unit="%"),
      dict(check="国民保養温泉地の延べ宿泊 1994→2024年度", value=pct("kokumin_stays", 1994, 2024), unit="%"),
      dict(check="1992〜96年度平均→2022〜24年度平均：1軒あたりの収容定員", value=round((avg("cap_per_fac", B) / avg("cap_per_fac", A) - 1) * 100, 1), unit="%"),
      dict(check="稼働の目安 1992〜96年度平均→2017〜19年度平均", value=round(avg("util", [2017, 2018, 2019]) - avg("util", A), 1), unit="ポイント")]
rbd = pd.DataFrame(rb); rbd.to_csv(R / "robustness.csv", index=False)
main["robust"] = {x.check: x.value for x in rbd.itertuples()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rbd.to_string())
