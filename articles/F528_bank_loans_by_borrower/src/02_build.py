"""data/raw の JSON を長い形の表 data/loans_long.csv にまとめる（オフライン）。
系列の名前（見出しの文字）から、勘定・規模・業種を読み取る。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SIZES = {"中小企業": "sme", "中堅企業": "mid", "大企業": "large"}

def parse(name):
    p = [x.strip() for x in name.split("／")]
    size = "all"
    if p[0] in SIZES:
        size = SIZES[p[0]]; p = p[1:]
    sector = p[0]
    if p[-1] == "信用金庫":
        acc = "shinkin"
    elif "銀行勘定、信託勘定、海外店勘定の合計" in name:
        acc = "3acc"
    elif "個人向け貸出金" in name:
        acc = "bank"; sector = sector + "（個人向け）"
    else:
        assert p[-2] == "銀行勘定" and p[-1] == "国内銀行", name
        acc = "bank"
    return acc, size, sector

def main():
    rows = []
    for f in sorted(RAW.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        for r in j["RESULTSET"]:
            acc, size, sector = parse(r["NAME_OF_TIME_SERIES_J"])
            assert r["FREQUENCY"] == "QUARTERLY"
            for d, v in zip(r["VALUES"]["SURVEY_DATES"], r["VALUES"]["VALUES"]):
                if v is None: continue
                y, q = divmod(int(d), 100)
                rows.append((acc, size, sector, f"{y}Q{q}", float(v), r["SERIES_CODE"]))
    df = pd.DataFrame(rows, columns=["account", "size", "sector", "quarter", "oku_yen", "code"])
    df = df.sort_values(["account", "size", "sector", "quarter"]).reset_index(drop=True)
    assert not df.duplicated(["account", "size", "sector", "quarter"]).any()
    df.to_csv(ROOT / "data" / "loans_long.csv", index=False, encoding="utf-8")
    print(df.shape, df.groupby(["account", "size"]).sector.nunique().to_dict())

if __name__ == "__main__":
    main()
