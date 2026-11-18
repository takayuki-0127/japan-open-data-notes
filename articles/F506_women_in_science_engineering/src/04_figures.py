"""図4枚（PNG）。日付などのメタデータは入れない。"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RES, FIG

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
SRC = "出典：文部科学省「学校基本調査」（各年度5月1日時点、入学者）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, metadata=META)
    plt.close(fig)


sb = pd.read_csv(RES / "share_by_year.csv")
ss = pd.read_csv(RES / "subfield_share.csv", keep_default_na=False)


def ser(level, g, col="female_share"):
    return sb[(sb.level == level) & (sb.group == g)].set_index("year")[col]


# 図1：学部の女性の割合
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.08, right=0.86, top=0.86, bottom=0.12)
for g, c, nm in [("全体", "#8a8985", "学部全体"), ("理学", C[2], "理学"), ("工学", C[0], "工学")]:
    s = ser("ug", g)
    ax.plot(s.index, s.values, color=c, lw=2, ls="--" if g == "全体" else "-")
    ax.text(2025.4, s[2025], f"{nm} {s[2025]:.1f}%", color=INK, fontsize=10, va="center")
    ax.text(2000, s[2000] + 1.3, f"{s[2000]:.1f}%", color=INK2, fontsize=9)
ax.axvline(2010, color=GRID, lw=1)
ax.set_xlim(1999.5, 2025.3)
ax.set_ylim(0, 52)
ax.set_xticks(range(2000, 2026, 5))
ax.set_ylabel("入学者に占める女性の割合（%）")
finish(fig, ax, "図1　工学の女性の割合は10.5%から20.4%に。上がったのは2010年度以降")
save(fig, "fig1_female_share_ug.png")

# 図2：工学の入学者（女性・男性）、2000年度＝100
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.08, right=0.86, top=0.86, bottom=0.12)
for col, c, nm in [("female", C[1], "女性"), ("male", C[0], "男性")]:
    s = ser("ug", "工学", col)
    idx = 100 * s / s[2000]
    ax.plot(idx.index, idx.values, color=c, lw=2)
    ax.text(2025.4, idx[2025], f"{nm} {idx[2025]:.0f}\n（{s[2025]:,.0f}人）", color=INK, fontsize=9.5, va="center")
ax.axhline(100, color=INK2, lw=0.8)
ax.set_xlim(1999.5, 2025.3)
ax.set_xticks(range(2000, 2026, 5))
ax.set_ylabel("工学の入学者（2000年度＝100）")
finish(fig, ax, "図2　工学の女性の入学者は1.7倍、男性は0.77倍（2000→2025年度）")
save(fig, "fig2_eng_entrants_index.png")

# 図3：学科別の女性の割合 2000年度と2025年度
items = [("工学", "機械工学"), ("工学", "電気通信工学"), ("工学", "土木建築工学"), ("工学", "応用化学"), ("工学", "その他"),
         ("理学", "数学"), ("理学", "物理学"), ("理学", "化学"), ("理学", "生物"), ("理学", "地学")]
fig, ax = plt.subplots(figsize=(8.6, 5.4))
fig.subplots_adjust(left=0.2, right=0.95, top=0.86, bottom=0.14)
for i, (f, s) in enumerate(items):
    q = ss[(ss.field == f) & (ss["sub"] == s)].set_index("year")["female_share"].astype(float)
    y = len(items) - 1 - i
    ax.plot([q[2000], q[2025]], [y, y], color=GRID, lw=3, zorder=1)
    ax.plot(q[2000], y, "o", ms=8, color="#9fc3ee", mec="#fcfcfb", mew=1.5, zorder=3)
    ax.plot(q[2025], y, "o", ms=8, color=C[0], mec="#fcfcfb", mew=1.5, zorder=3)
    ax.text(max(q[2000], q[2025]) + 1.2, y, f"{q[2000]:.1f}→{q[2025]:.1f}%", va="center", fontsize=9, color=INK)
ax.set_yticks(range(len(items)))
ax.set_yticklabels([f"{f}｜{s}" for f, s in items][::-1])
ax.set_xlim(0, 60)
ax.set_xlabel("入学者に占める女性の割合（%）　○2000年度　●2025年度", fontsize=9.5, color=INK2)
ax.grid(axis="x", color=GRID, lw=0.8)
ax.set_title("図3　工学の主な学科はどれも上がり、機械は2.9%→8.2%。数学は横ばい", loc="left", fontsize=12.5, color=INK, pad=12)
ax.set_axisbelow(True)
fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)
save(fig, "fig3_subfield_share.png")

# 図4：工学の学部・修士・博士の女性の割合
fig, ax = plt.subplots(figsize=(8.6, 5.0))
fig.subplots_adjust(left=0.08, right=0.86, top=0.86, bottom=0.12)
for lv, c, nm in [("ug", C[0], "学部"), ("master", C[3], "修士"), ("doctor", C[5], "博士")]:
    s = ser(lv, "工学")
    ax.plot(s.index, s.values, color=c, lw=2)
    off = {"ug": 0.5, "master": -0.6, "doctor": 0.0}[lv]
    ax.text(2025.4, s[2025] + off, f"{nm} {s[2025]:.1f}%", color=INK, fontsize=10, va="center")
ax.set_xlim(1999.5, 2025.3)
ax.set_ylim(0, 23)
ax.set_xticks(range(2000, 2026, 5))
ax.set_ylabel("工学の入学者に占める女性の割合（%）")
finish(fig, ax, "図4　工学の修士は9.0%→15.5%。学部より上がり幅が小さい")
save(fig, "fig4_eng_grad_share.png")
print("figures ok")
