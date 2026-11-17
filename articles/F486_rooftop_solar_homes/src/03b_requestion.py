"""問い直し（結果を見てから足した）：2018→2023年に増えた「太陽光のある住宅」のうち、2019年以降に建った住宅の分はどれくらいか。
（2023年の調査で、建築の時期が2019年〜2023年9月の住宅のうち太陽光のある住宅数 ÷ 2018→2023年の増加数）"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
jk = pd.read_csv(ROOT / "data" / "jiki.csv")
ts = pd.read_csv(ROOT / "data" / "timeseries.csv")
new = ["2019年", "2020年", "2021年", "2022年", "2023年1月～9月"]
out = {}
for ten in ["総数", "持ち家", "借家"]:
    j = jk[jk.tenure == ten].set_index("period")
    n_new = float(j.loc[new, "solar_yes"].sum())
    t = ts[(ts.area == "全国") & (ts.tenure == ten)].set_index("year")
    inc = float(t.solar_yes.loc[2023] - t.solar_yes.loc[2018])
    out[ten] = {"solar_in_built_2019_2023": n_new, "increase_2018_2023": inc, "share_of_increase_pct": round(n_new / inc * 100, 1),
                "built_2019_2023_total": float(j.loc[new, "total"].sum()),
                "share_among_built_2019_2023_pct": round(n_new / float(j.loc[new, "total"].sum()) * 100, 2),
                "existing_net_change": inc - n_new}
# 前の期間（2013→2018年）も同じ見方で：2013年の調査にない、2014〜2018年9月に建った住宅は2023年の表の「2016～2018年」と「2011～2015年」の一部で、きれいに分けられないので扱わない
pd.DataFrame(out).T.to_csv(R / "requestion_new_builds.csv")
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
