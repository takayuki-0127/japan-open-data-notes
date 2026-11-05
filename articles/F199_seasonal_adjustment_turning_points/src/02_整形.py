"""5系列の原数値（季節調整前）と公表の季節調整値を1つの表にする。完全失業率は符号を逆にして「上＝良い」にそろえる。"""
import pathlib, pandas as pd
R = pathlib.Path(__file__).resolve().parent.parent / "data"
df = pd.read_csv(R / "raw" / "f42_series.csv", parse_dates=["date"])
keep = {"鉱工業生産": "iip", "鉱工業出荷": "ship", "有効求人倍率": "jobs", "就業者": "emp", "完全失業率": "unemp"}
df = df[df.series.isin(keep)].copy()
df["key"] = df.series.map(keep)
df = df.dropna(subset=["nsa"]).sort_values(["key", "date"])
df[["date", "key", "series", "nsa", "sa_pub"]].to_csv(R / "series_nsa_sa.csv", index=False)
print(df.groupby("key").date.agg(["min", "max", "count"]))
