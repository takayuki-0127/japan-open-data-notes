"""data/raw から分析用の月次の表を作る（オフライン）。
出力：data/maikin_monthly.csv（2015年以降、5人以上・30人以上、就業形態計、全産業の中分類）
      data/truck_monthly.csv（営業用・合計の輸送トン数・トンキロ、2020年4月〜）"""
import gzip, io, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"

with gzip.open(RAW / "maikin_jissu_cumulative.csv.gz", "rb") as f:
    txt = f.read().decode("cp932")
d = pd.read_csv(io.StringIO(txt), dtype={"産業分類": str, "月": str, "規模": str})
d["産業分類"] = d["産業分類"].str.strip(); d["規模"] = d["規模"].astype(str).str.strip()
d = d[(d["種別"] == "実数") & (d["月"] != "CY") & (d["年"] >= 2015) & (d["就業形態"] == 0) & (d["規模"].isin(["T", "0"]))].copy()
d["month"] = d["月"].astype(int)
cols = {"年": "year", "産業分類": "ind", "規模": "size", "現金給与総額": "total_pay", "所定内給与": "sched_pay",
        "総実労働時間": "total_hours", "所定内労働時間": "sched_hours", "所定外労働時間": "ot_hours", "出勤日数": "days"}
d = d.rename(columns=cols)[["year", "month", "ind", "size", "total_pay", "sched_pay", "total_hours", "sched_hours", "ot_hours", "days"]]
d = d.drop_duplicates(["year", "month", "ind", "size"], keep="last").sort_values(["size", "ind", "year", "month"]).reset_index(drop=True)
d.to_csv(DATA / "maikin_monthly.csv", index=False)

# 自動車輸送統計：各年4月分の総括表から月の値を取る（同じ月は新しい表を優先）
recs = []
for y in range(2021, 2027):
    for kind in ("ton", "tonkm"):
        v = pd.read_excel(RAW / f"truck_{kind}_{y}04.xlsx", header=None)
        assert str(v.iloc[6, 4]).startswith("営業用計") and str(v.iloc[6, 2]).startswith("合計")
        assert str(v.iloc[6, 8]).startswith("3トン未満") and str(v.iloc[6, 16]).startswith("16トン以上")
        for i in range(8, len(v)):
            code = str(v.iloc[i, 1]).strip()
            m = re.fullmatch(r"(\d{4})00(\d{2})(\d{2})", code)
            if m and m.group(2) == m.group(3) and m.group(2) != "00":
                num = lambda j: float(v.iloc[i, j]) if str(v.iloc[i, j]).strip() not in ("-", "nan", "") else np.nan
                recs.append(dict(kind=kind, year=int(m.group(1)), month=int(m.group(2)), release=y,
                                 total=num(2), commercial=num(4), lt3=num(8), t3_6=num(10), t6_11=num(12), t11_16=num(14), t16p=num(16)))
t = pd.DataFrame(recs).sort_values(["kind", "year", "month", "release"]).drop_duplicates(["kind", "year", "month"], keep="last")
t = t.pivot(index=["year", "month"], columns="kind", values=["total", "commercial", "lt3", "t3_6", "t6_11", "t11_16", "t16p"])
t.columns = [f"{b}_{a}" for a, b in t.columns]
t = t.reset_index().sort_values(["year", "month"]).reset_index(drop=True)
t = t[(t.year * 12 + t.month) >= (2020 * 12 + 4)]
t.to_csv(DATA / "truck_monthly.csv", index=False)
print(len(d), len(t), t.head(2).to_dict("records"), t.tail(1).to_dict("records"))
