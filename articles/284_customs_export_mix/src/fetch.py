"""data/ を作り直す：python fetch.py [生ファイルのフォルダ]（指定しないときは data/raw に e-Stat から取得）"""
import sys
from pathlib import Path
import pandas as pd
import tradecodes as tc
from common import DATA

# 概況品別税関一覧表（輸出、1-12月）。概況品の1桁目（0〜9）ごとに1ファイル
FILES = {**{f"zei_exp_2025_{i}.csv": f"0000{40425035 + i}" for i in range(10)},
         **{f"zei_exp_2015_{i}.csv": f"0000{31361722 + i}" for i in range(10)}}


def build(raw):
    raw = Path(raw); rows = []
    for y in (2015, 2025):
        d = tc.long_table([raw / f"zei_exp_{y}_{i}.csv" for i in range(10)], "Custom"); d.insert(0, "year", y); rows.append(d)
    a = pd.concat(rows, ignore_index=True)
    a = a[(a.value > 0) & (a.Commodity.str.len() <= 5)]
    a.to_csv(DATA / "exports_customs_gaikyo_2015_2025.csv", index=False)
    tc.gaikyo(raw, "e")[["code", "name"]].to_csv(DATA / "gaikyo_export_names.csv", index=False)
    tc.customs(raw).to_csv(DATA / "customs_names.csv", index=False)


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else DATA / "raw"
    if len(sys.argv) == 1:
        tc.download(FILES, raw)
    build(raw)
