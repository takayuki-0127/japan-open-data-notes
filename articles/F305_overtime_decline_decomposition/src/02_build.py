"""毎勤の累積 CSV（gz）から、労働時間の月・年の表を作る（オフライン）。
出力：data/hours_monthly_size.csv（調査産業計×規模×就業形態、月、2015年〜）
      data/hours_annual_industry.csv（16大分類と調査産業計×就業形態、5人以上、年平均、2012年〜）"""
import gzip, io, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
with gzip.open(RAW / "maikin_jissu_cumulative.csv.gz", "rb") as f:
    txt = f.read().decode("cp932")
d = pd.read_csv(io.StringIO(txt), dtype={"産業分類": str, "月": str, "規模": str})
d["産業分類"] = d["産業分類"].str.strip(); d["規模"] = d["規模"].astype(str).str.strip()
d = d[d["種別"] == "実数"]
cols = {"年": "year", "月": "month", "産業分類": "ind", "規模": "size", "就業形態": "type", "総実労働時間": "total_hours",
        "所定内労働時間": "sched_hours", "所定外労働時間": "ot_hours", "出勤日数": "days", "本月末労働者数": "workers"}
m = d[(d["産業分類"] == "TL") & (d["月"] != "CY") & (d["年"] >= 2015)].rename(columns=cols)[list(cols.values())]
m["month"] = m["month"].astype(int)
m = m.drop_duplicates(["year", "month", "size", "type"], keep="last").sort_values(["size", "type", "year", "month"])
m.to_csv(DATA / "hours_monthly_size.csv", index=False)
IND = ["TL"] + list("CDEFGHIJKLMNOPQR")
a = d[(d["月"] == "CY") & (d["年"] >= 2012) & (d["規模"] == "T") & d["産業分類"].isin(IND)].rename(columns=cols)[list(cols.values())]
a = a.drop(columns=["month"]).drop_duplicates(["year", "ind", "type"], keep="last").sort_values(["ind", "type", "year"])
a.to_csv(DATA / "hours_annual_industry.csv", index=False)
print(len(m), len(a))
