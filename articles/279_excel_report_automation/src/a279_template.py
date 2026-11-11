"""月次レポートのひな形（Excel）を作る。人が毎月コピーして数字を貼っていた形を再現する。
表の範囲は 8 店ぶんで固定（手で作ったひな形によくある形）。"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from common import ROOT
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "月次"
depts = ["食品", "日用品", "衣料", "家電", "その他"]
ws["A1"] = "月次売上レポート（千円）"; ws["A1"].font = Font(size=14, bold=True)
ws["A2"] = "対象月："; ws["B2"] = ""
hdr = ["店"] + depts + ["合計", "前月合計", "前月比"]
for j, h in enumerate(hdr, 1):
    c = ws.cell(4, j, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2A78D6"); c.alignment = Alignment(horizontal="center")
for i in range(8):  # 5〜12行目：8店ぶん
    r = 5 + i
    ws.cell(r, 7, f"=SUM(B{r}:F{r})"); ws.cell(r, 9, f"=IF(H{r}=0,\"\",G{r}/H{r}-1)")
ws.cell(13, 1, "合計").font = Font(bold=True)
for j in range(2, 9):
    col = openpyxl.utils.get_column_letter(j); ws.cell(13, j, f"=SUM({col}5:{col}12)").font = Font(bold=True)
ws.cell(13, 9, "=IF(H13=0,\"\",G13/H13-1)")
for r in range(5, 14):
    for j in range(2, 9): ws.cell(r, j).number_format = "#,##0"
    ws.cell(r, 9).number_format = "0.0%"
thin = Side(style="thin", color="A3A29C")
for r in range(4, 14):
    for j in range(1, 10): ws.cell(r, j).border = Border(top=thin, bottom=thin, left=thin, right=thin)
ws.column_dimensions["A"].width = 8
(ROOT / "template").mkdir(exist_ok=True)
wb.save(ROOT / "template" / "monthly_template.xlsx"); print("ok")
