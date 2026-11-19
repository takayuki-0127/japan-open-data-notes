"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = pathlib.Path(__file__).resolve().parent.parent
R = BASE / "results"; F = BASE / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#8a5cc7"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校基本調査」、厚生労働省「一般職業紹介状況（職業安定業務統計）」をもとに作成者が加工して作成"
META = {"Software": None}


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
s = pd.read_csv(R / "series.csv", index_col="grad_year")
rob = pd.read_csv(R / "robustness.csv")
g = pd.read_csv(R / "requestion_gap.csv", index_col="grad_year")

# 図1 就職率と前年度の有効求人倍率（上下2段）
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.4, 5.8), sharex=True, gridspec_kw={"height_ratios": [1.4, 1]})
a1.plot(s.index, s["univ_t"], color=C[0], lw=2.2)
for y, dy in [(2003, -9), (2019, 6), (1991, 6)]:
    a1.annotate(f"{y}年 {s.loc[y, 'univ_t']:.1f}%", (y, s.loc[y, "univ_t"]), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=9, color=C[0])
a1.set_ylabel("大学（学部）の就職率（%）"); a1.set_ylim(50, 90)
a1.grid(axis="y", color=GRID, lw=0.8)
a2.plot(s.index, s["yuko_fy_lag1"], color=C[1], lw=2.2)
a2.set_ylabel("前年度の求人倍率（倍）"); a2.set_ylim(0, 2)
a2.grid(axis="y", color=GRID, lw=0.8); a2.set_xlabel("卒業した年（3月）")
a1.set_title("就職率は前年度の求人倍率と一緒に動き、2003年に55.1%まで下がった", loc="left", fontsize=12.5, color=INK, pad=12)
fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.91, bottom=0.12, hspace=0.12)
save(fig, "fig1_rate_and_openings.png")

# 図2 前の年からの変化どうしの散布図
d = s[["univ_t", "yuko_fy_lag1"]].diff().dropna()
fig, ax = plt.subplots(figsize=(8.4, 5.2))
for (a, b), c, lab in [((1965, 1990), C[2], "1965〜1990年"), ((1991, 2010), C[1], "1991〜2010年"), ((2011, 2025), C[0], "2011〜2025年")]:
    dd = d.loc[a:b]
    ax.scatter(dd["yuko_fy_lag1"], dd["univ_t"], s=28, color=c, label=lab, alpha=0.9, zorder=3)
xs = np.linspace(d["yuko_fy_lag1"].min(), d["yuko_fy_lag1"].max(), 10)
bb = m["H2"]["b_per_0.1"] * 10
cc = d["univ_t"].mean() - bb * d["yuko_fy_lag1"].mean()
ax.plot(xs, cc + bb * xs, color=INK2, lw=1.2, ls="--", label=f"全期間の直線（0.1あたり {m['H2']['b_per_0.1']:.2f}ポイント）")
for y, off in ((2010, (6, -4)), (2021, (-8, 8))):
    ax.annotate(f"{y}年", (d.loc[y, "yuko_fy_lag1"], d.loc[y, "univ_t"]), xytext=off, textcoords="offset points", fontsize=9, color=INK2, ha="right" if off[0] < 0 else "left")
ax.axhline(0, color=GRID, lw=1); ax.axvline(0, color=GRID, lw=1)
ax.set_xlabel("前年度の有効求人倍率の変化（倍）"); ax.set_ylabel("就職率の前の年からの変化（ポイント）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
finish(fig, ax, "倍率が0.1上がった年は、就職率も平均0.83ポイント上がった")
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.14)
save(fig, "fig2_change_scatter.png")

# 図3 年の合わせ方・期間で係数がどう変わるか
rows = [("前年度の有効求人倍率（主）", m["H2"]), ("前年（暦年）の有効求人倍率", rob.iloc[3].to_dict()),
        ("前年度の新規求人倍率", rob.iloc[1].to_dict()), ("卒業した年の年度の有効求人倍率", rob.iloc[2].to_dict()),
        ("期間 1964〜1990年", m["by_period_diff"]["1964-1990"]), ("期間 1991〜2010年", m["by_period_diff"]["1991-2010"]),
        ("期間 2011〜2025年", m["by_period_diff"]["2011-2025"])]
fig, ax = plt.subplots(figsize=(8.4, 4.9))
yy = np.arange(len(rows))[::-1]
for yv, (lab, r) in zip(yy, rows):
    col = C[1] if "卒業した年" in lab else (C[2] if lab.startswith("期間") else C[0])
    ax.plot([r["ci_lo_per_0.1"], r["ci_hi_per_0.1"]], [yv, yv], color=col, lw=2.2)
    ax.plot(r["b_per_0.1"], yv, "o", color=col, ms=7)
    ax.text(r["ci_hi_per_0.1"] + 0.05, yv, f"{r['b_per_0.1']:.2f}", va="center", fontsize=9.3, color=col)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy, [r[0] for r in rows], fontsize=9.5)
ax.set_xlabel("倍率0.1あたりの就職率の変化（ポイント、前の年からの変化どうし、95%区間）")
ax.set_xlim(-0.4, 2.5)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("効くのは「卒業の前の年度」の倍率。1991〜2010年は動き方が大きい", loc="left", fontsize=12.5, color=INK, pad=12)
fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.3, right=0.97, top=0.9, bottom=0.17)
save(fig, "fig3_coefficients.png")

# 図4 1964〜1999年の関係を延ばした値と実際
fig, ax = plt.subplots(figsize=(8.4, 4.9))
ax.plot(g.index, g["univ_t"], color=C[0], lw=2.2, label="実際の就職率")
ax.plot(g.index, g["pred_from_1964_1999"], color=C[1], lw=1.8, ls="--", label="1964〜1999年の関係から見込む値（倍率だけで）")
ax.fill_between(g.loc[2000:].index, g.loc[2000:, "univ_t"], g.loc[2000:, "pred_from_1964_1999"], color=C[1], alpha=0.12)
mg = q["mean_gap_by_period"]
for (a, b), x in [(("2000", "2009"), 2004.5), (("2010", "2019"), 2014.5), (("2020", "2025"), 2022.5)]:
    ax.text(x, 52.5, f"{a}〜{b[-2:]}年\n平均 {mg[f'{a}-{b}']:+.1f}", ha="center", fontsize=9, color=C[1])
ax.set_ylim(50, 92); ax.set_ylabel("大学（学部）卒業者のうち就職した人（%）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
finish(fig, ax, "倍率で見込むより低い分は、2000〜09年の平均 −13.8 から2020〜25年は −2.8 ポイントに")
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.1)
save(fig, "fig4_shortfall.png")
print("ok")
