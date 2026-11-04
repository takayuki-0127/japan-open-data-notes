"""02 整形：分析用の表を作る

- 年度×性×年齢（5〜17歳）の平均身長
- 生まれ年の目安 cohort = 年度 − 年齢（4月1日の満年齢なので、ほぼ「その年度に○歳になる世代」）
- 2020〜2023年度はコロナで測定の時期がずれた（文部科学省の注記）ので flag_covid=1
- 1940〜1947年度は調査なし、1939年度以前は調べ方が違う（prewar=1）
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
d = pd.read_csv(ROOT / "data" / "height_long.csv", encoding="utf-8-sig")
d["sex"] = d["sex"].map({"男": "M", "女": "F"})
d["cohort"] = d["year"] - d["age"]
d["flag_covid"] = d["year"].between(2020, 2023).astype(int)
d["prewar"] = (d["year"] <= 1939).astype(int)
d = d.sort_values(["sex", "age", "year"]).reset_index(drop=True)
(ROOT / "results").mkdir(exist_ok=True)
d.to_csv(ROOT / "results" / "height_panel.csv", index=False, encoding="utf-8")
print(d.shape, d.year.min(), d.year.max())
