"""毎勤の累積 CSV（gz）から、年平均・一般とパート・調査産業計と大分類の表を作る（オフライン）。
出力：data/maikin_annual_by_type.csv"""
import gzip, io, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
with gzip.open(RAW / "maikin_jissu_cumulative.csv.gz", "rb") as f:
    txt = f.read().decode("cp932")
d = pd.read_csv(io.StringIO(txt), dtype={"産業分類": str, "月": str, "規模": str})
d["産業分類"] = d["産業分類"].str.strip(); d["規模"] = d["規模"].astype(str).str.strip()
INDS = ["TL"] + list("CDEFGHIJKLMNOPQR")
d = d[(d["種別"] == "実数") & (d["月"] == "CY") & (d["年"] >= 2010) & (d["就業形態"].isin([1, 2])) & (d["規模"].isin(["T", "0"])) & d["産業分類"].isin(INDS)]
cols = {"年": "year", "産業分類": "ind", "規模": "size", "就業形態": "type", "現金給与総額": "total_pay", "所定内給与": "sched_pay",
        "総実労働時間": "total_hours", "所定内労働時間": "sched_hours", "本月末労働者数": "workers"}
d = d.rename(columns=cols)[list(cols.values())]
d["type"] = d["type"].map({1: "general", 2: "part"})
d = d.drop_duplicates(["year", "ind", "size", "type"], keep="last").sort_values(["size", "type", "ind", "year"]).reset_index(drop=True)
d.to_csv(DATA / "maikin_annual_by_type.csv", index=False)
print(len(d), d.groupby(["size", "type"]).size().to_dict())
