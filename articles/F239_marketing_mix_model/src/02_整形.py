# 02_整形：広告業の売上高（特定サービス産業動態統計）と小売6業態の販売額（商業動態統計）を月次でそろえる
import pandas as pd
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "data"
ad = pd.read_csv(D / "raw" / "ad_industry_monthly_1988_2024.csv", na_values=["…", "-", "―"])
ad["ym"] = ad["code"].astype(str).str[:4] + "-" + ad["code"].astype(str).str[-2:]
cols = ["total", "mass4", "tv", "newspaper", "internet", "flyer_dm", "sp_pr_event"]
ad = ad[["ym"] + cols].copy()
ad.to_csv(D / "ad_monthly_1988_2024.csv", index=False)

r = pd.read_csv(D / "raw" / "retail_6types_monthly.csv")
r = r[r["品目"] == "合計"].pivot(index="ym", columns="業態", values="販売額_百万円")
r = r[["スーパー", "コンビニ", "百貨店"]]  # 2014年1月からそろう3業態
r["小売3業態計"] = r.sum(axis=1)
m = ad.set_index("ym").join(r, how="inner").loc["2014-01":"2024-12"]
m.to_csv(D / "panel_2014_2024.csv")
print(m.shape, m.index.min(), m.index.max())
