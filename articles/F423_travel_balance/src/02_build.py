"""02 整形：国際収支（サービス）月次と訪日外客数（総数）月次をつなぎ、暦年の表を作る。
出力：data/monthly.csv, data/annual.csv
"""
import pathlib
import openpyxl
import pandas as pd
from bojload import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
NAME = {"BPBP6JYNSN": "services", "BPBP6JYNSN1": "transport", "BPBP6JYNSC2": "travel_rec", "BPBP6JYNSD2": "travel_pay",
        "BPBP6JYNSN2": "travel", "BPBP6JYNSC21": "travel_rec_business", "BPBP6JYNSC22": "travel_rec_personal",
        "BPBP6JYNSD21": "travel_pay_business", "BPBP6JYNSD22": "travel_pay_personal", "BPBP6JYNSN9": "other_services"}


def visitors():
    wb = openpyxl.load_workbook(RAW / "jnto_visitors_2003_2026.xlsx", read_only=True, data_only=True)
    rows = []
    for sh in wb.sheetnames:
        y = int(sh)
        ws = wb[sh]
        hdr = None
        for r in ws.iter_rows(values_only=True):
            if "1月" in r[:3]:
                hdr = r
            elif hdr is not None and r[0] == "総数":
                for j, h in enumerate(hdr):
                    if isinstance(h, str) and h.endswith("月") and h[:-1].isdigit():
                        v = r[j]
                        if isinstance(v, (int, float)):
                            rows.append((y * 100 + int(h[:-1]), int(v)))
                break
    return pd.Series(dict(sorted(rows)), name="visitors")


def main():
    m = load(RAW / "boj_services_monthly.json").rename(columns=NAME)
    m = m.join(load(RAW / "boj_usdjpy_monthly.json")["FXERM07"].rename("usdjpy")).join(visitors())
    m.index.name = "ym"
    m["year"] = m.index // 100
    m.round(4).to_csv(D / "monthly.csv")
    full = m[m.year <= 2025]
    cols = list(NAME.values())
    a = full.groupby("year")[cols].sum(min_count=12)
    a["travel_rec_usd"] = (full.travel_rec / full.usdjpy).groupby(full.year).sum(min_count=12)
    a["visitors"] = full.groupby("year").visitors.sum(min_count=12)
    a["usdjpy"] = full.groupby("year").usdjpy.mean()
    a.round(4).to_csv(D / "annual.csv")
    print(a[["travel_rec", "travel_pay", "travel", "services", "visitors"]].tail(8))


if __name__ == "__main__":
    main()
