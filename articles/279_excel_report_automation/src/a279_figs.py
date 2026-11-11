"""図：出来上がった表・手作業の手順の数・3つのわなの大きさ"""
import json, shutil, subprocess, tempfile
from pathlib import Path
import openpyxl, matplotlib.pyplot as plt
from common import ROOT, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
c = json.load(open(RES / "checks.json"))
d = Path(tempfile.mkdtemp())
subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(d), str(ROOT / "output" / "report_2025-10.xlsx")], capture_output=True, timeout=180)
ws = openpyxl.load_workbook(d / "report_2025-10.xlsx", data_only=True)["月次"]; shutil.rmtree(d)
rows = []
for r in range(4, 5 + c["stores"] + 1):
    v = [ws.cell(r, j).value for j in range(1, 10)]
    if r > 4:
        v = [v[0]] + [f"{x:,}" if isinstance(x, (int, float)) else "" for x in v[1:8]] + [f"{v[8]*100:+.1f}%" if isinstance(v[8], (int, float)) else "－"]
    rows.append(v)
fig, ax = plt.subplots(figsize=(10, 4.2)); ax.set_axis_off()
t = ax.table(cellText=rows[1:], colLabels=rows[0], loc="center", cellLoc="right", colLoc="center")
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.35)
for (i, j), cell in t.get_celld().items():
    cell.set_edgecolor("#d0cfca")
    if i == 0: cell.set_facecolor(BLUE); cell.get_text().set_color("white")
    if i == len(rows) - 1: cell.get_text().set_weight("bold")
ax.set_title("出来上がった月次レポート（2025年10月、千円）：S09 は今月開いた店で、行は自動で1つ増えた", fontsize=11.5)
save(fig, "a279_report.png")
# 図2：手作業の手順の数（手順書に書いた場合）
m = c["manual_steps_model"]
fig, ax = plt.subplots(figsize=(8, 3.6))
ks = list(m); vs = [m[k] for k in ks]
ax.barh(range(len(ks)), vs, color=LIGHT); ax.set_yticks(range(len(ks)), ks); ax.invert_yaxis()
for i, v in enumerate(vs): ax.text(v + 1, i, str(v), va="center", fontsize=10)
ax.set_xlabel("手作業の1回の操作の数（9店×5部門の月）")
ax.set_title(f"手で作ると毎月 約{c['manual_steps_total']}回の操作。自動では1回の実行と、{c['cells_checked']}セルの照合（ずれ{c['mismatches']}）")
save(fig, "a279_manual_steps.png")
# 図3：3つのわな
g = c["grand_total_k"]
fig, ax = plt.subplots(figsize=(8.6, 3.8))
labels = ["正しい合計", "わな1：ひな形の範囲が\n8店のまま（9店目を足し忘れ）", "わな2：「1,234」を\n文字のまま貼った（食品の列）"]
vals = [g, c["trap1_fixed_range_total_k"], c["trap2_text_total_k"]]
cols = [BLUE, ORANGE, ORANGE]
ax.barh(range(3), [v / 1000 for v in vals], color=cols); ax.set_yticks(range(3), labels); ax.invert_yaxis()
for i, v in enumerate(vals):
    s = f"{v/1000:,.1f}百万円" + ("" if i == 0 else f"（{(v-g)/g*100:+.0f}%、エラーは出ない）")
    ax.text(v / 1000 + 5, i, s, va="center", fontsize=9.5)
ax.set_xlim(0, g / 1000 * 1.6); ax.set_xlabel("レポートの総合計（百万円）")
ax.set_title(f"わな3：openpyxl で保存した式 {c['formula_cells']}個は、計算し直すまで値が空（{c['formula_cells_without_cached_value']}個）", fontsize=11)
save(fig, "a279_traps.png")
