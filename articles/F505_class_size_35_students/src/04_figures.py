"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RES, FIG, REGIONS

FIG.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#7b61c9"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校基本調査」（各年度5月1日時点、公立）をもとに作成者が加工して作成"
META = {"Software": None}
POLICY = {1: 2011, 2: 2021, 3: 2022, 4: 2023, 5: 2024, 6: 2025}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


by = pd.read_csv(RES / "by_year.csv")
pub = by[by.entity == "公立"]
sh = pd.read_csv(RES / "sizebins_share.csv")
reg = pd.read_csv(RES / "by_region.csv")
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))

# 図1：学年別の平均人数。35人になった年に印
fig, ax = plt.subplots(figsize=(8.6, 5.2))
fig.subplots_adjust(left=0.08, right=0.86, top=0.86, bottom=0.14)
for g in range(1, 7):
    s = pub[(pub.school == "es") & (pub.grade == g)].set_index("year")["avg"]
    ax.plot(s.index, s.values, color=C[g - 1], lw=2)
    T = POLICY[g]
    ax.plot([T], [s[T]], "o", ms=8, color=C[g - 1], mec="#fcfcfb", mew=2, zorder=5)
    ypos = {1: 25.08, 2: 25.59, 3: 26.25, 4: 26.45, 5: 26.65, 6: 26.85}[g]
    ax.text(2025.4, ypos, f"{g}年 {s[2025]:.1f}人", color=INK, fontsize=9.5, va="center")
ax.set_xlim(2007.5, 2025.3)
ax.set_xticks(range(2008, 2026, 2))
ax.set_ylabel("単式学級の平均人数（人）")
ax.set_xlabel("年度（●はその学年が35人の標準になった年度。2年は2021年度より前の2012年度に大きく下がった）", fontsize=9, color=INK2)
finish(fig, ax, "図1　小3〜小6は、35人になった年度に平均が約1人下がった（公立小学校）")
save(fig, "fig1_avg_by_grade.png")

# 図2：36人以上の学級の割合（小学校・中学校）
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.08, right=0.88, top=0.86, bottom=0.12)
for school, name, c in [("es", "小学校", C[0]), ("jh", "中学校", C[1])]:
    s = sh[(sh.school == school) & (sh.entity == "公立|単式学級")].set_index("year")["share_36plus"]
    ax.plot(s.index, s.values, color=c, lw=2)
    ax.text(2025.3, s[2025], f"{name} {s[2025]:.1f}%", color=INK, fontsize=10, va="center")
    ax.text(2008, s[2008] + 1.2, f"{s[2008]:.1f}%", color=INK2, fontsize=9, ha="left")
ax.set_xlim(2007.5, 2025.2)
ax.set_ylim(0, None)
ax.set_xticks(range(2008, 2026, 2))
ax.set_ylabel("単式学級のうち36人以上の学級の割合（%）")
finish(fig, ax, "図2　36人以上の学級は、小学校で0.3%に。中学校は24%残る（公立）")
save(fig, "fig2_share_36plus.png")

# 図3：地方別の平均の変化 2020→2025年度（北から南の順）
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.09, right=0.98, top=0.84, bottom=0.14)
x = range(len(REGIONS))
w = 0.38
r_ = reg.set_index("region").loc[REGIONS]
ax.bar([i - w / 2 - 0.01 for i in x], r_["change"], width=w, color=C[0], label="小学校")
ax.bar([i + w / 2 + 0.01 for i in x], r_["jh_change"], width=w, color=C[1], label="中学校")
for i, (a, b) in enumerate(zip(r_["change"], r_["jh_change"])):
    ax.text(i - w / 2, a - 0.05, f"{a:.2f}", ha="center", va="top", fontsize=8.5, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylim(-2.0, 0.35)
ax.set_xticks(list(x))
ax.set_xticklabels(REGIONS)
ax.set_ylabel("平均人数の変化（人、2025年度−2020年度）")
ax.set_xlabel("地方（北から南の順）", fontsize=9, color=INK2)
ax.legend(frameon=False, loc="lower right")
finish(fig, ax, "図3　小学校の平均はどの地方でも下がり、下がり幅は0.6〜1.7人")
save(fig, "fig3_region_change.png")

# 図4：人数の幅ごとの学級の数 2020→2025年度（小学校、公立の単式学級）
b = q["es"]["2020_2025"]["bins"]
labels = list(b.keys())
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.1, right=0.98, top=0.84, bottom=0.14)
x = range(len(labels))
ax.bar([i - w / 2 - 0.01 for i in x], [b[k]["n0"] / 1000 for k in labels], width=w, color="#9fc3ee", label="2020年度")
ax.bar([i + w / 2 + 0.01 for i in x], [b[k]["n1"] / 1000 for k in labels], width=w, color=C[0], label="2025年度")
for i, k in enumerate(labels):
    d = b[k]["diff"]
    ax.text(i, max(b[k]["n0"], b[k]["n1"]) / 1000 + 1.2, f"{d:+,.0f}", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=9.5)
ax.set_ylabel("学級の数（千）")
ax.set_xlabel("1学級の人数（数字は2020→2025年度の増減）", fontsize=9, color=INK2)
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "図4　36人以上の学級が減った分、増えたのは13〜30人の学級（公立小学校）")
save(fig, "fig4_size_bins.png")
print("figures ok")
