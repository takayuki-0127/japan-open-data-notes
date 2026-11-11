"""data/ を作り直す：python fetch.py [生ファイルのフォルダ] [日本銀行APIのドル円JSON]"""
import sys, json
from pathlib import Path
import pandas as pd
import tradecodes as tc
from common import DATA

FILES = {"hin_exp_2015.csv": "000031362183", "hin_exp_2020.csv": "000032046080", "hin_exp_2025.csv": "000040424890"}  # 統計品別表（輸出）


def build(raw, fx):
    raw = Path(raw); rows = []
    for name in FILES:
        d = tc.hinbetu(raw / name); d.insert(0, "year", int(name[8:12])); rows.append(d)
    a = pd.concat(rows, ignore_index=True)
    a["total_all_exports"] = a.groupby("year").value.transform("sum")
    tot = a.groupby("year").value.sum().rename("all_exports").reset_index()
    tot.to_csv(DATA / "all_exports_total.csv", index=False)
    f = a[a.HS.str[:2].between("01", "23") & ~a.HS.str.startswith("00")].drop(columns="total_all_exports")
    f.to_csv(DATA / "food_exports_hs9.csv", index=False)
    tc.finest_gaikyo(sorted(f.HS.unique()), raw, "e").to_csv(DATA / "hs9_to_gaikyo_export.csv", index=False)
    fx.rename("usdjpy").rename_axis("year").reset_index().to_csv(DATA / "usdjpy_annual.csv", index=False)


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else DATA / "raw"
    if len(sys.argv) == 1:
        tc.download(FILES, raw)
    if len(sys.argv) > 2:
        v = json.load(open(sys.argv[2]))["RESULTSET"][0]["VALUES"]
    else:
        import requests
        v = requests.get("https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&startDate=201501&endDate=202512&code=FXERM07", timeout=60).json()["RESULTSET"][0]["VALUES"]
    s = pd.Series(v["VALUES"], index=v["SURVEY_DATES"], dtype=float)
    build(raw, s.groupby(s.index // 100).mean().loc[2015:2025])
