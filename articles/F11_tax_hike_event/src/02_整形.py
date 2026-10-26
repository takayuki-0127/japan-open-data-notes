"""CSV を「項目 × 月」の縦長の表にし、実質の支出（2015年の価格）を作る。

実質化：長期時系列表の名目増減率と実質増減率（前年同月比）から、
前年同月比の物価の比 (1+名目)/(1+実質) を求め、2015年の各月を 1 として12か月ずつつないでデフレーターを作る。
"""
import csv
import numpy as np
import pandas as pd
from common import RAW, DATA, STAT_IDS


def read_table(sid, name_col=5, first=6):
    rows = list(csv.reader(open(RAW / f"kakei_{sid}.csv", encoding="utf-8")))
    years = rows[1][first:]
    months = rows[3][first:]
    dates = []
    y = None
    for yy, mm in zip(years, months):
        if yy.strip():
            y = int(yy.strip().replace("年", ""))
        if not mm.strip():
            dates.append(None)
            continue
        dates.append(f"{y}-{int(mm.strip().replace('月', '')):02d}")
    out = []
    for r in rows[4:]:
        if len(r) <= first:
            continue
        name = r[name_col].strip()
        for d, v in zip(dates, r[first:]):
            if d is None:
                continue
            v = v.strip()
            try:
                val = float(v)
            except ValueError:
                val = np.nan
            out.append((int(r[0]), name, d, val))
    return pd.DataFrame(out, columns=["no", "item", "date", "value"])


amt = read_table(STAT_IDS["amount"]).rename(columns={"value": "amount"})
nom = read_table(STAT_IDS["nominal"]).rename(columns={"value": "nom"})
rea = read_table(STAT_IDS["real"]).rename(columns={"value": "real"})
df = amt.merge(nom, on=["no", "item", "date"]).merge(rea, on=["no", "item", "date"])
df["date"] = pd.PeriodIndex(df["date"], freq="M")
df = df.sort_values(["no", "date"])

# デフレーター（2015年 = 1）
def chain(g):
    g = g.set_index("date").sort_index()
    ratio = (1 + g["nom"] / 100) / (1 + g["real"] / 100)
    d = pd.Series(np.nan, index=g.index)
    base = g.index[g.index.year == 2015]
    d.loc[base] = 1.0
    idx = list(g.index)
    pos = {p: i for i, p in enumerate(idx)}
    for p in idx:  # 2016年以降は前に
        if p.year > 2015 and (p - 12) in pos:
            d.loc[p] = d.loc[p - 12] * ratio.loc[p]
    for p in reversed(idx):  # 2014年以前は後ろに
        if p.year < 2015 and (p + 12) in pos:
            d.loc[p] = d.loc[p + 12] / ratio.loc[p + 12]
    g["deflator"] = d
    g["real_amount"] = g["amount"] / g["deflator"]
    return g.reset_index()

df = pd.concat([chain(g).assign(no=k) for k, g in df.groupby("no")], ignore_index=True)
df.to_csv(DATA / "kakei_monthly_long.csv", index=False)
print(df[df.item == "消費支出"].tail(3))
print("rows", len(df))
