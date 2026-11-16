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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK2 = "#52514e"
SRC = "出典：観光庁「旅行・観光消費動向調査」（主要指標の推移）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
Y = pd.read_csv(RES / "yearly.csv")
P = pd.read_csv(RES / "purpose_yearly.csv")


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


def covid(ax):
    ax.set_xticks([2010, 2013, 2016, 2019, 2022, 2025])
    ax.axvspan(2019.5, 2022.5, color="#eeeeec", zorder=0)
    ax.text(2021, ax.get_ylim()[1] * 0.97, "2020〜22年\n（感染症）", ha="center", va="top", fontsize=7.5, color=INK2)


# fig1 延べ旅行者数（宿泊・日帰り）
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, c in [("宿泊", C[0]), ("日帰り", C[1])]:
    g = Y[Y.kind == k].set_index("year")["延べ旅行者数"] / 1e5
    ax.plot(g.index, g, color=c, lw=2, marker="o", ms=3.5)
    ax.text(2025.3, g.loc[2025], f"{k}\n{g.loc[2025]:.2f}億", fontsize=8.5, va="center")
    ax.annotate(f"{k} {g.loc[2010]:.2f}億", (2010, g.loc[2010]), xytext=(0, 7 if k == "宿泊" else -24), textcoords="offset points", ha="left", fontsize=8, color=INK2)
ax.set_ylim(0, 3.6); ax.set_xlim(2009.5, 2027.3)
covid(ax)
ax.set_xlabel("年"); ax.set_ylabel("延べ旅行者数（億人回）")
ax.set_title("日帰り旅行は2010年から2割減り、宿泊旅行は5%減", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_trips.png", "国内旅行。延べ旅行者数は、旅行に行った回数を人ごとに足した数")

# fig2 目的別（2010年＝100）
lab = {"観光": "観光など", "帰省": "帰省など", "出張": "出張など"}
fig, ax = plt.subplots(figsize=(8, 4.6))
for (pp, c) in [("観光", C[2]), ("帰省", C[3]), ("出張", C[4])]:
    g = P[P.purpose == pp].set_index("year")["延べ旅行者数"]
    idx = 100 * g / g.loc[2010]
    ax.plot(idx.index, idx, color=c, lw=2, marker="o", ms=3.5)
    off = {"観光": 0, "帰省": 4, "出張": -4}[pp]
    ax.text(2025.3, idx.loc[2025] + off, f"{lab[pp]} {idx.loc[2025]:.0f}", fontsize=8.5, va="center")
ax.axhline(100, color=INK2, lw=0.8)
ax.set_ylim(0, 125); ax.set_xlim(2009.5, 2028.5)
covid(ax)
ax.set_xlabel("年"); ax.set_ylabel("延べ旅行者数（2010年＝100）")
ax.set_title("観光の旅行はほぼ横ばいで、減ったのは帰省と出張", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig2_purpose.png", "国内旅行（宿泊と日帰りの合計）。観光など＝観光・レクリエーション、帰省など＝帰省・知人訪問等、出張など＝出張・業務")

# fig3 消費額の分け方
S = pd.read_csv(RES / "spend_decomp.csv")
S = S[(S.kind == "全体") & (S.purpose == "計") & (S.y1 != 2025) | (S.kind == "全体") & (S.purpose == "計") & (S.y0 == 2019)]
fig, ax = plt.subplots(figsize=(8, 4.4))
lab = ["旅行消費額", "延べ旅行者数", "旅行単価"]
y = np.arange(3)[::-1]
for k, (y0, y1, c) in enumerate([(2010, 2019, C[0]), (2019, 2025, C[1])]):
    r = S[(S.y0 == y0) & (S.y1 == y1)].iloc[0]
    v = [r.spend_chg, r.trips_chg, r.unit_chg]
    yy = y + (0.18 if k == 0 else -0.18)
    ax.barh(yy, v, height=0.34, color=c, label=f"{y0}→{y1}年")
    for yi, vi in zip(yy, v):
        ax.text(vi + (0.6 if vi >= 0 else -0.6), yi, f"{vi:+.1f}%", va="center", ha="left" if vi >= 0 else "right", fontsize=8.5)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(y, lab); ax.grid(axis="y", visible=False); ax.set_xlim(-15, 42)
ax.set_xlabel("変化（%、名目）")
ax.set_title("消費額が増えたのは、回数ではなく1回あたりの支出が増えたため", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
fig.subplots_adjust(bottom=0.2, left=0.16, right=0.98, top=0.9)
save(fig, "fig3_spend.png", "旅行消費額＝延べ旅行者数×旅行単価（1人1回あたりの支出）。金額は名目で、物価の変化をのぞいていない")

# fig4 1人あたりの平均回数
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, c in [("宿泊", C[0]), ("日帰り", C[1])]:
    g = Y[Y.kind == k].set_index("year")["旅行平均回数"]
    ax.plot(g.index, g, color=c, lw=2, marker="o", ms=3.5)
    ax.text(2025.3, g.loc[2025], f"{k}\n{g.loc[2025]:.2f}回", fontsize=8.5, va="center")
    ax.annotate(f"{g.loc[2010]:.2f}回", (2010, g.loc[2010]), xytext=(0, 8 if k == "宿泊" else -14), textcoords="offset points", ha="center", fontsize=8, color=INK2)
ax.set_ylim(0, 3); ax.set_xlim(2009.5, 2027.3)
covid(ax)
ax.set_xlabel("年"); ax.set_ylabel("1人あたりの年間の旅行回数（回）")
ax.set_title("1人あたりの回数も、日帰りで減った", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig4_per_person.png", "旅行平均回数（調査の対象の人口1人あたり）")
