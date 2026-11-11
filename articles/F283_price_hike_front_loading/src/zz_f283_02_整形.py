"""F283 02 整形：家計調査の品目の月の支出と、消費者物価の品目指数をつなぐ。

出力 data/panel.csv：ym, item, spend（円）, cpi（2020=100）, real（支出÷物価×100）
"""
import pathlib
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "raw"

# --- 家計調査 ---
NAME2ITEM = {
    "消費支出": "consumption", "酒類": "alcohol_all", "たばこ": "tobacco",
    "ビール": "beer", "発泡酒・ビール風アルコール飲料": "happo", "清酒": "sake",
    "ワイン": "wine", "焼酎": "shochu", "ウイスキー": "whisky",
    "チューハイ・カクテル": "chuhai",
}
recs = []
blocks = RAW.joinpath("kakei_items_monthly_2015_2026.csv").read_text(encoding="utf-8").split("#")
for blk in blocks:
    lines = [l for l in blk.splitlines() if l.strip()]
    if len(lines) < 3:
        continue
    yrow = lines[1].split(",")
    years, cur = [], None
    for c in yrow[8:]:
        if c.strip():
            cur = int(c.strip().replace("年", ""))
        years.append(cur)
    for l in lines[3:]:
        c = l.split(",")
        name = c[7].strip()
        if name not in NAME2ITEM:
            continue
        vals = c[8:]
        mcount = {}
        for y, v in zip(years, vals):
            if y is None or v.strip() in ("", "-", "…"):
                continue
            mcount[y] = mcount.get(y, 0) + 1
            recs.append((y * 100 + mcount[y], NAME2ITEM[name], float(v)))
# 2025年以降の 3X7（名前が「発泡酒」に変わった）
l = RAW.joinpath("kakei_3X7_2025_2026.csv").read_text(encoding="utf-8").splitlines()[1]
vals = [float(v) for v in l.split(",")[8:] if v.strip()]
for i, v in enumerate(vals):
    y, m = 2025 + i // 12, i % 12 + 1
    recs.append((y * 100 + m, "happo", v))
kk = pd.DataFrame(recs, columns=["ym", "item", "spend"]).drop_duplicates(["ym", "item"])
kk = kk.sort_values(["item", "ym"])

# --- 消費者物価 ---
cpi = pd.read_csv(RAW / "cpi_items_monthly_f209.csv.gz")
meta = pd.read_csv(RAW / "cpi_items_meta_f209.csv", dtype={"code": str})
w = dict(zip(meta["code"], meta["weight"]))
col = {c.split("|")[1]: c for c in cpi.columns if "|" in c}


def geo(codes):
    ws = np.array([w[c] for c in codes], float)
    ws = ws / ws.sum()
    return np.exp(sum(wi * np.log(cpi[col[c]].astype(float)) for wi, c in zip(ws, codes)))


cp = pd.DataFrame({"ym": cpi["ym"].astype(int)})
cp["beer"] = cpi[col["2021"]].astype(float)
cp["happo"] = geo(["2026", "2027"])
cp["sake"] = cpi[col["2003"]].astype(float)
cp["wine"] = geo(["2041", "2042"])
cp["tobacco"] = cpi[col["0155"]].astype(float)
cp["alcohol_all"] = geo(["2003", "2011", "2021", "2026", "2027", "2041", "2042", "2012"])
cp["consumption"] = cpi[col["0001"]].astype(float)
cpl = cp.melt("ym", var_name="item", value_name="cpi")

panel = kk.merge(cpl, on=["ym", "item"], how="inner")
panel = panel[(panel.ym >= 201501) & (panel.ym <= 202609)]
panel["real"] = panel["spend"] / panel["cpi"] * 100
panel = panel.sort_values(["item", "ym"]).reset_index(drop=True)
(BASE / "data").mkdir(exist_ok=True)
panel.to_csv(BASE / "data" / "panel.csv", index=False, float_format="%.6g")
print(panel.groupby("item").agg(n=("ym", "size"), first=("ym", "min"), last=("ym", "max")))
assert panel.groupby("item").size().min() == 141, "月数が足りない品目がある"
