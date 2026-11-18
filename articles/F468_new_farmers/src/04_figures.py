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
for cand in ["Noto Sans CJK JP", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
INK2, GRID = "#52514e", "#e4e3df"
C = {"jiei": "#6b8e3a", "koyo": "#2f6db5", "sannyu": "#e08a2e", "total": "#333333"}
L = {"jiei": "新規自営農業就農者（家の農業）", "koyo": "新規雇用就農者（法人などに雇われる）", "sannyu": "新規参入者（自分で経営を始める）", "total": "計"}
META = {"Software": None}
SRC = "出典：農林水産省「新規就農者調査」（e-Stat）をもとに作成者が加工して作成"
S = pd.read_csv(R / "national_series.csv").set_index("year")
M = json.load(open(R / "main.json", encoding="utf-8"))
END, YP = M["end"], M["y49_peak"]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：形別の人数
fig, ax = plt.subplots(figsize=(9.0, 4.9))
for f in ["total", "jiei", "koyo", "sannyu"]:
    s = S[f"all_{f}"] / 1e4
    ax.plot(s.index, s.values, color=C[f], lw=2.4 if f == "total" else 1.9, marker="o", ms=3, label=L[f])
    ax.text(END + 0.3, s[END], f"{s[END]:.2f}", color=C[f], fontsize=9, va="center")
    ax.text(2006 - 0.3, s[2006], f"{s[2006]:.2f}", color=C[f], fontsize=9, va="center", ha="right")
ax.axvline(2013.5, color=INK2, lw=0.8, ls=":")
ax.text(2013.6, 8.3, "2014年から新規参入者に\n共同経営者を含む", fontsize=8.5, color=INK2, va="top")
ax.set_xlim(2004.5, 2026.5); ax.set_ylim(0, 8.8); ax.set_ylabel("万人")
ax.set_xticks(range(2006, 2026, 2))
ax.set_title("新規就農者は8.1万人から4.3万人へ減った。雇われて始める人は増えた", loc="left", fontsize=12)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=8.8, loc="upper right")
fig.subplots_adjust(bottom=0.14, top=0.9); foot(fig, "各年2月1日〜翌年1月31日に就農した人")
save(fig, "fig1_by_form.png")

# 図2：49歳以下の人数（形別の積み上げ）と、49歳以下のうち雇用就農の割合
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9.0, 5.8), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
yrs = S.loc[2007:].index
bottom = np.zeros(len(yrs))
for f in ["jiei", "koyo", "sannyu"]:
    v = S.loc[2007:, f"le49_{f}"].to_numpy() / 1e4
    ax.bar(yrs, v, bottom=bottom, color=C[f], label=L[f], width=0.72)
    bottom += v
for y in [2007, 2010, YP, END]:
    ax.text(y, bottom[list(yrs).index(y)] + 0.05, f"{S.loc[y, 'le49_total'] / 1e4:.2f}", ha="center", fontsize=8.8)
ax.set_ylim(0, 3.0); ax.set_ylabel("49歳以下（万人）")
ax.set_title("49歳以下は2015年の2.30万人から1.44万人へ。半分近くが雇われて始める人に", loc="left", fontsize=11.5)
ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
sk = 100 * S.loc[2007:, "le49_koyo"] / S.loc[2007:, "le49_total"]
ax2.plot(yrs, sk, color=C["koyo"], lw=1.9, marker="o", ms=3)
for y in [2007, 2010, YP, END]:
    ax2.text(y, sk[y] + 4, f"{sk[y]:.1f}%", ha="center", fontsize=8.8, color=C["koyo"])
ax2.set_ylim(0, 65); ax2.set_ylabel("雇用の割合（%）", fontsize=9.5); ax2.grid(axis="y", color=GRID); ax2.set_axisbelow(True)
ax2.set_xticks(range(2007, 2026, 2))
fig.subplots_adjust(bottom=0.12, top=0.93, hspace=0.12); foot(fig, "下の図は49歳以下のうち新規雇用就農者の割合。2007〜2009年の49歳以下は「39歳以下」と「40〜49歳」の和")
save(fig, "fig2_under49.png")

# 図3：年齢の構成（計）
A = pd.read_csv(R / "age_total.csv").set_index("year").loc[2007:]
sh = A.div(A.sum(1), axis=0) * 100
cols = ["#1f4e79", "#4f81bd", "#9bbb59", "#f2c14e", "#c0504d"]
fig, ax = plt.subplots(figsize=(9.0, 4.9))
ax.stackplot(sh.index, sh.T.values, labels=sh.columns, colors=cols, alpha=0.92)
for y in [2007, END]:
    acc = 0
    for c, v in zip(sh.columns, sh.loc[y]):
        ax.text(y + (0.25 if y == END else -0.25), acc + v / 2, f"{v:.0f}%", ha="left" if y == END else "right", va="center", fontsize=8.5)
        acc += v
ax.set_xlim(2005.6, 2026.6); ax.set_ylim(0, 100); ax.set_ylabel("新規就農者の年齢の構成（%）")
ax.set_xticks(range(2007, 2026, 2))
ax.set_title("新規就農者の4割は65歳以上。2007年の2割強から上がった", loc="left", fontsize=12)
h, l = ax.get_legend_handles_labels()
ax.legend(h[::-1], l[::-1], frameon=False, fontsize=8.8, loc="upper left", bbox_to_anchor=(1.0, 1.0))
fig.subplots_adjust(bottom=0.14, top=0.9, right=0.82); foot(fig, "年齢不詳（2023〜2025年に10〜30人）は除いた")
save(fig, "fig3_age.png")

# 図4：49歳以下の減少の内訳（形×年齢）
Q = pd.read_csv(R / "requestion_le49_form_age.csv")
Q["lab"] = Q.form.str.replace("新規", "") + "・" + Q.age
Q = Q.iloc[::-1].reset_index(drop=True)
fm = {"新規自営農業就農者": "jiei", "新規雇用就農者": "koyo", "新規参入者": "sannyu"}
fig, ax = plt.subplots(figsize=(9.0, 4.8))
for i, (f, a, v) in enumerate(zip(Q.form, Q.age, Q.change)):
    ax.barh(i, v, color=C[fm[f]], alpha=0.95 if a.startswith("15") else 0.55)
ax.set_yticks(range(len(Q)), Q.lab)
for i, (v, a) in enumerate(zip(Q.change, Q.age)):
    ax.text(v + (60 if v >= 0 else -60), i, f"{v:+,.0f}人", va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-6200, 1200)
ax.set_xlabel(f"{YP}→{END}年の増減（人）")
ax.set_title(f"49歳以下は{-M['splits'][2]['change']:,.0f}人減った。うち{-Q.loc[Q.lab.str.startswith('自営') & Q.age.eq('15〜39歳'), 'change'].iloc[0]:,.0f}人は家の農業に就く15〜39歳", loc="left", fontsize=11.5)
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
fig.subplots_adjust(left=0.27, bottom=0.17, top=0.9)
foot(fig, "形×年齢の人数の差。足すと49歳以下全体の増減に一致")
save(fig, "fig4_le49_change.png")
