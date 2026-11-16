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
SRC1 = "出典：総務省「国勢調査」時系列データ（15歳以上就業者、常住地）をもとに作成者が加工して作成"
SRC2 = "出典：総務省「国勢調査」（2020年、常住地）、総務省・経済産業省「令和3年経済センサス‐活動調査」速報（民営事業所の従業者）をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, src=SRC1, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, src, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
yrs = [2005, 2010, 2015, 2020]

# 図1
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for key, lab, col, ls in [("tokyo_area_share_G", "情報通信業：東京圏（1都3県）", C[0], "-"), ("tokyo_share_G", "情報通信業：東京都", C[1], "-"),
                          ("tokyo_area_share_total", "全産業：東京圏", C[0], "--"), ("tokyo_share_total", "全産業：東京都", C[1], "--")]:
    v = [m[key][str(y)] for y in yrs]
    ax.plot(yrs, v, color=col, lw=2.2, ls=ls, marker="o", ms=6, label=lab)
    for y, val in zip([2005, 2020], [v[0], v[-1]]):
        ax.annotate(f"{val:.1f}%", (y, val), textcoords="offset points", xytext=(-9 if y == 2005 else 9, 0),
                    ha="right" if y == 2005 else "left", va="center", fontsize=9, color=INK)
ax.set_xticks(yrs)
ax.set_xlim(2002.5, 2022.5)
ax.set_ylim(0, 72)
ax.set_xlabel("国勢調査の年")
ax.set_ylabel("全国の就業者に占める割合（%）")
ax.legend(frameon=False, loc="upper left", ncol=2, fontsize=9.5)
finish(fig, ax, "情報通信業で働く人の31%が東京都に、62%が東京圏に住む（2020年）")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig1_tokyo_share.png")

# 図2：地方別（北から南）
rg = pd.read_csv(R / "region_share.csv")
regs = list(dict.fromkeys(rg.region))
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(regs)); w = 0.27
for i, (lab, col, sel) in enumerate([("情報通信業 2005年", "#86b6ef", (rg.year == 2005, "share_G")), ("情報通信業 2020年", C[0], (rg.year == 2020, "share_G")),
                                      ("全産業 2020年", C[3], (rg.year == 2020, "share_total"))]):
    v = rg[sel[0]].set_index("region").loc[regs, sel[1]].values
    ax.bar(x + (i - 1) * w, v, w * 0.95, color=col, label=lab)
    for xi, vi in zip(x, v):
        if vi > 8:
            ax.text(xi + (i - 1) * w, vi + 0.8, f"{vi:.0f}", ha="center", fontsize=8.5, color=INK)
ax.set_xticks(x, regs)
ax.set_ylabel("全国に占める割合（%）")
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "関東以外のどの地方でも、情報通信業の割合は全産業の割合より小さい")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig2_region_share.png")

# 図3：住む場所と働く場所
rb = pd.read_csv(R / "robustness.csv").set_index("check")
ec = pd.read_csv(R / "ecensus2021_concentration.csv").set_index("ind")
labs = [("G", "情報通信業", "本線：情報通信業・総数（原数値）"), ("J", "金融業・保険業", "金融業・保険業"),
        ("L", "学術研究・専門技術\nサービス業", "学術研究・専門技術サービス業"), ("total", "全産業", "全産業")]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(labs)); w = 0.36
v1 = [rb.loc[k3, "tokyo1"] for _, _, k3 in labs]
v2 = [ec.loc[k1, "tokyo"] for k1, _, _ in labs]
ax.bar(x - w / 2, v1, w * 0.95, color=C[0], label="住む場所で数えた割合（国勢調査 2020年）")
ax.bar(x + w / 2, v2, w * 0.95, color=C[1], label="働く場所で数えた割合（経済センサス 2021年）")
for xi, a, b in zip(x, v1, v2):
    ax.text(xi - w / 2, a + 1, f"{a:.1f}%", ha="center", fontsize=9, color=INK)
    ax.text(xi + w / 2, b + 1, f"{b:.1f}%", ha="center", fontsize=9, color=INK)
ax.set_xticks(x, [l for _, l, _ in labs])
ax.set_ylim(0, 62)
ax.set_ylabel("全国に占める東京都の割合（%）")
ax.legend(frameon=False, loc="upper right")
finish(fig, ax, "働く場所で数えると、情報通信業の54%が東京都に集まる", src=SRC2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig3_residence_vs_workplace.png")

# 図4：増加の内訳
inc = pd.read_csv(R / "increase_by_region.csv")
inc = inc[inc.region != "うち東京都"]
regs = list(dict.fromkeys(inc.region))
fig, ax = plt.subplots(figsize=(8.8, 5.0))
x = np.arange(len(regs)); w = 0.38
for i, (p, lab, col) in enumerate([("2005→2015", "2005→2015年（+6.7万人）", "#86b6ef"), ("2015→2020", "2015→2020年（+27.5万人）", C[0])]):
    v = inc[inc.period == p].set_index("region").loc[regs, "share_of_increase_pct"].values
    ax.bar(x + (i - 0.5) * w, v, w * 0.95, color=col, label=lab)
    for xi, vi in zip(x, v):
        ax.text(xi + (i - 0.5) * w, vi + (1.2 if vi >= 0 else -4), f"{0 if abs(vi) < 0.5 else vi:.0f}", ha="center", fontsize=8.5, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, [s.replace("（東京圏を除く）", "\n（東京圏を除く）") for s in regs], fontsize=9)
ax.set_ylabel("全国の増加に占める割合（%）")
ax.legend(frameon=False, loc="upper left")
finish(fig, ax, "2015→2020年に増えた情報通信業の働き手の87%は東京圏に住む人")
fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.17)
save(fig, "fig4_increase_by_region.png")
