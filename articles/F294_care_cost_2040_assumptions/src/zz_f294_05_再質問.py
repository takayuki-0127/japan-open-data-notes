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

# レビュー後に追加：総合事業の受給者を足し戻す確認（各年11月審査分、月の受給者数、千人）
# 総合事業サービス受給者数は同じ統計の別表（kyufu19 統計表４、kyufu25 統計表５）。2014年度は総合事業の開始前。
# 注意: 総合事業には要介護認定を受けていない「事業対象者」も入り、介護予防と総合事業の両方を使う人は二重に数える。
RAW = ROOT / "data" / "raw"
def nov_total(f, sh):
    d = pd.read_excel(RAW / f, sheet_name=sh, header=None)
    for i in range(6):
        cols = [j for j, c in enumerate(d.iloc[i].astype(str)) if c.strip() == "11月"]
        if cols:
            j = cols[0]
            for k in range(i + 1, i + 4):
                if "総" in "".join(d.iloc[k, :3].astype(str)):
                    return float(d.iloc[k, j])
    raise ValueError(f + sh)
t3 = pd.read_excel(RAW / "kyufu14_09.xls", sheet_name="表３", header=None)
assert str(t3.iloc[3, 7]).strip() == "11月" and "介護予防サービス総数" in str(t3.iloc[4, 0])
ab = pd.DataFrame([
    {"年": 2014, "介護予防": float(t3.iloc[4, 7]), "総合事業": 0.0},
    {"年": 2019, "介護予防": nov_total("kyufu19_09.xlsx", "統計表１"), "総合事業": nov_total("kyufu19_09.xlsx", "統計表４")},
    {"年": 2025, "介護予防": nov_total("kyufu25_09.xlsx", "統計表１"), "総合事業": nov_total("kyufu25_09.xlsx", "統計表５")},
])
ab["合計（重複あり）"] = ab["介護予防"] + ab["総合事業"]
ab.to_csv(R / "reask_addback_sogo.csv", index=False, float_format="%.1f")
print(ab.to_string())
