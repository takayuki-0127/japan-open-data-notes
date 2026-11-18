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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a63d2"]
INK, INK2, GRID, BG = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SRC = "出典：文部科学省「学校基本調査」（年次統計、高等学校（通信制）の表、各年度5月1日時点）をもとに作成者が加工して作成"
META = {"Software": None}
man = ticker.FuncFormatter(lambda v, p: f"{v / 1e4:.0f}万")


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=7.8, color=INK2)
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
ny = pd.read_csv(R / "by_year_nenji.csv", index_col="year")
ag = pd.read_csv(R / "by_year_age.csv", index_col="year")
en = pd.read_csv(R / "by_year_entrants.csv", index_col="year")
pps = pd.read_csv(R / "requestion_per_school.csv", index_col="year")

# ---- 図1：在学者と高校生全体に占める割合（2つのパネル） ----
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.9))
ax = axes[0]
ax.plot(ny.index, ny.tsushin, color=C[0], lw=2.2)
for y in [1990, 2015, 2025]:
    ax.scatter([y], [ny.at[y, "tsushin"]], color=C[0], s=28, zorder=3)
    ax.annotate(f"{y}年\n{ny.at[y, 'tsushin'] / 1e4:.1f}万人", (y, ny.at[y, "tsushin"]), xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=8.8, color=INK)
ax.set_ylim(0, 360000)
ax.yaxis.set_major_formatter(man)
ax.set_title("通信制の在学者（人）", loc="left", fontsize=10.5, color=INK)
ax = axes[1]
ax.plot(ny.index, ny.corr_share_pct, color=C[1], lw=2.2)
for y in [1990, 2015, 2025]:
    ax.scatter([y], [ny.at[y, "corr_share_pct"]], color=C[1], s=28, zorder=3)
    ax.annotate(f"{ny.at[y, 'corr_share_pct']:.1f}%", (y, ny.at[y, "corr_share_pct"]), xytext=(0, 9), textcoords="offset points",
                ha="center", fontsize=8.8, color=INK)
ax.set_ylim(0, 11.5)
ax.set_title("高校生（全日制・定時制＋通信制）に占める割合（%）", loc="left", fontsize=10.5, color=INK)
for ax in axes:
    ax.set_xlim(1984, 2027)
    ax.set_xlabel("年")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
fig.suptitle("通信制の生徒は1990年の16.7万人から2025年の30.5万人に。高校生の9.6%", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.17, wspace=0.25)
save(fig, "fig1_students_share.png")

# ---- 図2：年齢の構成 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
bottom = pd.Series(0.0, index=ag.index)
for k, lab, c in [("total_15-17_pct", "15〜17歳", C[0]), ("total_18-19_pct", "18〜19歳", C[3]), ("total_20+_pct", "20歳以上", C[2])]:
    ax.bar(ag.index, ag[k], bottom=bottom, width=3.4, color=c, label=lab, edgecolor=BG, lw=1)
    for y in ag.index:
        if ag.at[y, k] >= 6:
            ax.text(y, bottom[y] + ag.at[y, k] / 2, f"{ag.at[y, k]:.0f}", ha="center", va="center", fontsize=8.6,
                    color="white" if c != C[3] else INK)
    bottom += ag[k]
ax.set_xticks(list(ag.index))
ax.set_ylim(0, 100)
ax.set_xlabel("年度")
ax.set_ylabel("生徒に占める割合（%）")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=9.2)
ax.set_title("15〜17歳の割合は46.8%（1990年度）から82.8%（2025年度）に", loc="left", fontsize=12.5, color=INK, pad=28)
fig.subplots_adjust(left=0.1, right=0.97, top=0.84, bottom=0.15)
save(fig, "fig2_age_share.png")

# ---- 図3：公立・私立の生徒数 ----
fig, ax = plt.subplots(figsize=(8.8, 5.0))
yrs = list(pps.index)
ax.bar(yrs, pps.public_students, width=3.4, color=C[2], label="公立", edgecolor=BG, lw=1)
ax.bar(yrs, pps.private_students, bottom=pps.public_students, width=3.4, color=C[5], label="私立", edgecolor=BG, lw=1)
for y in yrs:
    t = pps.at[y, "public_students"] + pps.at[y, "private_students"]
    ax.text(y, t + 5000, f"私立 {int(pps.at[y, 'private_schools'])}校\n公立 {int(pps.at[y, 'public_schools'])}校", ha="center", fontsize=7.8, color=INK2)
ax.set_xticks(yrs)
ax.set_ylim(0, 360000)
ax.yaxis.set_major_formatter(man)
ax.set_xlabel("年度")
ax.set_ylabel("生徒数（人）")
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9.2)
ax.set_title("私立は7.0万人→24.3万人、公立は9.7万人→6.2万人（1990→2025年度）", loc="left", fontsize=12.5, color=INK, pad=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig3_public_private.png")

# ---- 図4：入学の経路（2つのパネル） ----
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.9))
ax = axes[0]
s = ny.direct_to_corr_pt.loc[1985:]
ax.plot(s.index, s, color=C[0], lw=2.2)
for y in [1990, 2010, 2025]:
    ax.scatter([y], [s[y]], color=C[0], s=28, zorder=3)
    ax.annotate(f"{s[y]:.1f}", (y, s[y]), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=8.8, color=INK)
ax.set_xlim(1984, 2027)
ax.set_ylim(0, 7)
ax.set_xlabel("年（中学校を卒業した年の3月）")
ax.set_title("中学校卒業者のうち通信制へ進んだ割合（%）", loc="left", fontsize=10.5, color=INK)
ax = axes[1]
ax.plot(en.index - 1, en.midyear_share_pct, color=C[1], lw=2.2, marker="o", ms=5)
for y in [1990, 2005, 2025]:
    ax.annotate(f"{en.at[y, 'midyear_share_pct']:.1f}", (y - 1, en.at[y, "midyear_share_pct"]), xytext=(0, 8), textcoords="offset points",
                ha="center", fontsize=8.8, color=INK)
ax.set_xlim(1984, 2027)
ax.set_ylim(0, 35)
ax.set_xlabel("入学した年度")
ax.set_title("1年間の入学者のうち5月2日以降に入った割合（%）", loc="left", fontsize=10.5, color=INK)
for ax in axes:
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
fig.suptitle("中学からそのまま入る人も、年度の途中で入る人も増えた", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.subplots_adjust(left=0.07, right=0.98, top=0.83, bottom=0.17, wspace=0.22)
save(fig, "fig4_entry_routes.png")
print("ok")
