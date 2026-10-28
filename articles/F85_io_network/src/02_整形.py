"""F85 整形：国内の中間取引（競争輸入型の表から輸入分を除いたもの）を CSV に書き出す（確認用）。
python src/02_整形.py → data/domestic_flows_2020.csv, data/sectors_2020_basic.csv
"""
import numpy as np, pandas as pd
from common import ROOT, load_table, matrices

t = load_table("2020"); m = matrices(t)
Zd = (1 - m["m"])[:, None] * t["Z"]
pd.DataFrame(Zd.round(3), index=t["sec"], columns=t["sec"]).to_csv(ROOT / "data/domestic_flows_2020.csv", encoding="utf-8-sig")
pd.DataFrame({"部門コード": t["sec"], "部門": t["name"], "国内生産額_十億円": t["X"], "粗付加価値_十億円": t["VA"],
              "輸入係数": m["m"]}).to_csv(ROOT / "data/sectors_2020_basic.csv", index=False, encoding="utf-8-sig")
print("中間取引（国内分）の合計（十億円）:", round(float(Zd.sum()), 1), " うち自部門内:", round(float(np.trace(Zd)), 1))
print("GDP（粗付加価値の合計、十億円）:", round(float(t["VA"].sum()), 1))
