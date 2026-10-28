"""グループを付ける：圏域（4）・地方ブロック（8）・市区町村の人口密度（5分位）・用途（4）・価格帯（5分位）
電力は日の種類（平日・土曜・日曜祝日・連休）と気温（5分位）・季節"""
import numpy as np, pandas as pd
from common import RAW, DATA, KEN, block, DENS
d = pd.read_csv(RAW / "F03_features.csv", dtype={"code": str, "muni": str, "pref": str})
d["ken"] = d["pref"].map(KEN).fillna("地方圏")
d["blk"] = d["pref"].map(block)
d["dens"] = pd.qcut(d["log_muni_density"].rank(method="first"), 5, labels=DENS).astype(str)
d["use"] = d["land_use_class"].where(d["land_use_class"].isin(["住宅地", "商業地", "工業地"]), "その他")
d.to_csv(RAW / "land_groups.csv", index=False)
d[["code", "pref", "ken", "blk", "dens", "use"]].to_csv(DATA / "land_groups_small.csv", index=False)
print(d.groupby("ken").size(), d.groupby("blk").size(), d.groupby("use").size(), sep="\n")

p = pd.read_csv(RAW / "F92_pred_tokyo.csv", parse_dates=["date"])
t = pd.read_csv(RAW / "F92_tokyo.csv", parse_dates=["date"])
p = p.merge(t[["date", "temp_mean", "dow", "holiday", "offday", "obon", "nenmatsu", "gw"]], on="date", how="left")
def daytype(r):
    if r.obon or r.nenmatsu or r.gw: return "連休（盆・年末年始・GW）"
    if r.holiday or r.dow == 6: return "日曜・祝日"
    if r.dow == 5: return "土曜"
    return "平日"
p["daytype"] = p.apply(daytype, axis=1)
p["tempq"] = pd.qcut(p["temp_mean"], 5, labels=["気温1（寒い）", "気温2", "気温3", "気温4", "気温5（暑い）"]).astype(str)
p[["date", "actual", "point", "fold", "season", "temp_mean", "daytype", "tempq"]].to_csv(DATA / "power_daily.csv", index=False)
print(p.daytype.value_counts(), p.fold.value_counts().sort_index(), sep="\n")
