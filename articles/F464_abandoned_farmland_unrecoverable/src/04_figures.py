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
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：農林水産省「荒廃農地の発生・解消状況に関する調査」（各年の公表資料の都道府県別の表）をもとに作成者が加工して作成"
META = {"Software": None}
REG = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
N = pd.read_csv(R / "national_by_year.csv", index_col="year")
RG = pd.read_csv(R / "region_by_year.csv")
PF = pd.read_csv(R / "pref_B_share.csv", index_col="pref_code")
RQ = json.load(open(R / "requestion.json", encoding="utf-8"))


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.4, color=INK2)


def label(y):
    return f"{y}" if y <= 2020 else f"{y}年度"


# 図1：全国の A・B と B の割合
fig, ax = plt.subplots(figsize=(8.8, 4.9))
yrs = list(N.index); x = np.arange(len(yrs))
ax.bar(x, N.B / 1e4, 0.62, color=C[1], label="再生利用が困難（B分類）")
ax.bar(x, N.A / 1e4, 0.62, bottom=N.B / 1e4, color=C[0], label="再生利用が可能（A分類）")
for i, y in enumerate(yrs):
    ax.text(i, N.total[y] / 1e4 + 0.4, f"{N.B_share[y]:.0f}%", ha="center", fontsize=8.6, color=C[1])
k = yrs.index(2021)
ax.axvline(k - 0.5, color=INK2, lw=0.9, ls=":")
ax.text(k - 0.45, 31.2, "2021年度から調査を見直し\n（前とは単純にくらべられない）", fontsize=8.3, color=INK2, va="top")
ax.set_xticks(x, [str(y) if y <= 2020 else f"{y}\n年度" for y in yrs], fontsize=9)
ax.set_ylim(0, 32); ax.set_ylabel("荒廃農地の面積（万ha）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=2)
ax.set_title("図1　荒廃農地の面積と、そのうち「再生利用が困難」の割合（全国）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.2)
foot(fig, "棒の上の数字は、面積計に占める B分類の割合。47都道府県の表の合計（実績値）。2011〜2020年は暦年、2021年度からは年度末現在。")
save(fig, "fig1_national.png")

# 図2：地方別の B の割合
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ys = [2013, 2020, 2021, 2024]
cols = ["#b9d3f2", C[0], "#f3ae8c", C[1]]
xw = 0.2
for j, y in enumerate(ys):
    v = [RG[(RG.region == r) & (RG.year == y)].B_share.iloc[0] for r in REG]
    ax.bar(np.arange(len(REG)) + (j - 1.5) * xw, v, xw, color=cols[j], label=label(y))
ax.set_xticks(np.arange(len(REG)), REG)
ax.set_ylim(0, 100); ax.set_ylabel("B分類の割合（%）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, ncol=4, loc="upper left", fontsize=9)
ax.set_title("図2　地方別の「再生利用が困難」の割合（北から南の順）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.17)
foot(fig, "地方は農林水産省の農業地域の区分。並びは地方の北から南の順で、値の順ではない。")
save(fig, "fig2_region.png")

# 図3：都道府県別（北から南）
fig, ax = plt.subplots(figsize=(9.6, 5.0))
x = np.arange(47)
ax.vlines(x, PF.B_share_2013, PF.B_share_2020, color="#c9c8c4", lw=1.2)
ax.scatter(x, PF.B_share_2013, s=16, color="#8fb8ea", label="2013年", zorder=3)
ax.scatter(x, PF.B_share_2020, s=18, color=C[0], label="2020年", zorder=3)
ax.scatter(x, PF.B_share_2024, s=22, marker="x", color=C[1], label="2024年度", zorder=4)
ax.set_xticks(x, [p[:3] for p in PF.pref], rotation=90, fontsize=8)
ax.set_ylim(0, 100); ax.set_xlim(-0.8, 46.8); ax.set_ylabel("B分類の割合（%）")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, ncol=3, loc="upper left", fontsize=9)
ax.set_title("図3　都道府県別の「再生利用が困難」の割合（都道府県コード順＝北から南）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.07, right=0.99, top=0.9, bottom=0.24)
foot(fig, "並びは都道府県コード順で、値の順ではない。荒廃農地の面積が小さい都府県は、割合が大きく動きやすい。")
save(fig, "fig3_pref.png")

# 図4：2021年度からの出入り
fig, ax = plt.subplots(figsize=(8.8, 4.7))
yy = ["2022", "2023", "2024"]
items = [("new", "新たに発生した面積", C[1], 1), ("reclaimed", "再生された面積", C[2], -1), ("residual", "発生・再生のほかに面積計から外れた分（残差）", "#9b9a96", -1)]
xw = 0.26
for j, (k, nm, c, sg) in enumerate(items):
    v = [sg * RQ["national"][y][k] / 1e4 for y in yy]
    ax.bar(np.arange(3) + (j - 1) * xw, v, xw, color=c, label=nm)
    for i, vv in enumerate(v):
        ax.text(i + (j - 1) * xw, vv + (0.08 if vv > 0 else -0.08), f"{abs(vv):.1f}", ha="center", va="bottom" if vv > 0 else "top", fontsize=8.6, color=INK2)
tc = [(RQ["national"][y]["new"] - RQ["national"][y]["reclaimed"] - RQ["national"][y]["residual"]) / 1e4 for y in yy]
ax.plot(np.arange(3), tc, "D", color="#2b2a28", ms=6, label="面積計の増減（前年度から）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(np.arange(3), [f"{y}年度" for y in yy])
ax.set_ylim(-3.2, 4.7); ax.set_ylabel("面積（万ha）　上：増える分／下：減る分")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper center", fontsize=8.6, ncol=2)
ax.set_title("図4　毎年2〜3万haが新たに荒れ、発生と再生の差とほぼ同じだけ面積計から外れている", loc="left", fontsize=11.2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.9, bottom=0.17)
foot(fig, "残差＝前年度の面積計＋新たに発生−再生−今年度の面積計。中身（非農地判断など）はこの表では分からない。")
save(fig, "fig4_flow.png")
