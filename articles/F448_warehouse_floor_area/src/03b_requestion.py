"""問い直し（結果を見てから足した）：床面積の増減を「むね数」と「1むねあたりの大きさ」に分ける。
床面積 = むね数 × 1むねあたり床面積 なので、log の差を2つに分ける（2005〜09年度 → 2021〜23年度。
むね数に小数が入る2024・2025年度は使わない）。あわせて、県別の増加（北から南の順）を出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
P0, P1 = (2005, 2009), (2021, 2023)
df = pd.read_csv(ROOT / "data" / "pref_year.csv", dtype={"code": str})
w = df[df.kind == "倉庫"]

rows = []
for g in REGIONS + ["全国"]:
    t = w if g == "全国" else w[w.region == g]
    t = t.groupby("fy", sort=True)[["n_bldg", "floor_m2"]].sum()
    a, b = t.loc[P0[0]:P0[1]].mean(), t.loc[P1[0]:P1[1]].mean()
    dl_floor = np.log(b["floor_m2"] / a["floor_m2"])
    dl_n = np.log(b["n_bldg"] / a["n_bldg"])
    dl_size = dl_floor - dl_n
    rows.append({"region": g, "floor_ratio": round(float(np.exp(dl_floor)), 3), "n_bldg_ratio": round(float(np.exp(dl_n)), 3),
                 "size_ratio": round(float(np.exp(dl_size)), 3), "logdiff_floor": round(float(dl_floor), 4),
                 "logdiff_n": round(float(dl_n), 4), "logdiff_size": round(float(dl_size), 4)})
dec = pd.DataFrame(rows)
dec.to_csv(R / "requestion_count_size.csv", index=False, encoding="utf-8")

# 県別（北から南）：2005〜09 → 2021〜25 の床面積の平均の差（万㎡）
pref = w.groupby(["code", "pref", "region", "fy"], sort=True)["floor_m2"].sum().reset_index()
pa = pref[pref.fy.between(2005, 2009)].groupby(["code", "pref", "region"], sort=True)["floor_m2"].mean()
pc = pref[pref.fy.between(2021, 2025)].groupby(["code", "pref", "region"], sort=True)["floor_m2"].mean()
pp = pd.DataFrame({"mean_2005_09_10k_m2": pa / 1e4, "mean_2021_25_10k_m2": pc / 1e4}).reset_index()
pp["change_10k_m2"] = pp["mean_2021_25_10k_m2"] - pp["mean_2005_09_10k_m2"]
pp["change_pct"] = (pp["mean_2021_25_10k_m2"] / pp["mean_2005_09_10k_m2"] - 1) * 100
pp = pp.sort_values("code")
pp.round(2).to_csv(R / "pref_change_2005_09_to_2021_25.csv", index=False, encoding="utf-8")

m = json.load(open(R / "main.json", encoding="utf-8"))
d = dec.set_index("region")
m["requestion"] = {
    "national_floor_ratio_2005_09_to_2021_23": float(d.loc["全国", "floor_ratio"]),
    "national_n_bldg_ratio": float(d.loc["全国", "n_bldg_ratio"]),
    "national_size_ratio": float(d.loc["全国", "size_ratio"]),
    "regions_n_bldg_down": int((d.loc[REGIONS, "n_bldg_ratio"] < 1).sum()),
    "regions_size_up": int((d.loc[REGIONS, "size_ratio"] > 1).sum()),
    "prefs_increased_2005_09_to_2021_25": int((pp["change_10k_m2"] > 0).sum()),
}
json.dump(m, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(dec.to_string()); print(m["requestion"])
