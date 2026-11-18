"""図4枚（PNG）。日付などのメタデータは入れない。数字は results から読む。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from common import ROOT, YEARS, SHOWN

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = {"kogyo": "#2a78d6", "shogyo": "#eb6834", "eisei": "#1baf7a", "kasei": "#eda100", "bunka": "#8a63d2", "nogyo": "#e87ba4"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校基本調査」（専修学校 設置者別学科別生徒数・年次統計、各年度5月1日時点）をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
NM = {"kogyo": "工業", "shogyo": "商業実務", "eisei": "衛生（調理・美容など）", "kasei": "服飾・家政", "bunka": "文化・教養", "nogyo": "農業"}


def finish(fig, ax, title, sub=None):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=22 if sub else 12)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=INK2)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def end_labels(ax, items, x, gap):
    items = sorted(items)
    pos = []
    for v, lab in items:
        p = v if not pos or v - pos[-1] >= gap else pos[-1] + gap
        pos.append(p)
        ax.text(x, p, lab, va="center", fontsize=9, color=INK)


# ---- 図1：分野別の生徒数 ----
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.09, right=0.76, top=0.85, bottom=0.12)
lab = []
for f in ["kogyo", "shogyo", "eisei", "kasei", "bunka", "nogyo"]:
    ys = [m["students"][f][str(y)] / 1e4 for y in YEARS]
    ax.plot(YEARS, ys, color=C[f], lw=2, marker="o", ms=5.5, mec="#fcfcfb", mew=1.3)
    lab.append([ys[-1], f"{NM[f]} {ys[-1]:.1f}万人"])
end_labels(ax, lab, 2026.2, 0.75)
ax.text(1990, m["students"]["kogyo"]["1990"] / 1e4 + 0.6, f"{m['students']['kogyo']['1990']/1e4:.1f}", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(YEARS); ax.set_xlim(1983, 2026); ax.set_ylim(0, 19.5)
ax.set_ylabel("生徒数（万人）")
finish(fig, ax, "文化・教養は2005年度から6分野で最も多く、服飾・家政は7割減った",
       "専修学校の専門課程（専門学校）の分野別の生徒数。取り上げない2分野は除く")
save(fig, "fig1_field_counts.png")

# ---- 図2：18歳人口1,000人あたり ----
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.09, right=0.76, top=0.85, bottom=0.12)
lab = []
for f in ["kogyo", "shogyo", "eisei", "kasei", "bunka"]:
    ys = [m["per_1000_cohort18"][f][str(y)] for y in YEARS]
    ax.plot(YEARS, ys, color=C[f], lw=2, marker="o", ms=5.5, mec="#fcfcfb", mew=1.3)
    lab.append([ys[-1], f"{NM[f]} {ys[-1]:.1f}"])
end_labels(ax, lab, 2026.2, 4.5)
ax.text(1995, m["per_1000_cohort18"]["kogyo"]["1995"] + 4, f"{m['per_1000_cohort18']['kogyo']['1995']:.1f}", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(YEARS); ax.set_xlim(1983, 2026); ax.set_ylim(0, 125)
ax.set_ylabel("18歳人口1,000人あたりの生徒数（人）")
finish(fig, ax, "18歳人口あたりで見ると、工業は1995年度と同じ水準に戻った",
       "分野別の生徒数を、18歳人口の目安（3年前の中学校等卒業者）1,000人あたりにした値")
save(fig, "fig2_per_cohort.png")

# ---- 図3：進学率 ----
er = m["senmon_entry_rate"]; ur = m["univ_entry_rate"]
yy = sorted(int(y) for y in er)
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.08, right=0.84, top=0.85, bottom=0.12)
ax.plot(yy, [er[str(y)] for y in yy], color="#2a78d6", lw=2, label="専門学校（専門課程）")
ax.plot(yy, [ur[str(y)] for y in yy], color="#b9b8b3", lw=2, label="大学（学部）")
for y in (1985, 1995, 2005, 2025):
    ax.plot(y, er[str(y)], "o", color="#2a78d6", ms=6, mec="#fcfcfb", mew=1.3)
    ax.text(y + (0.6 if y == 1985 else 0), er[str(y)] - 3.2, f"{er[str(y)]:.1f}%", ha="left" if y == 1985 else "center", fontsize=9, color=INK)
ax.text(2025.6, er["2025"], "専門学校", va="center", fontsize=10, color=INK)
ax.text(2025.6, ur["2025"], f"大学 {ur['2025']:.1f}%", va="center", fontsize=10, color=INK)
ax.set_ylim(0, 65); ax.set_xlim(1984, 2025)
ax.set_ylabel("進学率（%）")
finish(fig, ax, "専門学校に進む割合は、1985年の13.4%から2025年は23.1%",
       "入学者（浪人・社会人などを含む）÷3年前の中学校等卒業者。大学は参考")
save(fig, "fig3_entry_rate.png")

# ---- 図4：学科別の増減（2010→2025年度）----
items = q["top_decrease"][::-1][::-1] + q["top_increase"][::-1]
items = sorted(q["top_decrease"] + q["top_increase"], key=lambda d: d["diff"])
fig, ax = plt.subplots(figsize=(8.6, 5.0)); fig.subplots_adjust(left=0.27, right=0.95, top=0.85, bottom=0.16)
ys = range(len(items))
ax.barh(list(ys), [d["diff"] / 1e4 for d in items], color=["#2a78d6" if d["diff"] > 0 else "#b9b8b3" for d in items], height=0.62)
ax.set_yticks(list(ys)); ax.set_yticklabels([f"{d['sub']}（{d['field']}）" for d in items])
for i, d in enumerate(items):
    x = d["diff"] / 1e4 + 0.04 if d["diff"] > 0 else 0.04
    ax.text(x, i, f"{d['diff']/1e4:+.2f}万（{d['2010']:,}→{d['2025']:,}人）", va="center", ha="left", fontsize=8.5, color=INK)
ax.axvline(0, color="#52514e", lw=0.8)
ax.set_xlim(-0.6, 1.8); ax.set_xlabel("2010→2025年度の増減（万人）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("増えたのは情報処理・商業・動物の学科", loc="left", fontsize=12.5, color=INK, pad=22)
ax.text(0, 1.02, "専門課程の学科別の増減。増えた5学科と減った5学科（各分野の「その他」は除く）", transform=ax.transAxes, fontsize=9, color=INK2)
fig.text(0.01, 0.012, SRC, fontsize=7.6, color=INK2)
save(fig, "fig4_subfields.png")
