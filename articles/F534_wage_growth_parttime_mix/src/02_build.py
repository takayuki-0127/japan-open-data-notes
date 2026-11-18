"""data/raw の累積データ（gzip）から、調査産業計・年平均・1993〜2025年の行を抜き出す。
名前（規模・就業形態）は記号の対応表で付け、列は見出しの文字で選ぶ。"""
import gzip, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
with gzip.open(ROOT / "data" / "raw" / "maikin_jissu_cumulative.csv.gz", "rb") as f:
    d = pd.read_csv(f, encoding="cp932", dtype=str)
d.columns = [c.strip() for c in d.columns]
d = d[(d["産業分類"].str.strip() == "TL") & (d["月"] == "CY")].copy()
d["year"] = d["年"].astype(int)
d = d[(d.year >= 1993) & (d.year <= 2025)]
SIZE = {"T": "5人以上", "0": "30人以上", "4": "500人以上", "5": "100〜499人", "7": "30〜99人", "9": "5〜29人"}
FORM = {"0": "計", "1": "一般", "2": "パート"}
d = d[d["規模"].isin(SIZE) & d["就業形態"].isin(FORM)]
COLS = {"現金給与総額": "cash", "所定内給与": "sched", "総実労働時間": "hours", "本月末労働者数": "workers", "パートタイム労働者数": "part_workers"}
out = pd.DataFrame({"year": d.year, "size_code": d["規模"], "size": d["規模"].map(SIZE),
                    "form_code": d["就業形態"], "form": d["就業形態"].map(FORM)})
for k, v in COLS.items():
    out[v] = pd.to_numeric(d[k], errors="coerce")
out = out.sort_values(["size_code", "form_code", "year"]).reset_index(drop=True)
out.to_csv(ROOT / "data" / "maikin_tl_cy.csv", index=False, encoding="utf-8", lineterminator="\n")
print(out.shape)
print(out.groupby(["size", "form"]).year.agg(["min", "max", "count"]))
