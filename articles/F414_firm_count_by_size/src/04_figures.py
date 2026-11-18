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
C = {"individual": "#eb6834", "company": "#2a78d6", "other_corp": "#1baf7a"}
OJ = {"individual": "個人経営", "company": "会社企業", "other_corp": "会社以外の法人"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：総務省・経済産業省「経済センサス」（活動調査 2012・2016・2021年、基礎調査 2014年）をもとに作成者が加工して作成"
META = {"Software": None}
m = json.load(open(R / "main.json", encoding="utf-8"))
SG_ORDER = ["0〜4人", "5〜19人", "20〜99人", "100〜299人", "300人以上"]


def lab(v):
    return f"{v:+.1f}" if abs(v) >= 0.05 else f"{int(round(v * 1e4)):+d}社"


def finish(fig, ax, title, grid="y", bottom=0.16):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.88, bottom=bottom)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


# 図1：経営組織別の企業等数
lv = pd.read_csv(R / "level_by_org.csv", index_col="year")
years = [2012, 2014, 2016, 2021]
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(len(years)); bottom = np.zeros(len(years))
for o in ("individual", "company", "other_corp"):
    v = lv.loc[years, o].values / 1e4
    ax.bar(x, v, 0.55, bottom=bottom, color=C[o], label=OJ[o])
    for xi, b, h in zip(x, bottom, v):
        ax.text(xi, b + h / 2, f"{h:.1f}", ha="center", va="center", color="white", fontsize=9.5)
    bottom += v
for xi, t in zip(x, bottom):
    ax.text(xi, t + 4, f"計 {t:.1f}", ha="center", va="bottom", fontsize=9.5, color=INK)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年\n（{'基礎調査' if y == 2014 else '活動調査'}）" for y in years])
ax.set_ylabel("企業等数（万）"); ax.set_ylim(0, 470)
ax.legend(frameon=False, ncol=3, loc="upper right", fontsize=9.5)
finish(fig, ax, "図1 企業等の数：個人経営は減り続け、会社企業は2016年に減ったあと2021年に増加", bottom=0.18)
save(fig, "fig1_level_by_org.png")

# 図2：2012→2021年の増減（規模×経営組織）
ch = pd.read_csv(R / "change_org_size_2012_2021.csv")
fig, ax = plt.subplots(figsize=(9, 4.8))
yy = np.arange(len(SG_ORDER))[::-1]; h = 0.26
for j, o in enumerate(("individual", "company", "other_corp")):
    sub = ch[ch.org == o].set_index("sg").loc[SG_ORDER]
    v = sub.change.values / 1e4
    ax.barh(yy + (1 - j) * h, v, h, color=C[o], label=OJ[o])
    for y_, vv in zip(yy + (1 - j) * h, v):
        ax.text(vv + (0.8 if vv >= 0 else -0.8), y_, lab(vv), va="center", ha="left" if vv >= 0 else "right", fontsize=8.6)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy); ax.set_yticklabels([f"常用雇用者 {s}" for s in SG_ORDER])
ax.set_xlabel("2012年→2021年の企業等数の増減（万）")
ax.set_xlim(-62, 16)
ax.legend(frameon=False, fontsize=9.5, loc="lower left")
finish(fig, ax, "図2 減少の大半は、常用雇用者0〜4人の個人経営", grid="x", bottom=0.18)
fig.subplots_adjust(left=0.2)
save(fig, "fig2_change_org_size.png")

# 図3：産業別の増減（個人経営と会社企業）。産業分類の順。主な6産業のほかはまとめる
ind = pd.read_csv(R / "change_by_industry_2012_2021.csv")
MAIN = ["D", "E", "I", "K", "M", "N"]
NAME = {"D": "建設業", "E": "製造業", "I": "卸売業，小売業", "K": "不動産業，物品賃貸業", "M": "宿泊業，飲食サービス業",
        "N": "生活関連サービス業，娯楽業", "Z": "その他の産業（12の大分類）"}
rows = []
for o in ("individual", "company"):
    s = ind[ind.org == o].set_index("ind")
    for k in MAIN:
        rows.append({"org": o, "ind": k, "change": s.loc[k, "change"]})
    rows.append({"org": o, "ind": "Z", "change": s.loc[[i for i in s.index if i not in MAIN], "change"].sum()})
pv = pd.DataFrame(rows)
labs = MAIN + ["Z"]
fig, ax = plt.subplots(figsize=(9, 4.8))
yy = np.arange(len(labs))[::-1]; h = 0.36
for j, o in enumerate(("individual", "company")):
    v = pv[pv.org == o].set_index("ind").loc[labs, "change"].values / 1e4
    ax.barh(yy + (0.5 - j) * h, v, h, color=C[o], label=OJ[o])
    for y_, vv in zip(yy + (0.5 - j) * h, v):
        ax.text(vv + (0.4 if vv >= 0 else -0.4), y_, lab(vv), va="center", ha="left" if vv >= 0 else "right", fontsize=8.6)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy); ax.set_yticklabels([NAME[k] for k in labs], fontsize=9.5)
ax.set_xlabel("2012年→2021年の企業等数の増減（万）。並びは産業分類の順")
ax.set_xlim(-20, 15)
ax.legend(frameon=False, fontsize=9.5, loc="lower left")
finish(fig, ax, "図3 産業別の増減（2012→2021年）", grid="x", bottom=0.18)
fig.subplots_adjust(left=0.27)
save(fig, "fig3_change_by_industry.png")

# 図4：問い直し：企業の数の割合と、常用雇用者の割合（規模別）
rq = pd.read_csv(R / "requestion_employment_by_size.csv")
fig, axs = plt.subplots(1, 2, figsize=(9, 4.8), sharey=True)
yy = np.arange(len(SG_ORDER))[::-1]; h = 0.36
for ax, col, ttl in ((axs[0], "firm_share", "企業等数の割合"), (axs[1], "emp_share", "常用雇用者数の割合")):
    for j, (y, cc) in enumerate(((2012, "#9fc3ee"), (2021, "#2a78d6"))):
        v = rq[rq.year == y].set_index("sg").loc[SG_ORDER, col].values * 100
        ax.barh(yy + (0.5 - j) * h, v, h, color=cc, label=f"{y}年")
        for y_, vv in zip(yy + (0.5 - j) * h, v):
            ax.text(vv + 1, y_, f"{vv:.1f}%", va="center", fontsize=8.6)
    ax.set_title(ttl, fontsize=10.5, color=INK2, loc="left")
    ax.set_xlabel("%"); ax.set_xlim(0, 95); ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
axs[0].set_yticks(yy); axs[0].set_yticklabels(SG_ORDER)
axs[1].legend(frameon=False, fontsize=9.5, loc="center right")
fig.suptitle("図4 数では0〜4人が7割強、雇用では300人以上が5割近く（規模別の割合）", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.015, SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.12, right=0.97, top=0.84, bottom=0.15, wspace=0.08)
save(fig, "fig4_firms_vs_employment.png")
print("ok")
