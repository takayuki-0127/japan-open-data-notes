"""02 整形：部門×年のパネル data/processed/panel.csv を作る（1994〜2020年、99部門）。"""
import pathlib
import openpyxl, pandas as pd
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

def wide(wb, sheet, r0=3, label_row=2, nrow=99):
    ws = wb[sheet]
    rows = list(ws.iter_rows(min_row=label_row, max_row=label_row + nrow, values_only=True))
    cols, seen = [], set()
    for j, y in enumerate(rows[0]):  # 同じ年が2回出る表（NV）は最初の列だけ使う
        if j >= 2 and isinstance(y, (int, float)) and int(y) not in seen:
            cols.append((j, int(y))); seen.add(int(y))
    recs = []
    for r in rows[1:]:
        if r[0] is None or not isinstance(r[0], int) or r[0] > 99:
            continue
        for j, y in cols:
            recs.append((r[0], r[1], y, r[j]))
    return pd.DataFrame(recs, columns=["code", "name", "year", sheet])

wb4 = openpyxl.load_workbook(RAW / "jip2023_4.xlsx", read_only=True, data_only=True)
df = None
for s in ["V", "NV", "TFPva", "LP_G", "VConK_T", "VConKC", "VConLC"]:
    d = wide(wb4, s)
    df = d if df is None else df.merge(d.drop(columns="name"), on=["code", "year"], how="outer")
# 市場経済の旗（DS の 202 列）
ws = wb4["DS"]
rows = list(ws.iter_rows(min_row=1, max_row=101, values_only=True))
col = rows[0].index(202)
mkt = {r[0]: r[col] for r in rows[2:] if isinstance(r[0], int) and r[0] <= 99}
df["market"] = df["code"].map(mkt)

# マンアワーの水準（千時間）
wb3 = openpyxl.load_workbook(RAW / "jip2023_3-8.xlsx", read_only=True, data_only=True)
ws = wb3["Sheet1"]
rows = list(ws.iter_rows(min_row=2, max_row=102, values_only=True))
cols = [(j, int(y)) for j, y in enumerate(rows[0]) if j >= 2 and isinstance(y, (int, float))]
rec = []
for r in rows[1:]:
    if isinstance(r[0], int) and r[0] <= 99:
        rec += [(r[0], y, r[j]) for j, y in cols]
df = df.merge(pd.DataFrame(rec, columns=["code", "year", "MH"]), on=["code", "year"], how="left")

# 資本：投資・資産マトリックス（部門×資産×年）
wb2 = openpyxl.load_workbook(RAW / "jip2023_2.xlsx", read_only=True, data_only=True)
ws = wb2["投資・資産マトリックス"]
rec = []
for r in ws.iter_rows(min_row=3, values_only=True):
    if r[0] is None:
        continue
    rec.append(r[:10])
m = pd.DataFrame(rec, columns=["code", "name", "asset", "asset_name", "year",
                               "inv_nom", "inv_real", "stk_nom", "stk_real", "kcost_nom"])
m = m[m["code"].apply(lambda x: isinstance(x, int) and x <= 99)]
for c in ["inv_nom", "inv_real", "stk_nom", "stk_real"]:
    m[c] = pd.to_numeric(m[c], errors="coerce")
ICT = {321, 322, 630}
SW = {630}
g = m.groupby(["code", "year"])
cap = pd.DataFrame({
    "inv_nom_all": g["inv_nom"].sum(min_count=1),
    "stk_real_all": g["stk_real"].sum(min_count=1),
})
for lab, s in [("ict", ICT), ("sw", SW), ("ithw", {321, 322})]:
    mm = m[m["asset"].isin(s)].groupby(["code", "year"])
    cap[f"inv_nom_{lab}"] = mm["inv_nom"].sum(min_count=1)
    cap[f"stk_real_{lab}"] = mm["stk_real"].sum(min_count=1)
df = df.merge(cap.reset_index(), on=["code", "year"], how="left")
df["name"] = df["code"].map(df.dropna(subset=["name"]).groupby("code")["name"].first())
df = df[df["year"] <= 2020].sort_values(["code", "year"])
assert not df.duplicated(["code", "year"]).any()
out = ROOT / "data" / "processed" / "panel.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False, float_format="%.6g")
print(out, df.shape, df["code"].nunique(), "部門", df["year"].min(), "-", df["year"].max())
