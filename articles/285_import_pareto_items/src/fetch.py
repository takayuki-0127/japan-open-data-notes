"""data/ を作り直す：python fetch.py [生ファイルのフォルダ]（指定しないときは data/raw に e-Stat から取得）"""
import sys
from pathlib import Path
import pandas as pd
import tradecodes as tc
from common import DATA

FILES = {"hin_imp_2015.csv": "000031362184", "hin_imp_2020.csv": "000032046081", "hin_imp_2025.csv": "000040424891",
         "hin_exp_2025.csv": "000040424890"}  # 統計品別表（1-12月）


def build(raw):
    raw = Path(raw); rows = []
    for name in FILES:
        d = tc.hinbetu(raw / name)[["HS", "value"]]
        d.insert(0, "flow", "import" if "imp" in name else "export"); d.insert(1, "year", int(name[8:12])); rows.append(d)
    a = pd.concat(rows, ignore_index=True)
    a.to_csv(DATA / "hs9_values.csv", index=False)
    top = a[(a.flow == "import") & (a.year == 2025)].nlargest(60, "value").HS
    tc.finest_gaikyo(sorted(top), raw, "i").to_csv(DATA / "hs9_to_gaikyo_top_import2025.csv", index=False)


if __name__ == "__main__":
    raw = sys.argv[1] if len(sys.argv) > 1 else DATA / "raw"
    if len(sys.argv) == 1:
        tc.download(FILES, raw)
    build(raw)
