import json, numpy as np, matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK
cases = json.load(open(RES / "cases.json")); sel = json.load(open(RES / "selectivity.json"))
# 図1 直す前と後の時間
fig, ax = plt.subplots(figsize=(8.2, 4.2))
names = [c["case"] for c in cases][::-1]; y = np.arange(len(names))
b = [c["before"]["ms"] for c in cases][::-1]; a = [c["after"]["ms"] for c in cases][::-1]
ax.barh(y + 0.2, b, 0.38, color=GRAY, label="直す前"); ax.barh(y - 0.2, a, 0.38, color=BLUE, label="直した後")
for i, c in enumerate(cases[::-1]):
    ax.text(max(c["before"]["ms"], c["after"]["ms"]) * 1.25, i, f"{c['time_ratio']:g}倍速い", va="center", fontsize=10, color=INK)
ax.set_xscale("log"); ax.set_yticks(y); ax.set_yticklabels(names); ax.set_xlabel("1回の実行時間（ミリ秒、対数目盛、5回の中央値）", labelpad=2)
ax.set_xlim(0.005, 3000); ax.legend(loc="upper center", bbox_to_anchor=(0.5,-0.16), ncol=2, frameon=False)
ax.set_title("同じ答えのクエリでも、書き方と索引で時間は数倍〜数千倍変わった（架空の注文100万行）", loc="left", fontsize=11.5)
save(fig, "a294_cases.png", y=-0.1)
# 図2 実行プランの読み方（表）
fig, ax = plt.subplots(figsize=(10.5, 3.4)); ax.axis("off"); fig.subplots_adjust(left=0.01, right=0.99)
rows = [[c["case"], c["before"]["plan"].replace("SEARCH orders USING ", "SEARCH ").replace(" (", "\n("), c["after"]["plan"].replace("SEARCH orders USING ", "SEARCH ").replace(" (", "\n(")] for c in cases]
t = ax.table(cellText=rows, colLabels=["場面", "直す前の実行プラン", "直した後の実行プラン"], loc="center", cellLoc="left", colWidths=[0.25, 0.375, 0.375])
t.auto_set_font_size(False); t.set_fontsize(8.6); t.scale(1, 2.35)
for (r, c_), cell in t.get_celld().items():
    cell.set_edgecolor("#dddddd")
    if r == 0: cell.set_facecolor("#eef3fb"); cell.set_text_props(weight="bold")
ax.set_title("実行プランで見るのは「SCAN（全部読む）か SEARCH（索引で絞る）か」と「どの列で絞れているか」（SQLite の EXPLAIN QUERY PLAN）", loc="left", fontsize=10)
save(fig, "a294_plans.png", y=0.02)
# 図3 当てはまる行の割合と、索引・全件読み
fig, ax = plt.subplots(figsize=(8, 4.2))
p = [s["pct"] for s in sel]
ax.plot(p, [s["index_ms"] for s in sel], "-o", color=ORANGE, label="索引をたどる")
ax.plot(p, [s["scan_ms"] for s in sel], "-o", color=BLUE, label="全部読む")
ax.set_xscale("log"); ax.set_xticks(p); ax.set_xticklabels([f"{x}%" for x in p])
ax.set_xlabel("条件に当てはまる行の割合"); ax.set_ylabel("実行時間（ミリ秒）"); ax.legend(frameon=False)
ax.set_title("索引が速いのは、当てはまる行が数%までのとき。それより多いと全部読むほうが速かった", loc="left", fontsize=11.5)
save(fig, "a294_selectivity.png")
