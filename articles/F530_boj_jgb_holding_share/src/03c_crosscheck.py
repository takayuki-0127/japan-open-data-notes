"""03c 照らし合わせ：API から作った表の値を、日銀の参考図表 sjlong.xlsx（シート64、
「中央政府＋財政融資資金が発行する債券（長期）」の保有者別残高）と、見出しの文字で行と列を対応させて比べる。
出力：results/crosscheck_sjlong.csv
"""
import pathlib
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
t = pd.read_csv(D / "ff_quarterly.csv", index_col="period")
API = {"総発行残高": t["FOF_FFAS420L311"] + t["FOF_FFAS181L311"], "うち中央銀行による保有": t["FOF_FFAS110A311"],
       "社会保障基金による保有": t["FOF_FFAS423A311"], "家計による保有": t["FOF_FFAS430A311"], "海外による保有": t["FOF_FFAS500A311"]}


def main():
    wb = openpyxl.load_workbook(ROOT / "data" / "raw" / "sjlong.xlsx", read_only=True, data_only=True)
    rows = [list(r) for r in wb["64"].iter_rows(values_only=True)]
    i = next(i for i, r in enumerate(rows) if "中央政府＋財政融資資金が発行する債券（長期）" in r)
    hdr = rows[i + 1]
    cols = {}
    for j, c in enumerate(hdr):
        if c:
            y, q = str(c).replace("(P)", "").split("/")   # 例 "2024/1Q" → "2024Q1"
            cols[j] = f"{y}Q{q[0]}"
    out = []
    for r in rows[i + 2:i + 13]:
        lab = next((c for c in r if isinstance(c, str)), None)
        if lab not in API:
            continue
        for j, per in cols.items():
            v = r[j]
            if v is None:
                continue
            a = float(API[lab][per])
            out.append({"item": lab, "period": per, "sjlong": float(v), "api": a, "diff": a - float(v)})
    df = pd.DataFrame(out)
    df.to_csv(R / "crosscheck_sjlong.csv", index=False)
    print(len(df), "cells, max abs diff", df["diff"].abs().max())


if __name__ == "__main__":
    main()
