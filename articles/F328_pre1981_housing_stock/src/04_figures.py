"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2 = "#52514e"
SRC = "出典：総務省「住宅・土地統計調査」（令和5年 第5-1表、平成30年 第6-1表、平成30年調査 時系列 第20-1表）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
METRO = [11, 12, 13, 14, 21, 23, 24, 26, 27, 28, 29]

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 全国の持ち家（1980年以前）
O = pd.read_csv(RES / "national_owned_pre1981.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(O))
ax.bar(x, O["owned"] / 1e4, color=C[0], width=0.6)
for i, (y, row) in enumerate(O.iterrows()):
    ax.text(i, row.owned / 1e4 + 15, f"{row.owned/1e4:,.0f}万戸", ha="center", fontsize=8.5, color=INK2)
    if not pd.isna(row["5年後に残る割合_%"]):
        ax.text(i - 0.5, row.owned / 1e4 * 0.5, f"5年で\n{row['5年後に残る割合_%']:.0f}%\nが残る", ha="center", fontsize=8, color="#0b0b0b",
                bbox=dict(boxstyle="round,pad=0.2", fc="#fcfcfb", ec="none"))
ax.set_xticks(x, [f"{y}年" for y in O.index]); ax.set_ylim(0, 1400)
ax.set_ylabel("1980年以前に建った持ち家（万戸）")
ax.set_title(f"1980年以前の持ち家は20年で{O['owned'].iloc[0]/1e4:,.0f}万→{O['owned'].iloc[-1]/1e4:,.0f}万戸。5年ごとに約9割が残る", loc="left", fontsize=10)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_national_owned.png", "人が住んでいる持ち家（空き家は入らない）。全国")

# fig2 都道府県の残る割合（北から南）
T = pd.read_csv(RES / "pref_pre1981.csv").set_index("pref").loc[1:47]
fig, ax = plt.subplots(figsize=(8, 9.2))
y = np.arange(len(T))[::-1]
cols = [C[1] if pr in METRO else C[0] for pr in T.index]
ax.hlines(y, 75, T["5年後に残る割合_%"], color="#e6e5e0", lw=1)
ax.scatter(T["5年後に残る割合_%"], y, c=cols, s=40, zorder=3, edgecolor="#fcfcfb")
ax.set_xlim(75, 100)
ax.set_yticks(y, [n if n == "北海道" else n[:-1] for n in T["県"]]); ax.tick_params(axis="y", labelsize=8.5)
ax.axvline(M["全国_すべて"]["5年後に残る割合_%"], color="#0b0b0b", lw=0.8, ls="--")
ax.text(M["全国_すべて"]["5年後に残る割合_%"] + 0.2, len(T) - 0.5, f"全国 {M['全国_すべて']['5年後に残る割合_%']:.1f}%", fontsize=8.5, color=INK2, va="bottom")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C[1], label="三大都市圏の11都府県"), Patch(color=C[0], label="地方圏の36道県")], frameon=False, loc="lower right", fontsize=8.5)
ax.set_xlabel("1980年以前に建った住宅が2018→2023年の5年で残った割合（%、人が住む住宅）")
ax.set_title(f"三大都市圏は平均{M['H2']['三大都市圏_平均_%']:.1f}%、地方圏は{M['H2']['地方圏_平均_%']:.1f}%が残った（北から南の順）", loc="left", fontsize=10.5)
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.09, left=0.1, right=0.98, top=0.95)
save(fig, "fig2_pref_survival.png", "点の位置が値（横軸は75%から）")

# fig3 耐震工事をした割合
fig, ax = plt.subplots(figsize=(8, 4.2))
rf = O["耐震工事をした割合_%"].dropna()
ax.bar(np.arange(len(rf)), rf.values, color=C[2], width=0.55)
for i, v in enumerate(rf.values):
    ax.text(i, v + 0.1, f"{v:.1f}%", ha="center", fontsize=9, color=INK2)
ax.set_xticks(np.arange(len(rf)), [f"{int(y)}年調査" for y in rf.index]); ax.set_ylim(0, 6)
ax.set_ylabel("耐震工事をした割合（%）")
ax.set_title("1980年以前の持ち家のうち、耐震工事をした割合は各調査で2〜4%", loc="left")
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_retrofit.png", "表の「耐震工事をした」は、各調査で尋ねた期間（調査前のおおむね数年）に工事をした持ち家。全国")

# fig4 問い直し
fig, ax = plt.subplots(figsize=(8, 4.8))
isM = T.index.isin(METRO)
ax.scatter(T.loc[~isM, "住宅全体の増減率_%"], T.loc[~isM, "5年後に残る割合_%"], s=30, color=C[0], label="地方圏", edgecolor="#fcfcfb")
ax.scatter(T.loc[isM, "住宅全体の増減率_%"], T.loc[isM, "5年後に残る割合_%"], s=30, color=C[1], label="三大都市圏", edgecolor="#fcfcfb")
b = np.polyfit(T["住宅全体の増減率_%"], T["5年後に残る割合_%"], 1); xs = np.linspace(T["住宅全体の増減率_%"].min(), T["住宅全体の増減率_%"].max(), 50)
ax.plot(xs, b[0] * xs + b[1], color=INK2, lw=1, ls="--")
ax.axvline(0, color="#0b0b0b", lw=0.6)
ax.set_xlabel("人が住む住宅全体の増減率（2018→2023年、%）"); ax.set_ylabel("1980年以前の住宅が残った割合（%）")
ax.set_title(f"人が住む住宅全体が増えている県ほど、古い住宅もよく残っている（順位相関 {M['問い直し']['順位相関']:.2f}）", loc="left", fontsize=10)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_requestion.png", "47都道府県。破線は回帰直線")
print("figures ok")
