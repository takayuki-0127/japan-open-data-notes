"""GDP 速報の各公表回（F50 で集めた CSV）から、GDP と需要項目の実質前期比を取り出し、
公表回 × 対象四半期 の表（ビンテージ表）を項目ごとに作る"""
import json
import pandas as pd
from common import ROOT, RAW, DATA, release_id, release_info, parse_series

# GDP 速報の生データは F50 のフォルダのものを使う（同じリポジトリの articles/F50_gdp_revisions/data/raw/）
F50RAW = ROOT.parent / "F50_gdp_revisions" / "data" / "raw"
SRC = RAW if (RAW / "f50_qe_releases.json").exists() else F50RAW

# 列の見つけ方（英語の見出しを空白を除いて照らし合わせる）
ITEMS = {
    "GDP": r"国内総(生産|支出)|GDE|GDP",
    "民間消費": r"^PrivateConsumption$",
    "住宅投資": r"Residential",
    "設備投資": r"Non-?Resi",
    "政府消費": r"^GovernmentConsumption$",
    "公共投資": r"^PublicInvestment$",
    "輸出": r"^Exports$",
    "輸入": r"^Imports$",
}

d = json.load(open(SRC / "f50_qe_releases.json", encoding="utf-8"))
extra = json.load(open(SRC / "f50_qe_extra.json", encoding="utf-8"))
got = {e["menu"] for e in extra}
d = [r for r in d if r["menu"] not in got] + extra
info, tabs = [], {k: {} for k in ITEMS}
for r in d:
    rid = release_id(r["menu"])
    if rid is None or not r.get("jk"):
        continue
    info.append(release_info(rid))
    for k, pat in ITEMS.items():
        try:
            tabs[k][rid] = parse_series(r["jk"], pat)
        except Exception as e:
            print("skip", rid, k, e)
info = pd.DataFrame(info)
fixed = {x[:-1] for x in info.rid if x.endswith("r")}
info = info[~info.rid.isin(fixed)].copy()
info["order"] = info["ref"].astype(str) + info["stage"].astype(str) + info["reissue"].astype(int).astype(str)
info = info.sort_values("order").reset_index(drop=True)
info["ref"] = info["ref"].astype(str)
info.to_csv(DATA / "gdp_releases.csv", index=False)
out = []
for k, dd in tabs.items():
    for x in fixed:
        dd.pop(x, None)
    v = pd.DataFrame(dd).T
    v.columns = v.columns.astype(str)
    v = v.reindex([x for x in info.rid if x in v.index])
    v = v.stack().rename("value").reset_index()
    v.columns = ["rid", "q", "value"]
    v["item"] = k
    out.append(v)
    print(k, v.rid.nunique(), "回")
pd.concat(out).to_csv(DATA / "gdp_vintages_long.csv.gz", index=False)
