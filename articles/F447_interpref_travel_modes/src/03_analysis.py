"""距離帯×機関の県間（定期外）人数と割合、機関別の推移、コロナ後の戻り、頑健性。出力：results/"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
PUB = ["jr_nonpass", "pvt_nonpass", "bus_route", "bus_charter", "taxi", "ship", "air"]
GRP = {"rail": ["jr_nonpass", "pvt_nonpass"], "bus": ["bus_route", "bus_charter"], "air": ["air"], "ship": ["ship"], "taxi": ["taxi"]}
GNAME = {"rail": "鉄道", "bus": "バス", "air": "航空", "ship": "旅客船", "taxi": "タクシー等"}
BANDS = [0, 100, 300, 500, 700, 1000, 99999]
BLAB = ["100km未満", "100〜300km", "300〜500km", "500〜700km", "700〜1,000km", "1,000km以上"]
P0, P1 = (2000, 2002), (2017, 2019)
METRO = {"東京", "神奈川", "埼玉", "千葉"}

od = pd.read_csv(ROOT / "data" / "od_wide.csv")
dist = pd.read_csv(ROOT / "data" / "pref_distance.csv")
od = od.merge(dist, on=["orig", "dest"], how="left", validate="many_to_one")
assert od["km"].notna().all()
for g, cols in GRP.items():
    od[g] = od[cols].sum(axis=1)
od["pub"] = od[PUB].sum(axis=1)


def band(df, edges=BANDS, labels=BLAB):
    return pd.cut(df["km"], edges, right=False, labels=labels)


def shares(df, years, edges=BANDS, labels=BLAB):
    t = df[df.fy.between(*years)].copy()
    t["band"] = band(t, edges, labels)
    s = t.groupby("band", observed=False)[list(GRP) + ["pub"]].sum()
    out = s[list(GRP)].div(s["pub"], axis=0) * 100
    out["pub_thousand_per_year"] = s["pub"] / (years[1] - years[0] + 1)
    return out


def r(x, n=1):
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


# 1. 距離帯×機関の割合（初め・コロナ前・直近）
tabs = {}
for name, yrs in [("2000_02", P0), ("2017_19", P1), ("2024", (2024, 2024)), ("2019", (2019, 2019))]:
    s = shares(od, yrs); s.insert(0, "period", name); tabs[name] = s
pd.concat(tabs.values()).round(2).to_csv(R / "band_mode_share.csv", encoding="utf-8")

# 2. 機関別の県間（定期外）人数の推移（百万人）と、2019年度＝100
ts = od.groupby("fy", sort=True)[list(GRP) + ["pub", "car_private", "bus_private"]].sum() / 1e3
ts.round(3).to_csv(R / "national_by_mode_million.csv", encoding="utf-8")
idx = (ts[list(GRP) + ["pub"]] / ts.loc[2019, list(GRP) + ["pub"]] * 100)
idx.round(2).to_csv(R / "index_2019_100.csv", encoding="utf-8")

# 3. 2024年度の2019年度比（距離帯×機関）
t = od[od.fy.isin([2019, 2024])].copy(); t["band"] = band(t)
s = t.groupby(["fy", "band"], observed=False)[list(GRP) + ["pub"]].sum()
rec = (s.loc[2024] / s.loc[2019] * 100).replace([np.inf, -np.inf], np.nan)
rec.round(2).to_csv(R / "recovery_2024_vs_2019_by_band.csv", encoding="utf-8")

# 4. 自家用乗用車を入れた分担（2000〜02年度、2009年度）
car = {}
for name, yrs in [("2000_02", P0), ("2007_09", (2007, 2009))]:
    tt = od[od.fy.between(*yrs)].copy(); tt["band"] = band(tt)
    ss = tt.groupby("band", observed=False)[list(GRP) + ["car_private", "bus_private"]].sum()
    tot = ss.sum(axis=1)
    sh = ss.div(tot, axis=0) * 100
    sh.insert(0, "period", name); car[name] = sh
    car[name + "_under300"] = float(ss.iloc[:2]["car_private"].sum() / tot.iloc[:2].sum() * 100)
    car[name + "_all"] = float(ss["car_private"].sum() / tot.sum() * 100)
pd.concat([car["2000_02"], car["2007_09"]]).round(2).to_csv(R / "band_mode_share_with_private_car.csv", encoding="utf-8")

a, b = tabs["2000_02"], tabs["2017_19"]
mid = (lambda T: float((T.loc[["300〜500km", "500〜700km"], "rail"] * T.loc[["300〜500km", "500〜700km"], "pub_thousand_per_year"]).sum()
                       / T.loc[["300〜500km", "500〜700km"], "pub_thousand_per_year"].sum()))


def wavg(T, bands, col):
    w = T.loc[bands, "pub_thousand_per_year"]
    return float((T.loc[bands, col] * w).sum() / w.sum())


LONG = ["700〜1,000km", "1,000km以上"]; MID = ["300〜500km", "500〜700km"]; SHORT = ["100km未満", "100〜300km"]
rec_mode = ts.loc[2024, list(GRP) + ["pub"]] / ts.loc[2019, list(GRP) + ["pub"]] * 100
rec_mode23 = ts.loc[2023, list(GRP) + ["pub"]] / ts.loc[2019, list(GRP) + ["pub"]] * 100

# 頑健性
rob = []
def add(check, h, val, note=""):
    rob.append({"check": check, "hypothesis": h, "value": round(float(val), 2), "note": note})

add("基本：300〜700km 鉄道の割合 2017〜19（%）", "H1", wavg(b, MID, "rail"))
add("基本：700km以上 航空の割合 2017〜19（%）", "H1", wavg(b, LONG, "air"))
add("基本：700km以上 鉄道の割合 2000〜02→2017〜19（ポイント）", "H3", wavg(b, LONG, "rail") - wavg(a, LONG, "rail"))
add("基本：2024/2019 航空−鉄道（ポイント）", "H4", rec_mode["air"] - rec_mode["rail"])
for f in (0.8, 1.2):
    e = [0, 100 * f, 300 * f, 500 * f, 700 * f, 1000 * f, 99999]
    bb, aa = shares(od, P1, e), shares(od, P0, e)
    add(f"距離の区切り×{f}：300〜700km 鉄道（%）", "H1", wavg(bb, MID, "rail"))
    add(f"距離の区切り×{f}：700km以上 航空（%）", "H1", wavg(bb, LONG, "air"))
    add(f"距離の区切り×{f}：700km以上 鉄道の変化（ポイント）", "H3", wavg(bb, LONG, "rail") - wavg(aa, LONG, "rail"))
sub = od[~od.orig.isin(["北海道", "沖縄"]) & ~od.dest.isin(["北海道", "沖縄"])]
bb, aa = shares(sub, P1), shares(sub, P0)
add("北海道・沖縄の発着を除く：300〜700km 鉄道（%）", "H1", wavg(bb, MID, "rail"))
add("北海道・沖縄の発着を除く：700km以上 航空（%）", "H1", wavg(bb, LONG, "air"))
add("北海道・沖縄の発着を除く：700km以上 鉄道の変化（ポイント）", "H3", wavg(bb, LONG, "rail") - wavg(aa, LONG, "rail"))
sub2 = od[~(od.orig.isin(METRO) & od.dest.isin(METRO))]
ts2 = sub2.groupby("fy")[list(GRP)].sum()
add("東京圏の1都3県の間を除く：2024/2019 航空−鉄道（ポイント）", "H4",
    (ts2.loc[2024, "air"] / ts2.loc[2019, "air"] - ts2.loc[2024, "rail"] / ts2.loc[2019, "rail"]) * 100)
add("2023年度で：2023/2019 航空−鉄道（ポイント）", "H4", rec_mode23["air"] - rec_mode23["rail"])
add("H2 基本：300km未満 自家用乗用車の割合 2000〜02（%）", "H2", car["2000_02_under300"])
add("H2 確かめ：300km未満 自家用乗用車の割合 2007〜09（%）", "H2", car["2007_09_under300"])
# 500〜700km の鉄道の割合の上がり方：2000〜01年度のタクシー等に、遠い県の間の大きな値（例：広島〜東京）があるため、
# タクシー等を分母から除く確かめと、起点を2003〜05年度にする確かめ（レビューで足した）
def rail_500_700(years, drop_taxi):
    t = od[od.fy.between(*years) & (od.km >= 500) & (od.km < 700)]
    den = t["pub"].sum() - (t["taxi"].sum() if drop_taxi else 0)
    return float(t["rail"].sum() / den * 100)
r57 = {"base_2000_02": rail_500_700(P0, False), "base_2017_19": rail_500_700(P1, False),
       "notaxi_2000_02": rail_500_700(P0, True), "notaxi_2017_19": rail_500_700(P1, True),
       "base_2003_05": rail_500_700((2003, 2005), False)}
add("500〜700km 鉄道の割合の変化 2000〜02→2017〜19（ポイント）", "参考", r57["base_2017_19"] - r57["base_2000_02"])
add("タクシー等を除いて：500〜700km 鉄道の割合の変化 2000〜02→2017〜19（ポイント）", "参考", r57["notaxi_2017_19"] - r57["notaxi_2000_02"])
add("起点を2003〜05年度に：500〜700km 鉄道の割合の変化（ポイント）", "参考", r57["base_2017_19"] - r57["base_2003_05"])
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False, encoding="utf-8")

main = {
    "pub_interpref_million": {str(y): r(ts.loc[y, "pub"]) for y in (2000, 2009, 2019, 2020, 2021, 2023, 2024)},
    "rail_million": {str(y): r(ts.loc[y, "rail"]) for y in (2000, 2019, 2020, 2024)},
    "air_million": {str(y): r(ts.loc[y, "air"]) for y in (2000, 2019, 2020, 2024)},
    "bus_million": {str(y): r(ts.loc[y, "bus"]) for y in (2000, 2019, 2020, 2024)},
    "car_private_million": {str(y): r(ts.loc[y, "car_private"]) for y in (2000, 2009)},
    "share_rail_all_pub": {"2000_02": r(ts.loc[2000:2002, "rail"].sum() / ts.loc[2000:2002, "pub"].sum() * 100),
                           "2017_19": r(ts.loc[2017:2019, "rail"].sum() / ts.loc[2017:2019, "pub"].sum() * 100),
                           "2024": r(ts.loc[2024, "rail"] / ts.loc[2024, "pub"] * 100)},
    "H1": {"mid_rail_2017_19": r(wavg(b, MID, "rail")), "long_air_2017_19": r(wavg(b, LONG, "air")),
           "short_rail_2017_19": r(wavg(b, SHORT, "rail"))},
    "H2": {"under300_private_car_2000_02": r(car["2000_02_under300"]), "all_private_car_2000_02": r(car["2000_02_all"]),
           "under300_private_car_2007_09": r(car["2007_09_under300"])},
    "H3": {"long_rail_2000_02": r(wavg(a, LONG, "rail")), "long_rail_2017_19": r(wavg(b, LONG, "rail")),
           "long_air_2000_02": r(wavg(a, LONG, "air")),
           "mid_rail_2000_02": r(wavg(a, MID, "rail"))},
    "H4": {"rec_2024_vs_2019": {GNAME.get(k, "公共計"): r(v) for k, v in rec_mode.items()},
           "rec_2023_vs_2019": {GNAME.get(k, "公共計"): r(v) for k, v in rec_mode23.items()},
           "air_minus_rail_2024": r(rec_mode["air"] - rec_mode["rail"])},
    "band_share_2017_19": {k: {GNAME[g]: r(v) for g, v in row.items() if g in GRP} for k, row in b.iterrows()},
    "band_share_2000_02": {k: {GNAME[g]: r(v) for g, v in row.items() if g in GRP} for k, row in a.iterrows()},
    "band_share_2024": {k: {GNAME[g]: r(v) for g, v in row.items() if g in GRP} for k, row in tabs["2024"].iterrows()},
    "band_volume_2017_19_million_per_year": {k: r(v / 1e3, 2) for k, v in b["pub_thousand_per_year"].items()},
    "recovery_2024_by_band": {k: {GNAME.get(g, "公共計"): r(v) for g, v in row.items()} for k, row in rec.iterrows()},
    "rail_500_700_check": {k: r(v) for k, v in r57.items()},
    "n_pairs": int(len(dist)),
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(pd.DataFrame(rob).to_string())
