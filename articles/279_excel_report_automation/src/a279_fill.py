"""ひな形に数字を入れて月次レポートを作る（pandas＋openpyxl）。
店が増えてもよいように、行は書き出しの店の数だけ作り、合計の式の範囲もそれに合わせる。"""
import sys, openpyxl, pandas as pd
from copy import copy
from common import DATA, ROOT
ym, prev = sys.argv[1] if len(sys.argv) > 1 else "2025-10", sys.argv[2] if len(sys.argv) > 2 else "2025-09"
DEPTS = ["食品", "日用品", "衣料", "家電", "その他"]
def load(m):
    df = pd.read_csv(DATA / f"pos_{m}.csv", encoding="utf-8-sig", dtype={"売上": str})
    df["売上"] = df["売上"].str.replace(",", "", regex=False).astype("int64")  # 「1,234」→ 1234（数値にしてから入れる）
    return df
cur, pre = load(ym), load(prev)
tab = (cur.pivot_table(index="店", columns="部門", values="売上", aggfunc="sum").reindex(columns=DEPTS).fillna(0) / 1000).round(0).astype("int64")
pre_tot = (pre.groupby("店")["売上"].sum() / 1000).round(0).astype("int64")
wb = openpyxl.load_workbook(ROOT / "template" / "monthly_template.xlsx"); ws = wb["月次"]
ws["B2"] = ym
n, fixed = len(tab), 8
if n > fixed:  # 店が増えたら行を差し込み、書式を写す
    ws.insert_rows(5 + fixed - 1 + 1, n - fixed)
    for r in range(5 + fixed, 5 + n):
        for j in range(1, 10):
            src = ws.cell(5, j); dst = ws.cell(r, j); dst._style = copy(src._style)
tot_row = 5 + n
for i, (store, row) in enumerate(tab.iterrows()):
    r = 5 + i
    ws.cell(r, 1, store)
    for j, d in enumerate(DEPTS, 2): ws.cell(r, j, int(row[d]))
    ws.cell(r, 7, f"=SUM(B{r}:F{r})")
    ws.cell(r, 8, int(pre_tot.get(store, 0)))
    ws.cell(r, 9, f"=IF(H{r}=0,\"\",G{r}/H{r}-1)")
ws.cell(tot_row, 1, "合計")
for j in range(2, 9):
    col = openpyxl.utils.get_column_letter(j); ws.cell(tot_row, j, f"=SUM({col}5:{col}{tot_row - 1})")
ws.cell(tot_row, 9, f"=IF(H{tot_row}=0,\"\",G{tot_row}/H{tot_row}-1)")
(ROOT / "output").mkdir(exist_ok=True)
out = ROOT / "output" / f"report_{ym}.xlsx"; wb.save(out); print(out.name, n, "stores")
