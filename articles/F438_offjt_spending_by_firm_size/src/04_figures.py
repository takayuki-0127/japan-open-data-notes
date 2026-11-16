"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：厚生労働省「能力開発基本調査」、総務省「消費者物価指数」をもとに作成者が加工して作成"
SRC1 = "出典：厚生労働省「能力開発基本調査」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
w = pd.read_csv(R / "size_wide.csv", header=[0, 1], index_col=0)
U = ["s1000", "s300", "s100", "s50", "s30"]
LAB = {"s1000": "1,000人以上", "s300": "300〜999人", "s100": "100〜299人", "s50": "50〜99人", "s30": "30〜49人", "total": "総数"}
COL = {"s1000": C[0], "s300": "#6aa6e8", "s100": C[2], "s50": C[3], "s30": C[1], "total": INK}
yrs = w.index.values

# 図1 総数の1人あたり費用
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(yrs, w["per_worker"]["total"], color=C[0], lw=2.4, marker="o", ms=4, label="名目")
ax.plot(yrs, w["per_worker_real"]["total"], color=C[1], lw=1.6, marker="s", ms=3.5, ls="--", label="物価を除いた値（2024年度の物価）")
ax.axvspan(2020.5, 2021.5, color=GRID, alpha=0.7, lw=0)
ax.text(2021, 0.35, "2020年度\nの実績", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(yrs); ax.set_xticklabels([str(y) for y in yrs], fontsize=8.5)
ax.set_ylim(0, 2.8)
ax.set_ylabel("OFF-JT の費用 労働者1人あたり（万円）")
ax.set_xlabel("調査年度（費用はその前の年度の実績）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"総数：{m['pw_total_2009']:.1f}万円（2009年度調査）→{m['pw_total_2021']:.2f}万円（2021年度）→{m['pw_total_2025']:.1f}万円（2025年度）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, F / "fig1_total_per_worker.png", SRC, "注：OFF-JT に費用を支出した企業の平均。表の値は2021年度調査を除き0.1万円単位。")

# 図2 支出した企業の割合
sh = w["share_spend"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for u in U + ["total"]:
    ax.plot(yrs, sh[u], color=COL[u], lw=2.4 if u in ("s1000", "s30") else 1.4, marker="o", ms=3.5, ls="--" if u == "total" else "-", label=LAB[u])
ax.set_xticks(yrs); ax.set_xticklabels([str(y) for y in yrs], fontsize=8.5)
ax.set_ylim(0, 100)
ax.set_ylabel("OFF-JT に費用を支出した企業の割合（%）")
ax.set_xlabel("調査年度（その前の年度の実績）")
ax.legend(frameon=False, loc="lower left", fontsize=8.8, ncol=3)
style(ax)
ax.set_title(f"費用を出した企業の割合：2025年度調査は1,000人以上{m['share_s1000_2025']:.1f}%、30〜49人{m['share_s30_2025']:.1f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, F / "fig2_share_spend.png", SRC1)

# 図3 規模別の1人あたり費用（3回平均）
el = pd.read_csv(R / "early_late.csv").set_index("unit")
x = np.arange(len(U)); wd = 0.36
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(x - wd / 2, el.loc[U, "pw_early"], width=wd, color=C[5], label="2009〜2011年度調査の平均")
ax.bar(x + wd / 2, el.loc[U, "pw_late"], width=wd, color=C[0], label="2023〜2025年度調査の平均")
for i, u in enumerate(U):
    ax.text(i - wd / 2, el.loc[u, "pw_early"] + 0.04, f"{el.loc[u, 'pw_early']:.2f}", ha="center", fontsize=8.5, color=INK2)
    ax.text(i + wd / 2, el.loc[u, "pw_late"] + 0.04, f"{el.loc[u, 'pw_late']:.2f}", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(x); ax.set_xticklabels([LAB[u] for u in U])
ax.set_ylabel("OFF-JT の費用 労働者1人あたり（万円、名目）")
ax.set_ylim(0, 2.6)
ax.legend(frameon=False, loc="upper right", fontsize=9)
style(ax)
ax.set_title(f"費用を出した企業の中では、1人あたりの額は規模で大きく違わない（1,000人以上÷30〜49人＝{q['ratio_pw_late']:.2f}倍）", loc="left", fontsize=11)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.12)
save(fig, F / "fig3_per_worker_by_size.png", SRC1, "注：各期間の3回の調査の単純平均。費用を支出した企業の平均。")

# 図4 差の分け方
fig, ax = plt.subplots(figsize=(8.8, 4.6))
labels = ["2009〜2011年度調査", "2023〜2025年度調査"]
for i, t in enumerate(["early", "late"]):
    ls, lp = np.log(q[f"ratio_share_{t}"]), np.log(q[f"ratio_pw_{t}"])
    tot = ls + lp
    ax.barh(i, ls / tot * 100, color=C[1], height=0.5, label="支出した企業の割合の差" if i == 0 else None)
    ax.barh(i, lp / tot * 100, left=ls / tot * 100, color=C[0], height=0.5, label="1人あたりの額の差" if i == 0 else None)
    ax.text(ls / tot * 50, i, f"{ls / tot * 100:.0f}%\n（{q[f'ratio_share_{t}']:.2f}倍）", ha="center", va="center", color="white", fontsize=9.5)
    ax.text(ls / tot * 100 + lp / tot * 50, i, f"{lp / tot * 100:.0f}%", ha="center", va="center", color="white", fontsize=9)
    ax.text(101, i, f"全体の差 {q[f'ratio_flat_{t}']:.2f}倍", va="center", fontsize=9.5, color=INK)
ax.set_yticks([0, 1]); ax.set_yticklabels(labels)
ax.set_xlim(0, 125); ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("1,000人以上と30〜49人の差（対数）に占める割合（%）")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=2, fontsize=9)
ax.invert_yaxis()
ax.set_title("3回平均で比べると、規模の差の8〜9割は「費用を出す企業の割合」の差", loc="left", fontsize=12)
fig.subplots_adjust(left=0.21, right=0.97, top=0.89, bottom=0.3)
save(fig, F / "fig4_gap_decomposition.png", SRC1, f"注：全企業で平らにした目安＝1人あたりの額×支出した企業の割合。比をかけ算に分け、対数で割合を出した。全17回の平均どうしでは{q['pct_from_share_all']:.0f}%、2025年度調査だけでは{q['pct_from_share_2025']:.0f}%。")
