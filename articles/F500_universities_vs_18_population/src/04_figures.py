"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from common import ROOT

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校基本調査」年次統計（各年5月1日時点）をもとに作成者が加工して作成"
META = {"Software": None}
comma = ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
by = pd.read_csv(R / "by_year.csv", index_col="year").loc[1985:2025]
ps = pd.read_csv(R / "per_school.csv", index_col="year").loc[1985:2025]

# ---- 図1：1992年＝100の指数 ----
fig, ax = plt.subplots(figsize=(8.8, 5.2))
series = [("univ_idx", "大学の数", C[0]), ("ent_univ_idx", "大学（学部）の入学者", C[2]),
          ("pop18_idx", "18歳人口（3年前の中学校等卒業者）", C[1])]
for c, lab, col in series:
    ax.plot(by.index, by[c], color=col, lw=2.3, label=lab)
    ax.text(2025.6, by[c].iloc[-1], f"{by[c].iloc[-1]:.0f}", va="center", fontsize=9.5, color=col)
ax.axhline(100, color=INK2, lw=0.8, ls=":")
ax.axvline(1992, color=INK2, lw=0.8, ls=":")
ax.text(1992.4, 40, "1992年（18歳人口が最多）", fontsize=8.8, color=INK2)
ax.set_ylim(35, 175)
ax.set_xlim(1985, 2028)
ax.set_xlabel("年")
ax.set_ylabel("1992年を100とした値")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "18歳人口は半分近くに減ったが、大学は1.55倍、入学者は1.19倍になった")
fig.subplots_adjust(left=0.09, right=0.95, top=0.89, bottom=0.15)
save(fig, "fig1_index_1992.png")

# ---- 図2：大学と短大の数（積み上げ） ----
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.stackplot(by.index, by.univ, by.jc, colors=[C[0], C[3]], alpha=0.85, labels=["大学", "短期大学"])
ax.plot(by.index, by.univ_plus_jc, color=INK, lw=1.0)
for y in [1992, 2025]:
    ax.annotate(f"{y}年　計 {int(by.at[y, 'univ_plus_jc']):,}\n大学 {int(by.at[y, 'univ'])}・短大 {int(by.at[y, 'jc'])}",
                (y, by.at[y, "univ_plus_jc"]), xytext=(0, 12), textcoords="offset points", ha="center", fontsize=8.8, color=INK)
ax.set_ylim(0, 1600)
ax.set_xlabel("年")
ax.set_ylabel("学校数（校）")
ax.yaxis.set_major_formatter(comma)
ax.legend(frameon=False, loc="upper center", ncol=2)
finish(fig, ax, "大学と短大を合わせた数は、1992年と2025年でほぼ同じ（1,114校→1,104校）")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig2_univ_jc_schools.png")

# ---- 図3：入学者の変化の分解 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
labs = ["大学（学部）", "大学＋短大"]
ds = [m["decomp_univ"], m["decomp_both"]]
x = range(len(labs))
w = 0.26
for i, (key, lab, col) in enumerate([("pop_effect", "18歳人口が減った効果", C[1]), ("rate_effect", "進学率が上がった効果", C[0]),
                                       ("change", "実際の変化", INK2)]):
    vals = [d[key] / 1e4 for d in ds]
    xs = [xx + (i - 1) * w for xx in x]
    ax.bar(xs, vals, width=w, color=col, label=lab)
    for xx, v in zip(xs, vals):
        ax.text(xx, v + (1.2 if v >= 0 else -1.2), f"{v:+.1f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=9.5, color=INK)
ax.axhline(0, color=INK2, lw=0.9)
ax.set_xticks(list(x)); ax.set_xticklabels(labs)
ax.set_ylim(-60, 65)
ax.set_ylabel("入学者の増減（万人、1992→2025年）")
ax.legend(frameon=False, loc="upper right", fontsize=9.5)
finish(fig, ax, "大学の入学者が増えたのは、進学率の上がり方が人口の減り方を上回ったから")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.13)
save(fig, "fig3_entrant_decomposition.png")

# ---- 図4：1校あたりの在籍者（設置者別） ----
fig, ax = plt.subplots(figsize=(8.8, 5.2))
for c, lab, col in [("students_per_univ_national", "国立", C[0]), ("students_per_univ_public", "公立", C[2]),
                    ("students_per_univ_private", "私立", C[1]), ("students_per_univ_total", "全体", INK2)]:
    ax.plot(ps.index, ps[c], color=col, lw=2.3 if lab != "全体" else 1.6, ls="-" if lab != "全体" else "--", label=lab)
    off = {"全体": 170, "私立": -170}.get(lab, 0)
    ax.text(2025.6, ps[c].iloc[-1] + off, f"{ps[c].iloc[-1]:,.0f}", va="center", fontsize=9.3, color=col)
ax.set_xlim(1985, 2029)
ax.set_ylim(0, 8000)
ax.set_xlabel("年")
ax.set_ylabel("1校あたりの在籍者（人、大学院などを含む）")
ax.yaxis.set_major_formatter(comma)
ax.legend(frameon=False, loc="upper left", ncol=4)
finish(fig, ax, "私立の1校あたりの学生は1993年の約4,500人から約3,500人に減った")
fig.subplots_adjust(left=0.1, right=0.94, top=0.89, bottom=0.15)
save(fig, "fig4_students_per_university.png")
