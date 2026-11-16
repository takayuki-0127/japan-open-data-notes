"""data/raw の HTML（年ごとの値、詳細：気温）から、地点×年の表 data/annual.csv を作る。ネットにはつながない。
列：日平均気温の年平均（1列目）、日最低気温の年平均（7列目）、日最低気温25℃以上の日数（15列目）など。
「]」（資料不足値）の付いた値は flag=1。「)」（準正常値）はそのまま使う。"""
import pathlib, re, html
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
st = pd.read_csv(RAW / "stations.csv", dtype=str)
COLS = {1: "tmean", 7: "tmin_mean", 14: "days_tmin_lt0", 15: "days_tmin_ge25", 16: "days_tmax_lt0", 18: "days_tmax_ge30"}


def val(s):
    m = re.match(r"^\s*(-?\d+(\.\d+)?)", s)
    return (float(m.group(1)) if m else np.nan), int("]" in s)


rows = []
for _, r in st.iterrows():
    s = (RAW / f"jma_a2_{r.block_no}.html").read_text(encoding="utf-8")
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, flags=re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(cells) >= 20 and re.match(r"^\d{4}$", cells[0]):
            rec = {"station": r.station, "group": r.group, "year": int(cells[0])}
            for j, k in COLS.items():
                v, f = val(cells[j])
                rec[k] = v; rec[k + "_flag"] = f
            rows.append(rec)
a = pd.DataFrame(rows)
order = {n: i for i, n in enumerate(st.station)}
a["order"] = a.station.map(order)
a = a.sort_values(["order", "year"]).drop(columns="order")
a.to_csv(ROOT / "data" / "annual.csv", index=False)
print(len(a), a.station.nunique(), a.year.min(), a.year.max())
