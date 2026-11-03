"""02 整形：輸出（国×年×品目）、GDP、距離、EPA をまとめて data/panel.csv を作る。"""
import os, json, math
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data")

# --- 輸出（UN Comtrade に日本が報告した値＝財務省貿易統計の米ドル換算） ---
ct = json.load(open(os.path.join(RAW, "comtrade_jpn_exports.json"), encoding="utf-8"))
P = pd.DataFrame(ct["P"], columns=["partnerCode", "iso3", "name"])
rows = []
for key, recs in ct["D"].items():
    y, c = key.split("_")
    for pc, v in recs:
        rows.append((int(y), c, int(pc), float(v)))
X = pd.DataFrame(rows, columns=["year", "cmd", "partnerCode", "exports_usd"])
X = X.merge(P, on="partnerCode", how="left")
# 490 = "Other Asia, nes"（実質的に台湾）
X.loc[X.partnerCode == 490, "iso3"] = "TWN"
X = X[X.partnerCode != 0]
world = pd.DataFrame([(int(k.split("_")[0]), k.split("_")[1], sum(v for pc, v in recs if pc == 0))
                      for k, recs in ct["D"].items()], columns=["year", "cmd", "world_usd"])
world.to_csv(os.path.join(OUT, "world_total.csv"), index=False)

# --- GDP（IMF WEO、名目・十億米ドル）と WB ---
imf = json.load(open(os.path.join(RAW, "imf_weo_ngdpd.json"), encoding="utf-8"))["values"]["NGDPD"]
g = [(k, int(y), v) for k, d in imf.items() if len(k) == 3 for y, v in d.items() if 2000 <= int(y) <= 2024 and v is not None]
GDP = pd.DataFrame(g, columns=["iso3", "year", "gdp_imf_bn"])
wb = json.load(open(os.path.join(RAW, "wb_gdp_pop_capital.json"), encoding="utf-8"))
wbg = pd.DataFrame(wb["NY.GDP.MKTP.CD"], columns=["iso3", "year", "gdp_wb"]).dropna()
wbg["year"] = wbg.year.astype(int); wbg["gdp_wb_bn"] = wbg.gdp_wb / 1e9
pop = pd.DataFrame(wb["SP.POP.TOTL"], columns=["iso3", "year", "pop"]).dropna(); pop["year"] = pop.year.astype(int)
cty = pd.DataFrame(wb["countries"], columns=["iso3", "iso2", "wb_name", "region", "income", "capital", "lat", "lon"])
cty = cty[cty.region.str.strip() != "Aggregates"].copy()
cty["lat"] = pd.to_numeric(cty.lat, errors="coerce"); cty["lon"] = pd.to_numeric(cty.lon, errors="coerce")
# 世界銀行の一覧にない台湾（台北）を追加
cty = pd.concat([cty, pd.DataFrame([{"iso3": "TWN", "iso2": "TW", "wb_name": "Taiwan", "region": "East Asia & Pacific",
                                      "income": "High income", "capital": "Taipei", "lat": 25.03, "lon": 121.56}])])
cty["region"] = cty.region.str.strip()

def gc(lat, lon, lat0=35.6895, lon0=139.6917):
    p1, p2 = math.radians(lat0), math.radians(lat)
    dl = math.radians(lon - lon0)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))
cty["dist_km"] = [gc(a, b) if pd.notna(a) else np.nan for a, b in zip(cty.lat, cty.lon)]
LANDLOCKED = set("AFG AND ARM AUT AZE BDI BFA BLR BOL BTN BWA CAF CHE CZE ETH HUN KAZ KGZ LAO LIE LSO LUX MDA MKD MLI MNG MWI NER NPL PRY RWA SMR SRB SSD SVK SWZ TCD TJK TKM UGA UZB VAT XKX ZMB ZWE".split())
cty["landlocked"] = cty.iso3.isin(LANDLOCKED).astype(int)

# --- EPA（発効年。7月以降の発効は翌年から1とする）外務省の EPA/FTA 一覧から作成者が整理 ---
EU27 = "AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP SWE".split()
EPA = {"SGP": 2003, "MEX": 2005, "MYS": 2007, "CHL": 2008, "THA": 2008, "IDN": 2009, "BRN": 2009, "PHL": 2009,
       "LAO": 2009, "MMR": 2009, "VNM": 2009, "KHM": 2010, "CHE": 2010, "IND": 2012, "PER": 2012, "AUS": 2015,
       "MNG": 2016, "CAN": 2019, "NZL": 2019, "GBR": 2019, "USA": 2020, "CHN": 2022, "KOR": 2022}
for e in EU27: EPA[e] = 2019

# --- 結合：GDP がある国 × 年の格子（輸出がない組はゼロ） ---
keep = set(cty.iso3) & set(GDP.iso3) - {"JPN"}
grid = GDP[GDP.iso3.isin(keep)][["iso3", "year", "gdp_imf_bn"]]
cmds = sorted(X.cmd.unique())
pan = []
for c in cmds:
    xc = X[(X.cmd == c) & X.iso3.isin(keep)].groupby(["iso3", "year"], as_index=False).exports_usd.sum()
    years = sorted(X[X.cmd == c].year.unique())
    gg = grid[grid.year.isin(years)].merge(xc, on=["iso3", "year"], how="left")
    gg["exports_usd"] = gg.exports_usd.fillna(0.0); gg["cmd"] = c
    pan.append(gg)
pan = pd.concat(pan)
pan = pan.merge(wbg[["iso3", "year", "gdp_wb_bn"]], on=["iso3", "year"], how="left")
pan = pan.merge(pop, on=["iso3", "year"], how="left")
pan = pan.merge(cty[["iso3", "wb_name", "region", "income", "dist_km", "landlocked"]], on="iso3", how="left")
pan["epa"] = [int(y >= EPA.get(i, 9999)) for i, y in zip(pan.iso3, pan.year)]
pan = pan[pan.gdp_imf_bn > 0]
pan.to_csv(os.path.join(OUT, "panel.csv"), index=False)
cov = pan[pan.cmd == "TOTAL"].groupby("year").exports_usd.sum().rename("covered")
w = world[world.cmd == "TOTAL"].set_index("year").world_usd
print(pd.concat([cov, w, cov / w], axis=1).round(3))
print(pan.groupby("cmd").size(), pan.iso3.nunique())
