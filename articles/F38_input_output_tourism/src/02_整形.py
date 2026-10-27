"""F38 整形：産業連関表から分析に使う行列と係数を CSV に書き出す（確認用）。
python src/02_整形.py → data/io2020_108_vectors.csv, data/io2020_A108.csv
"""
import numpy as np, pandas as pd
from common import ROOT, load_table, matrices, employment_coef

t = load_table("2020"); m = matrices(t); e = employment_coef(t)
v = pd.DataFrame({"部門コード": t["sec"], "部門": t["name"], "国内生産額_十億円": t["X"],
                  "雇用者所得率": m["w"], "粗付加価値率": m["v"], "輸入係数": m["m"],
                  "従業者_人_per_十億円": e, "民間消費_構成比_帰属家賃除く": m["h"],
                  "逆行列_列和_競争輸入型": m["B"].sum(0), "逆行列_列和_閉鎖型": m["B0"].sum(0)})
v.to_csv(ROOT / "data/io2020_108_vectors.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(m["A"], index=t["sec"], columns=t["sec"]).round(6).to_csv(ROOT / "data/io2020_A108.csv", encoding="utf-8-sig")
# 検算：国内生産額＝中間需要＋最終需要−輸入（行）と、中間投入＋粗付加価値（列）
col = t["Z"].sum(0) + t["VA"]
print("列の検算 最大差（十億円）:", float(np.abs(col - t["X"]).max()))
print("国内生産額合計（十億円）:", round(float(t["X"].sum()), 1))
