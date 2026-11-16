"""遠洋漁業とカツオ・マグロの遠洋3漁法の縮み方。仮説・頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
b = pd.read_csv(ROOT / "data" / "bumon.csv").set_index("year")
s = pd.read_csv(ROOT / "data" / "shurui.csv").set_index("year")
g = pd.read_csv(ROOT / "data" / "gyoshu.csv").set_index("year")
b["distant_share_pct"] = b.distant / b.marine_fishing * 100
s["tuna3_distant"] = s.longline_distant + s.polepole_distant + s.seine_distant
s["tuna3_offshore"] = s.longline_offshore + s.polepole_offshore + s.seine_offshore
b.round(4).to_csv(R / "bumon_series.csv"); s.round(4).to_csv(R / "shurui_series.csv")


def peak(x):
    x = x.dropna()
    return int(x.idxmax()), float(x.max())


py, pv = peak(b.distant)
h1 = float(b.distant.loc[2024] / pv * 100)
ly, lv = peak(s.longline_distant)
h3 = float(s.longline_distant.loc[2024] / lv * 100)
seine24 = float(s.seine_distant.loc[2024]); lp24 = float(s.longline_distant.loc[2024] + s.polepole_distant.loc[2024])
h4 = float(b.distant_share_pct.loc[2024])

rows = []
for col, name in [("longline_distant", "遠洋まぐろはえ縄"), ("polepole_distant", "遠洋かつお一本釣"), ("seine_distant", "遠洋かつお・まぐろまき網"),
                  ("tuna3_distant", "遠洋の3漁法 計"), ("longline_offshore", "近海まぐろはえ縄"), ("polepole_offshore", "近海かつお一本釣"),
                  ("seine_offshore", "近海かつお・まぐろまき網"), ("tuna3_offshore", "近海の3漁法 計")]:
    y, v = peak(s[col])
    last = int(s[col].dropna().index.max())  # 近海のまき網は2019年以降が秘匿などで空欄
    rows.append({"gear": name, "peak_year": y, "peak_kt": round(v, 1), "kt_2000": round(float(s[col].loc[2000]), 1),
                 "last_year": last, "kt_last": round(float(s[col].loc[last]), 1), "pct_of_peak_last": round(float(s[col].loc[last] / v * 100), 1),
                 "pct_of_peak_3yr": round(float(s[col].loc[last - 2:last].mean() / v * 100), 1),
                 "change_2000_last_pct": round(float((s[col].loc[last] / s[col].loc[2000] - 1) * 100), 1)})
gear = pd.DataFrame(rows)
gear.to_csv(R / "gears.csv", index=False)
mix = s[["longline_distant", "polepole_distant", "seine_distant"]].div(s.tuna3_distant, axis=0) * 100
mix.round(2).to_csv(R / "distant_tuna_mix.csv")

rob = pd.DataFrame([
    {"check": "本線：単年2024年", "distant_pct_of_peak": round(h1, 1), "longline_pct_of_peak": round(h3, 1),
     "seine_vs_longline_polepole": round(seine24 / lp24, 2), "distant_share_pct": round(h4, 1)},
    {"check": "3年平均（2022〜2024年）", "distant_pct_of_peak": round(float(b.distant.loc[2022:2024].mean() / pv * 100), 1),
     "longline_pct_of_peak": round(float(s.longline_distant.loc[2022:2024].mean() / lv * 100), 1),
     "seine_vs_longline_polepole": round(float(s.seine_distant.loc[2022:2024].mean() / (s.longline_distant + s.polepole_distant).loc[2022:2024].mean()), 2),
     "distant_share_pct": round(float(b.distant.loc[2022:2024].sum() / b.marine_fishing.loc[2022:2024].sum() * 100), 1)},
    {"check": "比べる年を2018年に（近海のまき網が分かる最後の年）", "distant_pct_of_peak": round(float(b.distant.loc[2018] / pv * 100), 1),
     "longline_pct_of_peak": round(float(s.longline_distant.loc[2018] / lv * 100), 1),
     "seine_vs_longline_polepole": round(float(s.seine_distant.loc[2018] / (s.longline_distant + s.polepole_distant).loc[2018]), 2),
     "distant_share_pct": round(float(b.distant_share_pct.loc[2018]), 1)},
])
rob.to_csv(R / "robustness.csv", index=False)
# 魚種別との照合（まぐろ類・かつお）
chk = pd.DataFrame({"tuna_total": g.tuna_total, "skipjack": g.skipjack, "tuna3_all": s.tuna3_distant + s.tuna3_offshore})
chk.round(3).to_csv(R / "check_species.csv")
cc = chk.loc[1975:2018].dropna()
corr = float(np.corrcoef(np.log(cc.tuna_total + cc.skipjack), np.log(cc.tuna3_all))[0, 1])

main = {
    "distant_peak_year": py, "distant_peak_kt": round(pv, 1), "distant_2000_kt": round(float(b.distant.loc[2000]), 1),
    "distant_2024_kt": round(float(b.distant.loc[2024]), 1), "distant_pct_of_peak": round(h1, 1),
    "distant_share_1979": round(float(b.distant_share_pct.loc[1979]), 1), "distant_share_2024": round(h4, 1),
    "marine_fishing_1979": round(float(b.marine_fishing.loc[1979]), 1), "marine_fishing_2024": round(float(b.marine_fishing.loc[2024]), 1),
    "offshore_2024": round(float(b.offshore.loc[2024]), 1), "coastal_2024": round(float(b.coastal.loc[2024]), 1),
    "longline_peak_year": ly, "longline_peak_kt": round(lv, 1), "longline_2024_kt": round(float(s.longline_distant.loc[2024]), 1),
    "longline_pct_of_peak": round(h3, 1),
    "polepole_distant_2024": round(float(s.polepole_distant.loc[2024]), 1), "seine_distant_2024": round(seine24, 1),
    "tuna3_distant_2024": round(float(s.tuna3_distant.loc[2024]), 1),
    "mix_2024": {k: round(float(v), 1) for k, v in mix.loc[2024].items()}, "mix_1990": {k: round(float(v), 1) for k, v in mix.loc[1990].items()}, "mix_2000": {k: round(float(v), 1) for k, v in mix.loc[2000].items()},
    "corr_species_vs_gears_log": round(corr, 3),
    "hypotheses": {
        "H1_distant_le_15pct_of_peak": {"value": round(h1, 1), "result": "支持" if h1 <= 15 else "外れ"},
        "H2_seine_gt_longline_plus_polepole": {"seine": round(seine24, 1), "longline_polepole": round(lp24, 1), "result": "支持" if seine24 > lp24 else "外れ"},
        "H3_longline_le_30pct_of_peak": {"value": round(h3, 1), "result": "支持" if h3 <= 30 else "外れ"},
        "H4_distant_share_lt_15": {"value": round(h4, 1), "result": "支持" if h4 < 15 else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(gear.to_string()); print(rob.to_string())
