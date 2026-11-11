"""data/ を作り直す：python fetch.py [生ファイルのフォルダ]（指定しないときは data/raw に e-Stat から取得）"""
import sys
from pathlib import Path
import pandas as pd
import tradecodes as tc
from common import DATA

FILES = {"gkc_imp_2015.csv": "000031362206", "gkc_imp_2025.csv": "000040424913"}  # 概況品別国別表（輸入、1-12月）


def build(raw):
    raw = Path(raw); rows = []
    for name in FILES:
        d = tc.long_table([raw / name], "Country"); d.insert(0, "year", int(name[8:12])); rows.append(d)
    a = pd.concat(rows, ignore_index=True)
    a = a[a.value > 0]
    a.to_csv(DATA / "imports_gaikyo_country_2015_2025.csv", index=False)
    tc.gaikyo(raw, "i")[["code", "name"]].to_csv(DATA / "gaikyo_import_names.csv", index=False)
    tc.countries(raw).to_csv(DATA / "country_names.csv", index=False)


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else DATA / "raw"
    if len(sys.argv) == 1:
        tc.download(FILES, raw)
    build(raw)
