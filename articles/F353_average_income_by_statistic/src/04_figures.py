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
SRC = "出典：国税庁「民間給与実態統計調査」、厚生労働省「毎月勤労統計調査」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
df = pd.read_csv(R / "definitions_2025.csv")
yrs = pd.read_csv(R / "requestion_mean_median_years.csv")
br = pd.read_csv(ROOT / "data" / "nta_brackets_2025.csv")

# ---- 図1：定義ごとの「年収」 -----------------------------------------------------------------
d = df.sort_values("annual_man").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9.6, 6.0))
yy = np.arange(len(d))
cols = [C[0] if s.startswith("国税庁") else C[1] for s in d.definition]
ax.barh(yy, d.annual_man, height=0.62, color=cols)
for y_, v in zip(yy, d.annual_man):
    ax.text(v + 6, y_, f"{v:.0f}万円", va="center", fontsize=9, color=INK)
ax.set_yticks(yy); ax.set_yticklabels([s.replace("：", "\n") if len(s) > 26 else s for s in d.definition], fontsize=8.6)
ax.set_xlim(0, 700)
ax.set_xlabel("2025年の年収（万円）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C[0], label="国税庁「民間給与実態統計調査」"), Patch(color=C[1], label="厚生労働省「毎月勤労統計調査」（月額×12）")], loc="lower right", frameon=False, fontsize=9)
ax.set_title(f"同じ2025年の「平均年収」でも、定義によって{d.annual_man.min():.0f}万〜{d.annual_man.max():.0f}万円", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：税・社会保険料を引く前の額。毎月勤労は事業所規模別の常用労働者1人あたりの月額の年平均×12。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.36, right=0.97, top=0.93, bottom=0.12)
save(fig, "fig1_definitions.png")

# ---- 図2：「全体」とされる数字と中央値 ------------------------------------------------------
pick = [("毎月勤労：5人以上・就業形態計 ×12", "毎月勤労\n5人以上の事業所\n（パートを含む）"), ("国税庁：1年未満勤続の人も含めた平均", "国税庁\n1年未満勤続を含む"),
        ("国税庁：1年を通じて勤務した人の中央値", "国税庁\n1年勤務の中央値"), ("国税庁：1年を通じて勤務した人の平均", "国税庁\n1年勤務の平均\n（よく引用される数字）"),
        ("毎月勤労：30人以上・就業形態計 ×12", "毎月勤労\n30人以上の事業所\n（パートを含む）")]
v = [float(df.set_index("definition").loc[k, "annual_man"]) for k, _ in pick]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(pick))
ax.bar(x, v, width=0.6, color=[C[1], C[0], C[2], C[0], C[1]])
for i, val in enumerate(v):
    ax.text(i, val + 6, f"{val:.0f}万円", ha="center", fontsize=10, color=INK)
ax.set_xticks(x); ax.set_xticklabels([l for _, l in pick], fontsize=8.8)
ax.set_ylim(0, 560)
ax.set_ylabel("2025年の年収（万円）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("「全体の平均」とされる数字は427万〜490万円。中央値は420万円", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：中央値は給与階級（100万円きざみなど）の人数から、階級の中で人数が均等に並ぶとして求めた。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.2)
save(fig, "fig2_overall_numbers.png")

# ---- 図3：給与階級の分布（1年勤務、2025年） -------------------------------------------------
b = br[(br.kind == "1年勤務") & (br.sex == "計") & (br.bracket != "計")].copy()
b["lo"] = [0] + list(b.upper_man.values[:-1])
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(b))
ax.bar(x, b.persons / 1e4, width=0.75, color=C[0])
labels = [s.replace("万円以下", "").replace("万円超", "超") for s in b.bracket]
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8.5, rotation=0)
# 平均・中央値の位置（100万円きざみの範囲だけ）
def pos(val):
    for i, (lo, hi) in enumerate(zip(b.lo, b.upper_man)):
        if lo < val <= hi:
            return i - 0.5 + (val - lo) / (hi - lo)
for val, lab, c in [(main["nta_median"], "中央値", C[2]), (main["nta_full_mean"], "平均", C[1])]:
    p = pos(val); ax.axvline(p, color=c, lw=2, ls="--")
    left = lab == "中央値"
    ax.text(p + (-0.1 if left else 0.1), 890, f"{lab}\n{val:.0f}万円", color=INK, fontsize=9.5, va="top", ha="right" if left else "left",
            bbox=dict(boxstyle="round,pad=0.2", fc="#fcfcfb", ec="none"))
ax.set_ylim(0, 920)
ax.set_xlabel("年間の給与（万円、各階級の上限。たとえば「500」は400万円超500万円以下）")
ax.set_ylabel("人数（万人）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"1年を通じて勤務した人の{main['share_below_mean']*100:.0f}%は、平均（487万円）より下", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：国税庁の1年を通じて勤務した給与所得者（5,163万人）。1,000万円を超える階級は幅が広い（500万円きざみ）。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_distribution.png")

# ---- 図4：平均と中央値の推移 ----------------------------------------------------------------
a = yrs[yrs.sex == "計"]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(a.year, a["mean"], color=C[0], lw=2.2, marker="o", ms=4, label="平均")
ax.plot(a.year, a["median"], color=C[2], lw=2.2, marker="o", ms=4, label="中央値")
for y in [2016, 2025]:
    r = a[a.year == y].iloc[0]
    ax.text(y, r["mean"] + 8, f"{r['mean']:.0f}", ha="center", fontsize=9, color=INK)
    ax.text(y, r["median"] - 18, f"{r['median']:.0f}", ha="center", fontsize=9, color=INK)
ax.legend(loc="upper left", frameon=False)
ax.set_xlim(2015.5, 2025.5); ax.set_ylim(300, 520)
ax.set_xticks(range(2016, 2026))
ax.set_ylabel("1年を通じて勤務した人の年収（万円）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"平均と中央値の差は、この10年ずっと{req['gap_min']:.0f}万〜{req['gap_max']:.0f}万円", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：国税庁の累年比較（2016〜2025年分）。中央値は給与階級の人数から求めた。\n" + SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_mean_median_years.png")
print("figures ok")
