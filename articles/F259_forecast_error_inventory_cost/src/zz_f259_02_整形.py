# F259 02 整形：架空の小売チェーン「あおばストア（架空）」の需要に見立てる。
# 業態ごとに 2017〜2019年の月平均＝100 に換算（実績・予測とも同じ倍率）。
import pandas as pd
s = pd.read_csv("data/sales_monthly_6types.csv")
f = pd.read_csv("data/f231_forecasts_main.csv.gz")
base = s[(s.ym >= "2017-01") & (s.ym <= "2019-12")].groupby("業態")["販売額_百万円"].mean().rename("基準")
s = s.merge(base, on="業態"); s["需要"] = s["販売額_百万円"] / s["基準"] * 100
f = f.merge(base, on="業態"); f["実績"] = f["実績"] / f["基準"] * 100; f["予測"] = f["予測"] / f["基準"] * 100
s[["ym", "業態", "需要"]].round(6).to_csv("data/demand_scaled.csv", index=False)
f[["業態", "モデル", "起点", "対象月", "h", "実績", "予測"]].round(6).to_csv("data/forecasts_scaled.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
print(base.round(0).to_dict()); print(len(s), len(f))
