"""02 整形：市区町村 × 年の小売事業所数と人口のパネルを作る。

入力（data/raw）
- ssds_retail_raw.json : 社会・人口統計体系 市区町村データ（小売業事業所数など、年度別）
- ssds_pop_raw_from_F46.json : 同（総人口・年齢3区分、国勢調査 2005〜2020。F46 で取得）
- ipss_projection_from_F45.csv : 社人研の市区町村別将来推計（2050年、F45 で整形）
- ssdse_a_area.csv : SSDSE-A の総面積・可住地面積
出力（data）
- panel.csv : 1行1市区町村
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def num(x):
    x = str(x).replace(",", "").strip()
    try:
        return float(x)
    except ValueError:
        return np.nan  # "-" や "***"（秘匿）は欠測


def table(rows):
    head = rows[0]
    recs = []
    for r in rows[1:]:
        code, name = r[0].split("_", 1)
        rec = {"code": code, "name": name}
        for h, v in zip(head[1:], r[1:]):
            rec[h.split("_")[0]] = num(v)
        recs.append(rec)
    return pd.DataFrame(recs)


def main():
    rt = json.load(open(RAW / "ssds_retail_raw.json"))
    # SSDS の「年度」→ 調査の時点（2011年度＝2012年経済センサス-活動調査）
    survey = {"R2002": 2002, "R2004": 2004, "R2007": 2007, "R2011": 2012,
              "R2014": 2014, "R2016": 2016, "R2021": 2021}
    sales = {"R2001": 2002, "R2003": 2004, "R2006": 2007, "R2011": 2012,
             "R2013": 2014, "R2015": 2016, "R2020": 2021}
    out = None
    for k, y in survey.items():
        t = table(rt[k])[["code", "name", "C350202", "C350302"]]
        t.columns = ["code", "name", f"stores{y}", f"workers{y}"]
        out = t if out is None else out.merge(t.drop(columns="name"), on="code", how="outer")
    for k, y in sales.items():
        t = table(rt[k])[["code", "C350102"]].rename(columns={"C350102": f"sales{y}"})
        out = out.merge(t, on="code", how="left")

    pop = json.load(open(RAW / "ssds_pop_raw_from_F46.json"))
    for y in [2005, 2010, 2015, 2020]:
        t = table(pop[f"P{y}"])[["code", "A1101", "A1303"]]
        t.columns = ["code", f"pop{y}", f"old{y}"]
        out = out.merge(t, on="code", how="left")

    ip = pd.read_csv(RAW / "ipss_projection_from_F45.csv", dtype={"code": str})
    ip["code"] = ip["code"].str.zfill(5)
    out = out.merge(ip[["code", "ipss2050"]], on="code", how="left")
    ar = pd.read_csv(RAW / "ssdse_a_area.csv", dtype={"code": str})
    out = out.merge(ar, on="code", how="left")

    # 政令市の区は、市全体と二重になるので外す（市全体の行を使う）
    out["is_ward"] = out["name"].str.contains("区$") & ~out["code"].str.startswith("13")
    out["pref"] = out["code"].str[:2]
    out = out[~out["is_ward"]].drop(columns="is_ward")
    # 東京都の特別区部（13100）は区と二重
    out = out[out["code"] != "13100"]
    out.to_csv(ROOT / "data" / "panel.csv", index=False)
    print(out.shape)
    print(out[[c for c in out.columns if c.startswith("stores")]].sum().round())
    print(out[[c for c in out.columns if c.startswith("pop")]].sum().round())


if __name__ == "__main__":
    main()
