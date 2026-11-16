"""問い直し：8月の割合が下がったのは、8月が減ったからか、ほかの月が増えたからか。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "japanese_stays_monthly.csv")
n = d[d.code == 0]
EARLY, LATE = [2012, 2013, 2014], [2023, 2024, 2025]
m = pd.DataFrame({"2012-14": n[n.year.isin(EARLY)].groupby("month").stays.mean(), "2023-25": n[n.year.isin(LATE)].groupby("month").stays.mean()})
m["ratio"] = m["2023-25"] / m["2012-14"]
m.round(3).to_csv(R / "requestion_month_levels.csv")
aug_e, aug_l = m.loc[8, "2012-14"], m.loc[8, "2023-25"]
oth_e, oth_l = m.drop(8)["2012-14"].sum(), m.drop(8)["2023-25"].sum()
# 8月の割合の変化を、「8月だけが変わった場合」と「ほかの月だけが変わった場合」に分ける（2つの順の平均）
s = lambda a, o: a / (a + o) * 100
d_aug = ((s(aug_l, oth_e) - s(aug_e, oth_e)) + (s(aug_l, oth_l) - s(aug_e, oth_l))) / 2
d_oth = ((s(aug_e, oth_l) - s(aug_e, oth_e)) + (s(aug_l, oth_l) - s(aug_l, oth_e))) / 2
out = {"question": "8月の割合が下がったのは、8月が減ったからか、ほかの月が増えたからか",
       "aug_2012_14_million": round(aug_e / 1e6, 2), "aug_2023_25_million": round(aug_l / 1e6, 2), "aug_ratio": round(aug_l / aug_e, 3),
       "others_2012_14_million": round(oth_e / 1e6, 2), "others_2023_25_million": round(oth_l / 1e6, 2), "others_ratio": round(oth_l / oth_e, 3),
       "share_change_pt": round(s(aug_l, oth_l) - s(aug_e, oth_e), 3), "part_august_pt": round(d_aug, 3), "part_others_pt": round(d_oth, 3),
       "month_ratio": {int(k): round(float(v), 3) for k, v in m.ratio.items()}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print("requestion ok")
