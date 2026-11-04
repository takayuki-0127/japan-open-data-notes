"""02 整形：気象庁「年ごとの値」「月ごとの値」から日降水量の最大値を取り出し、分析用の表にする。

- 値の後ろの「]」（資料不足値）と、空欄・「×」・「--」は使わない（欠測扱い）。
- 「)」（準正常値）は使う。
- 2026年は年の途中なので使わない。1901〜2025年に限る。
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"


def parse(v):
    s = "" if pd.isna(v) else str(v).strip()
    if s == "" or "]" in s or "×" in s or "--" in s:
        return None
    s = s.replace(")", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def main():
    a = pd.read_csv(D / "jma_annual_raw.csv", encoding="utf-8-sig")
    a["station"] = a["station"].str.replace(r"（.*", "", regex=True)
    a["amax"] = a["daily_max_raw"].map(parse)
    a = a[(a.year >= 1901) & (a.year <= 2025)]
    out = a[["block_no", "station", "year", "amax"]].dropna()
    out.to_csv(D / "annual_max.csv", index=False)
    print("年最大：", len(out), "行", out.station.nunique(), "地点")

    mp = D / "jma_monthly_raw.csv"
    if mp.exists():
        m = pd.read_csv(mp, encoding="utf-8-sig")
        m["mmax"] = m["daily_max_raw"].map(parse)
        m = m[(m.year >= 1901) & (m.year <= 2025)]
        mo = m[["block_no", "station", "year", "month", "mmax"]].dropna()
        mo.to_csv(D / "monthly_max.csv", index=False)
        print("月最大：", len(mo), "行", mo.station.nunique(), "地点")


if __name__ == "__main__":
    main()
