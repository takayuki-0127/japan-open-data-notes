"""出来上がった Excel を、pandas を使わない別の計算（csv＋Decimal）と1セルずつ照合する。
あわせて、手作業でよく起きる3つのわなを再現して、ずれの大きさを測る。"""
import csv, json, shutil, subprocess, tempfile
from decimal import Decimal, ROUND_HALF_EVEN
from collections import defaultdict
from pathlib import Path
import openpyxl
from common import DATA, ROOT, RES
DEPTS = ["食品", "日用品", "衣料", "家電", "その他"]
def indep(m):
    t = defaultdict(Decimal)
    with open(DATA / f"pos_{m}.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): t[(r["店"], r["部門"])] += Decimal(r["売上"].replace(",", ""))
    return t
def k(x): return int((x / 1000).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))
cur, pre = indep("2025-10"), indep("2025-09")
stores = sorted({s for s, _ in cur})
def recalc(path):  # LibreOffice で開き直して数式を計算させる
    d = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(d), str(path)], capture_output=True, timeout=180)
    out = d / path.name; wb = openpyxl.load_workbook(out, data_only=True); shutil.rmtree(d); return wb["月次"]
rep = ROOT / "output" / "report_2025-10.xlsx"
raw = openpyxl.load_workbook(rep)["月次"]; cached = openpyxl.load_workbook(rep, data_only=True)["月次"]
n_formula = sum(1 for row in raw.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("="))
n_cached_none = sum(1 for row in raw.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=") and cached[c.coordinate].value is None)
ws = recalc(rep)
mis, cells = [], 0
for i, s in enumerate(stores):
    r = 5 + i
    assert ws.cell(r, 1).value == s
    for j, d in enumerate(DEPTS, 2):
        cells += 1
        if ws.cell(r, j).value != k(cur[(s, d)]): mis.append((s, d))
    exp_tot = sum(k(cur[(s, d)]) for d in DEPTS); cells += 1
    if ws.cell(r, 7).value != exp_tot: mis.append((s, "合計"))
    exp_pre = k(sum((v for (ss, _), v in pre.items() if ss == s), Decimal(0))); cells += 1
    if ws.cell(r, 8).value != exp_pre: mis.append((s, "前月"))
tot_row = 5 + len(stores)
grand = sum(k(cur[(s, d)]) for s in stores for d in DEPTS); cells += 1
if ws.cell(tot_row, 7).value != grand: mis.append(("合計", "合計"))
# わな1：店が増えてもひな形の固定範囲（8店）のまま貼ると、9店目が合計から落ちる
tmp = Path(tempfile.mkdtemp()); t1 = tmp / "trap1.xlsx"
wb = openpyxl.load_workbook(ROOT / "template" / "monthly_template.xlsx"); w = wb["月次"]
for i, s in enumerate(stores):  # 9店目は合計行（13行目）の下ではなく、手で14行目に足したことにする
    r = 5 + i if i < 8 else 14
    w.cell(r, 1, s)
    for j, d in enumerate(DEPTS, 2): w.cell(r, j, k(cur[(s, d)]))
    w.cell(r, 7, f"=SUM(B{r}:F{r})")
wb.save(t1); g1 = recalc(t1).cell(13, 7).value
# わな2：CSV の「1,234」を文字のまま貼ると、SUM はその数字を飛ばす（ここでは食品の列だけ文字で貼った）
t2 = tmp / "trap2.xlsx"; wb = openpyxl.load_workbook(rep); w = wb["月次"]
for i, s in enumerate(stores): w.cell(5 + i, 2, f"{k(cur[(s, '食品')]):,}")
wb.save(t2); g2 = recalc(t2).cell(tot_row, 7).value
shutil.rmtree(tmp)
food = sum(k(cur[(s, "食品")]) for s in stores)
manual = {"CSV を開く・店で絞り込む（店ごと）": len(stores) * 2, "部門の合計を出す（店×部門）": len(stores) * len(DEPTS),
          "ひな形に貼る（店×部門＋前月）": len(stores) * (len(DEPTS) + 1), "対象月・店名を書く": 1 + len(stores)}
res = {"stores": len(stores), "cells_checked": cells, "mismatches": len(mis), "mismatch_list": mis,
       "formula_cells": n_formula, "formula_cells_without_cached_value": n_cached_none,
       "grand_total_k": grand, "trap1_fixed_range_total_k": g1, "trap1_missing_k": grand - g1, "trap1_missing_store": stores[-1],
       "trap1_missing_share": (grand - g1) / grand, "trap2_text_total_k": g2, "trap2_missing_k": grand - g2, "trap2_missing_share": (grand - g2) / grand,
       "food_total_k": food, "manual_steps_model": manual, "manual_steps_total": sum(manual.values())}
json.dump(res, open(RES / "checks.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(res, ensure_ascii=False, indent=1))
