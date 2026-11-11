# 02 整形：F231 の予測から、在庫の判断に使う 1〜3か月先・3モデルを抜き出す
import pandas as pd
f = pd.read_csv("data/raw_f231_forecasts_main.csv.gz")
f = f[(f.h <= 3) & f.モデル.isin(["季節ナイーブ", "ETS", "SARIMA"])].copy()
f["比"] = f["実績"] / f["予測"]                     # 実績÷予測（1より大きいと足りない側に外れた）
f["コロナ期"] = f["対象月"].between("2020-03", "2021-12")
f = f.sort_values(["モデル", "業態", "h", "起点"])
f.to_csv("data/forecasts_h1to3.csv", index=False)
print(len(f), f.groupby(["モデル", "h"]).size().to_dict())
