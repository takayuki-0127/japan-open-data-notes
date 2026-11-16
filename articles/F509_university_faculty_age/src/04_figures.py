"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import ROOT, load, POS_ORDER

R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f509"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：文部科学省「学校教員統計調査」（大学の本務教員、各年度10月1日時点）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


d = load()
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
bp = pd.read_csv(R / "by_position.csv")
by = pd.read_csv(R / "by_year.csv").set_index("year")

# ---- 図1：各歳の人数（1998・2025年度） ----------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
t = d[(d.setter == "計") & (d.position == "計") & (d.age.between(25, 69))]
for y, c in [(1998, C[0]), (2025, C[1])]:
    g = t[t.year == y].sort_values("age")
    ax.plot(g.age, g.n, color=c, lw=2.2, label=f"{y}年度（{main['total_n'][str(y)]:,}人）")
ax.axvline(40, color=INK2, lw=0.8, ls=":")
ax.text(39.6, ax.get_ylim()[1] * 0.97, "40歳", ha="right", va="top", fontsize=9, color=INK2)
ax.set_xlabel("年齢（歳）")
ax.set_ylabel("本務教員の人数（人）")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{v:,.0f}"))
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "大学の先生の年齢の山は、30代後半から40代後半〜50代へ移った")
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig1_age_distribution.png")

# ---- 図2：40歳未満と60歳以上の割合 -------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(by.index, by.share_u40, color=C[0], lw=2.2, marker="o", ms=6, label="40歳未満")
ax.plot(by.index, by.share_60p, color=C[1], lw=2.2, marker="o", ms=6, label="60歳以上")
ax.axhline(30, color=INK2, lw=0.8, ls="--")
ax.text(2013, 30.4, "3割の線", fontsize=9, color=INK2, ha="center", va="bottom")
for col, dy in [("share_u40", 9), ("share_60p", -15)]:
    for y in (1998, 2025):
        ax.annotate(f"{by.loc[y, col]:.1f}%", (y, by.loc[y, col]), textcoords="offset points",
                    xytext=(0, dy), ha="center", fontsize=9, color=INK)
ax.set_xticks(by.index)
ax.set_ylim(0, 38)
ax.set_xlabel("調査の年度")
ax.set_ylabel("本務教員に占める割合（%）")
ax.legend(frameon=False, loc="lower left")
finish(fig, ax, "40歳未満の割合は3割から2割強へ下がり、60歳以上と並んだ")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig2_young_old_share.png")

# ---- 図3：職名別の平均年齢 ---------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for p, c in zip(POS_ORDER, C):
    g = bp[bp.pos == p]
    ax.plot(g.year, g.mean_age, color=c, lw=2.0, marker="o", ms=5, label=p)
    ax.text(2025.6, g.mean_age.iloc[-1], f"{p} {g.mean_age.iloc[-1]:.1f}", va="center", fontsize=8.8, color=INK)
ax.set_xticks(sorted(bp.year.unique()))
ax.set_xlim(1997, 2032)
ax.set_xlabel("調査の年度（2004年度までの助教授は准教授、助手は助教・助手に入れた）")
ax.set_ylabel("平均年齢（歳）")
ax.legend(frameon=False, loc="lower left", ncol=5, fontsize=9, bbox_to_anchor=(0, -0.02))
ax.set_ylim(30, 68)
finish(fig, ax, "学長・副学長を除くどの職名でも、平均年齢は上がった")
fig.subplots_adjust(left=0.09, right=0.98, top=0.89, bottom=0.15)
save(fig, "fig3_mean_age_by_position.png")

# ---- 図4：同じ年齢の層の職名の内訳 ---------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
mix = pd.read_csv(R / "position_mix_by_age.csv")
labels = []
ypos = 0
order = ["教授", "准教授", "講師", "助教・助手"]
cols = [C[1], C[2], C[3], C[0]]
yt = []
for band in ["35〜39歳", "40〜44歳", "45〜49歳"]:
    for y in (1998, 2025):
        g = mix[(mix.year == y) & (mix.band == band)].set_index("pos")
        left = 0.0
        for p, c in zip(order, cols):
            v = g.loc[p, "share_pct"]
            ax.barh(ypos, v, left=left, color=c, height=0.7, edgecolor="#fcfcfb", lw=2,
                    label=p if (band == "35〜39歳" and y == 1998) else None)
            if v >= 6:
                ax.text(left + v / 2, ypos, f"{v:.0f}%", ha="center", va="center", fontsize=8.6, color=INK)
            left += v
        yt.append((ypos, f"{band} {y}年度"))
        ypos += 1
    ypos += 0.6
ax.set_yticks([p for p, _ in yt], [l for _, l in yt])
ax.invert_yaxis()
ax.set_xlim(0, 100)
ax.set_xlabel("その年齢の層の本務教員に占める割合（%）（学長・副学長は0.2%以下なので省いた）")
ax.legend(frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=9)
ax.set_title("45〜49歳で教授の人は、4割弱から4分の1に", loc="left", fontsize=12.5, color=INK, pad=28)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.text(0.01, 0.01, SRC, fontsize=7.8, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.86, bottom=0.15)
save(fig, "fig4_position_mix_by_age.png")
