"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校基本調査」（e-Stat）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
tb = pd.read_csv(R / "totals_by_year.csv", index_col=0)
lt = pd.read_csv(R / "requestion_long_rates.csv", index_col=0)
fc = pd.read_csv(R / "field_change.csv")
pe = pd.read_csv(R / "requestion_prof_edu.csv", index_col=0)

# ---- 図1：修了者の長い流れ（人数） ------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
q = lt[lt.index >= 1960]
ax.plot(q.index, q.master_grad / 1e4, color=C[0], lw=2)
ax.plot(q.index, q.doctor_grad / 1e4, color=C[1], lw=2)
ax.text(2025.5, q.master_grad.iloc[-1] / 1e4, f"修士の修了者\n{q.master_grad.iloc[-1]/1e4:.1f}万人", fontsize=9, color=INK, va="center")
ax.text(2025.5, q.doctor_grad.iloc[-1] / 1e4, f"博士の修了者\n{q.doctor_grad.iloc[-1]/1e4:.1f}万人", fontsize=9, color=INK, va="center")
for y in [1990, 2012]:
    v = float(lt.loc[y, "master_grad"]) / 1e4
    ax.plot([y], [v], "o", color=C[0], ms=7, mec="#fcfcfb", mew=2)
    ax.text(y, v + 0.35, f"{y}年 {v:.1f}万人", ha="center", fontsize=9, color=INK)
ax.set_xlim(1960, 2033); ax.set_ylim(0, 9.5)
ax.set_ylabel("各年3月の修了者（万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("修士の修了者は1990年代に3倍になり、2012年ごろから横ばい", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：修士課程・博士課程の卒業者（各年3月）。専門職学位課程は含まない。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_graduates_long.png")

# ---- 図2：進学の割合（2009〜2025年度） ------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(tb.index, tb.doctor_rate_pct, color=C[1], lw=2, marker="o", ms=4)
ax.plot(tb.index, tb.master_rate_pct, color=C[0], lw=2, marker="o", ms=4)
ax.text(2025.4, tb.doctor_rate_pct.iloc[-1], f"博士の入学者\n÷ 同じ年の修士修了者\n{tb.doctor_rate_pct.iloc[-1]:.1f}%", fontsize=8.8, color=INK, va="center")
ax.text(2025.4, tb.master_rate_pct.iloc[-1], f"修士の入学者\n÷ 同じ年の学部卒業者\n{tb.master_rate_pct.iloc[-1]:.1f}%", fontsize=8.8, color=INK, va="center")
for col, y in [("master_rate_pct", 2010), ("master_rate_pct", 2020), ("doctor_rate_pct", 2010), ("doctor_rate_pct", 2012)]:
    v = float(tb.loc[y, col])
    ax.text(y, v + 0.6, f"{v:.1f}%", ha="center", fontsize=8.8, color=INK)
ax.set_xlim(2008.5, 2029.5); ax.set_ylim(0, 27)
ax.set_xticks(range(2009, 2026, 2))
ax.set_ylabel("割合（%）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"修士への割合は2010年度の{tb.loc[2010,'master_rate_pct']:.1f}%から{main['master_rate_min_year']}年度の{main['master_rate_min']:.1f}%へ下がり、2025年度は{tb.loc[2025,'master_rate_pct']:.1f}%", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：入学者には社会人・留学生・前の年の卒業者も含むので、割合は目安。卒業者は各年3月。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_rates.png")

# ---- 図3：分野別の増減（2010→2025年度、人） ------------------------------------------------
order = ["人文科学", "社会科学", "理学", "工学", "農学", "保健", "家政", "教育", "芸術", "その他"]
fig, axes = plt.subplots(1, 2, figsize=(10.0, 5.0), sharey=True)
for ax, course, c in [(axes[0], "修士", C[0]), (axes[1], "博士", C[1])]:
    z = fc[fc.course == course].set_index("field").loc[order]
    yy = np.arange(len(order))[::-1]
    ax.barh(yy, z["diff"], height=0.6, color=c)
    lim = 7000 if course == "修士" else 700
    for y_, (f, r) in zip(yy, z.iterrows()):
        ha = "left" if r["diff"] >= 0 else "right"
        off = lim * 0.02 * (1 if r["diff"] >= 0 else -1)
        ax.text(r["diff"] + off, y_, f"{r['diff']:+,.0f}（{r['ratio']*100:.0f}%）", va="center", ha=ha, fontsize=8.3, color=INK)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlim(-lim * 1.25, lim * 1.35)
    key = "master" if course == "修士" else "doctor"
    ax.set_title(f"{course}課程（{tb.loc[2010, key]:,.0f}→{tb.loc[2025, key]:,.0f}人）", loc="left", fontsize=11)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_xlabel("入学者の増減（人）")
axes[0].set_yticks(np.arange(len(order))[::-1]); axes[0].set_yticklabels(order)
fig.suptitle("2010→2025年度：修士は「その他」が増え教育が減った。博士は人文・社会が3割減", x=0.01, ha="left", fontsize=12)
fig.text(0.01, 0.01, "注：括弧の中は2025年度÷2010年度。商船は省いた。専攻分野は大学の申告による。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.17, wspace=0.08)
save(fig, "fig3_field_change.png")

# ---- 図4：専門職と教育の分野 ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for col, lab, c in [("master_edu", "修士課程の教育分野", C[0]), ("teach", "教職大学院（専門職）", C[2]), ("law", "法科大学院（専門職）", C[1]), ("other_prof", "その他の専門職", C[3])]:
    s = pe[col].dropna()
    ax.plot(s.index, s / 1e3, color=c, lw=2, label=f"{lab}：{int(s.index[0])}年度 {s.iloc[0]:,.0f} → 2025年度 {s.iloc[-1]:,.0f}")
ax.legend(loc="upper left", frameon=False, fontsize=8.8, ncol=1, bbox_to_anchor=(0.0, 1.0))
ax.set_xlim(2008.5, 2025.5); ax.set_ylim(0, 7.5)
ax.set_xticks(range(2009, 2026, 2))
ax.set_ylabel("入学者（千人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("法科大学院は半分に。教職大学院は増えたが、修士の教育分野の減りの半分弱", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：その他の専門職＝専門職学位課程の合計 − 法科大学院 − 教職大学院。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_professional_education.png")
print("figures ok")
