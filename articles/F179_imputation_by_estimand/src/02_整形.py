"""02 整形：SSDSE-A-2026 から、分析に使う8つの指標を市区町村ごとに作る。

SSDSE には欠測がない（全1,741市区町村で値がそろっている）。そこでこの記事では、
そろったデータを「答えがわかっている母集団」とみなし、あとから人工的に値を欠かせる。

出力 data/muni.csv（市区町村名は使わないので出力しない）
- logpop   : 総人口の対数（2020）……欠かさない
- aging    : 65歳以上人口の割合 %（2020）……欠かさない
- logdens  : 可住地1km²あたり人口の対数（2020人口／2024面積）……欠かさない
- births   : 人口千人あたり出生数（2023出生／2020人口）……欠かさない
- single   : 一般世帯に占める単独世帯の割合 %（2020）……欠かさない
- logtax   : 1人あたり地方税（千円）の対数（2022決算／2020人口）……欠かす
- unemp    : 完全失業率 %（完全失業者／(就業者＋完全失業者)、2020）……欠かす
- tert     : 就業者に占める第3次産業の割合 %（2020）……欠かす
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
raw = pd.read_csv(BASE / "data" / "raw" / "SSDSE-A-2026.csv", encoding="cp932", header=None, dtype=str)
codes = raw.iloc[0].tolist()
body = raw.iloc[3:].reset_index(drop=True)
num = body.iloc[:, 3:].apply(lambda s: pd.to_numeric(s.str.replace(",", ""), errors="coerce"))
num.columns = codes[3:]
g = num.get

d = pd.DataFrame({"area_code": body.iloc[:, 0].values})
d["logpop"] = np.log(g("A1101"))
d["aging"] = 100 * g("A1303") / g("A1101")
d["logdens"] = np.log(100 * g("A1101") / g("B1103"))  # 可住地面積は ha 単位なので km² に直す
d["births"] = 1000 * g("A4101") / g("A1101")
d["single"] = 100 * g("A810105") / g("A710101")
d["logtax"] = np.log(g("D320101") / g("A1101"))  # 千円／人
d["unemp"] = 100 * g("F1107") / (g("F1102") + g("F1107"))
d["tert"] = 100 * g("F2221") / g("F1102")

before = len(d)
d = d.replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)
print("市区町村", before, "→", len(d), "（人口0などで計算できない行を除外）")
d.to_csv(BASE / "data" / "muni.csv", index=False)
print(d.describe().round(3).to_string())
