"""306 図3枚"""
import json
import matplotlib.pyplot as plt, numpy as np, pandas as pd
from matplotlib.patches import FancyBboxPatch
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

df = pd.read_csv(RES / "errors_by_scenario.csv"); byc = pd.read_csv(RES / "all_by_course.csv"); S = json.load(open(RES / "summary.json"))
one = df[~df.scenario.isin(["clean", "all"])].iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 5.6)); y = np.arange(len(one))
ax.barh(y + 0.2, one.formula_people_err, 0.4, color=ORANGE, label="関数をそのまま当てた場合（模した計算）")
ax.barh(y - 0.2, one.script_people_err, 0.4, color=BLUE, label="スクリプトの集計関数（Node で実行）")
for i, (a, b) in enumerate(zip(one.formula_people_err, one.script_people_err)):
    ax.text(a + 0.8, i + 0.2, str(a), va="center", fontsize=8.5, color=ORANGE); ax.text(b + 0.8, i - 0.2, str(b), va="center", fontsize=8.5, color=BLUE)
ax.set_yticks(y); ax.set_yticklabels(one.label, fontsize=9); ax.set_xlabel("人数の集計のずれ（5コースの差の絶対値の合計、人）")
ax.set_title(f"入力のゆれを1種類ずつ40行に入れたときの、人数のずれ\n関数は{S['edge_types']}種類中{S['formula_handles']}種類、スクリプトは{S['script_handles']}種類でずれが0", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=2)
save(fig, "a306_by_edge.png", y=-0.09)

fig, axs = plt.subplots(1, 2, figsize=(11, 4.4)); x = np.arange(len(byc))
for ax, m, t in zip(axs, ["app", "people"], ["申込件数", "人数"]):
    ax.bar(x - 0.27, byc[f"truth_{m}"], 0.27, color=GRAY, label="正解")
    ax.bar(x, byc[f"formula_{m}"], 0.27, color=ORANGE, label="関数（模した計算）")
    ax.bar(x + 0.27, byc[f"script_{m}"], 0.27, color=BLUE, label="スクリプト")
    ax.set_xticks(x); ax.set_xticklabels(byc.course, fontsize=8.5); ax.set_title(t, loc="left")
axs[0].legend(frameon=False, fontsize=8.5)
a = S["all"]; tt = S["all_totals"]
fig.suptitle(f"11種類のゆれを全部入れた申込シート：正解 {a['truth_app']}件・{a['truth_people']}人、関数 {tt['formula_app']}件・{tt['formula_people']}人、スクリプト {tt['script_app']}件・{tt['script_people']}人",
             x=0.01, ha="left", fontsize=11.5)
save(fig, "a306_all_by_course.png")

fig, ax = plt.subplots(figsize=(11, 4.6)); ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 4.6)
ax.set_title("スクリプトの流れと、試した範囲", loc="left")
def box(x, y, w, h, t, c):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=c, ec="none")); ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=9)
box(0.1, 2.6, 1.7, 1.0, "申込シート\n（6列）", "#e8e7e3")
box(2.3, 2.6, 2.0, 1.0, "1行ずつ整える\n空白・全角・人数・取消", LIGHT)
box(4.8, 2.6, 2.2, 1.0, "メール×コースで\nいちばん新しい行を残す", LIGHT)
box(7.5, 3.2, 1.9, 0.7, "集計シート", "#cfe8dc"); box(7.5, 2.2, 1.9, 0.7, "確認が要る行", "#f6c3ad")
for x0, x1, yy in [(1.85, 2.25, 3.1), (4.35, 4.75, 3.1), (7.05, 7.45, 3.5), (7.05, 7.45, 2.6)]:
    ax.annotate("", xy=(x1, yy), xytext=(x0, 3.1), arrowprops=dict(arrowstyle="->", color=GRAY))
ax.plot([2.3, 7.0], [2.35, 2.35], color=BLUE, lw=2); ax.text(4.65, 2.05, f"計算だけの関数：Node で試験 {S['tests_passed']}/{S['tests_total']} 件が通過", ha="center", fontsize=9, color=BLUE)
ax.plot([0.1, 1.8], [2.35, 2.35], color=ORANGE, lw=2); ax.plot([7.5, 9.4], [1.95, 1.95], color=ORANGE, lw=2)
ax.text(0.1, 1.45, "シートの読み書き・1時間ごとのトリガー・メニュー：\nGAS 本体では未検証（Node の小さな模型で読み書きだけ確かめた）", fontsize=9, color=ORANGE, va="top")
ax.text(9.6, 3.55, "コースごとの\n申込件数・人数", fontsize=8.5, va="center"); ax.text(9.6, 2.55, "人数が読めない行など\n（推し量らずに人に返す）", fontsize=8.5, va="center")
save(fig, "a306_flow.png", y=0.02)
print("ok")
