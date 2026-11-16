"""問い直し（結果を見てから足した）：
2013〜15年から2023〜25年に、男性の雇人のない業主は減ったが、女性は増えた。
女性の就業者が増えた分を除くため、男女それぞれの就業者に占める雇人のない業主の割合を比べる。
あわせて、男女の差（女性 − 男性の対数差）が、年をずらしても続くかを見る（始点を2010〜2018年の各3年平均にする）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
D, RES = ROOT / "data", ROOT / "results"
r3 = lambda x: round(float(x), 3)
d = pd.read_csv(D / "lfs_status.csv")
d["share"] = 100 * d.solo / d.employed
W = d.pivot(index="year", columns="sex", values="share")
W.loc[1990:].round(4).to_csv(RES / "requestion_share_by_sex.csv")
S = d.pivot(index="year", columns="sex", values="solo"); E = d.pivot(index="year", columns="sex", values="employed")
B = [2023, 2024, 2025]
out = {"share": {s: dict(y2013_15=r3(W.loc[2013:2015, s].mean()), y2023_25=r3(W.loc[B, s].mean())) for s in ["male", "female", "total"]}}
for s in out["share"]: out["share"][s]["change_pt"] = r3(out["share"][s]["y2023_25"] - out["share"][s]["y2013_15"])
out["employed_dlog_2013_15_to_2023_25"] = {s: r3(100 * np.log(E.loc[B, s].mean() / E.loc[2013:2015, s].mean())) for s in ["male", "female"]}
gap = {}
for y0 in range(2010, 2019):
    a = list(range(y0, y0 + 3))
    f = 100 * np.log(S.loc[B, "female"].mean() / S.loc[a, "female"].mean()); m = 100 * np.log(S.loc[B, "male"].mean() / S.loc[a, "male"].mean())
    gap[f"{y0}-{y0+2}"] = dict(female=r3(f), male=r3(m))
out["by_start"] = gap
T = d[d.sex == "total"].set_index("year")
sw = 100 * T.solo / (T.self_employed + T.family)
out["solo_share_within_self_family"] = dict(y2000_02=r3(sw.loc[2000:2002].mean()), y2023_25=r3(sw.loc[B].mean()))
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
