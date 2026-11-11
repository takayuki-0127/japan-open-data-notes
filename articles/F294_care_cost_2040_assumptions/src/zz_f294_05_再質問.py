"""F294 再質問（事後・計画外）: 2014→2019 の受給率の下がりは、介護予防サービス（要支援）の側に偏っているか？
2015〜2017年度に介護予防の訪問介護・通所介護が総合事業（この統計の外）へ移った。
年間実受給者数を「介護予防」と「介護」に分け、人口構成だけの伸び（65歳以上・11月審査分から計算）と比べる。
注意: 年間実受給者は40〜64歳を含み、両方を使った人は両方に数えられる。人口構成の伸びは65歳以上だけの近似。
"""
import json, math, pathlib
import pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, R = ROOT / "data" / "processed", ROOT / "results"
ser = pd.read_csv(P / "annual_series.csv").set_index("fy")
summ = json.loads((R / "summary.json").read_text(encoding="utf-8"))
demo = {b["期間"]: b["人口構成(受給率一定)"] for b in summ["バックテスト"]}
out = []
for y0, y1 in [(2014, 2019), (2019, 2025), (2014, 2025)]:
    k = f"{y0}→{y1}"
    d = demo[k]
    all_ = ser.users_all_k[y1] / ser.users_all_k[y0]
    kai = ser.users_kaigo_k[y1] / ser.users_kaigo_k[y0]
    yob = ser.users_yobo_k[y1] / ser.users_yobo_k[y0]
    out.append({"期間": k, "人口構成だけ": d, "全体の倍率": all_, "介護の倍率": kai, "介護予防の倍率": yob,
                "全体の受給率効果": all_ / d, "介護だけの受給率効果": kai / d,
                "受給率の下がりのうち介護だけで説明できない割合": 1 - math.log(kai / d) / math.log(all_ / d) if all_ / d < 1 else float("nan"),
                "介護予防の費用の倍率": ser.cost_yobo_m[y1] / ser.cost_yobo_m[y0],
                "介護の費用の倍率": ser.cost_kaigo_m[y1] / ser.cost_kaigo_m[y0]})
df = pd.DataFrame(out)
df.to_csv(R / "reask_yobo_kaigo.csv", index=False, float_format="%.4f")
print(df.T.to_string())
