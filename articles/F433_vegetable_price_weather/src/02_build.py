"""02 整形：物価指数（野菜の品目と生鮮食品を除く総合）と、7地点の月の気温・降水量・日照時間。
気象庁の値：「)」（準正常値）は使い、「]」（資料不足値）・「×」・「///」・空欄は欠測。
出力：data/cpi_veg.csv（年月×品目）、data/weather.csv（年月×地点×要素）
"""
import csv, gzip, io, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"
ITEMS = {"0022": "fresh_veg", "1401": "cabbage", "1403": "chinese_cabbage", "1406": "lettuce", "1414": "radish", "1434": "cucumber",
         "1436": "tomato", "1402": "spinach", "1405": "leek", "0161": "core"}


def num(s):
    s = s.strip()
    if s.endswith(")"):
        s = s[:-1].strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def main():
    rows = list(csv.reader(io.StringIO((RAW / "cpi_item_monthly.csv").read_bytes().decode("cp932"))))
    pos = {ITEMS[c]: j for j, c in enumerate(rows[2]) if c in ITEMS}
    out = [{"ym": int(r[0]), **{k: float(r[j]) for k, j in pos.items()}} for r in rows[6:] if r and r[0].isdigit()]
    pd.DataFrame(out).set_index("ym").loc[199001:].to_csv(D / "cpi_veg.csv")
    w = []
    for f in sorted((RAW / "jma").glob("*.html.gz")):
        st, el = f.name.split(".")[0].split("_")
        t = gzip.decompress(f.read_bytes()).decode("utf-8", "replace")
        for r in re.split(r"<tr[^>]*>", t):
            c = [re.sub(r"<[^>]+>", "", x).strip() for x in re.split(r"<td[^>]*>", r.split("</table>")[0])[1:]]
            if len(c) >= 13 and c[0].isdigit():
                y = int(c[0])
                for mth in range(1, 13):
                    w.append((st, el, y * 100 + mth, num(c[mth])))
    W = pd.DataFrame(w, columns=["st", "element", "ym", "value"])
    W = W[(W.ym >= 199101) & (W.ym <= 202609)]
    W.to_csv(D / "weather.csv", index=False)
    print(W.groupby(["element"]).value.count(), W.st.nunique())


if __name__ == "__main__":
    main()
