"""図を作る（PNG、メタデータなし）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e"})
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
GRAY, INK2 = "#9a9893", "#52514e"
SRC = "出典：総務省「科学技術研究調査」各年調査（2002〜2025年）総括 第1表・第2表をもとに作成者が加工"
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))
q = json.loads((RES / "requestion.json").read_text(encoding="utf-8"))
R = pd.read_csv(RES / "researchers_by_sector.csv", index_col=0)
E = pd.read_csv(RES / "expenditure_by_sector.csv", index_col=0)
P = pd.read_csv(RES / "per_researcher_by_sector.csv", index_col=0)
LAB = {"business": "企業", "university": "大学等", "public": "公的機関", "nonprofit": "非営利団体"}
COL = {"business": C6[0], "university": C6[1], "public": C6[2], "nonprofit": C6[3]}
def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7.5, color=INK2)
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None}); plt.close(fig)
x = R.index.values
def idx_plot(X, name, title, sub, ylab, ylim, offs):
    fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.85, top=0.83, bottom=0.14)
    for s in LAB:
        v = 100 * X[s] / X.loc[2002:2004, s].mean(); ax.plot(x, v, color=COL[s], lw=2)
        ax.text(2025.4, v.iloc[-1] + offs.get(s, 0), LAB[s], fontsize=9, color=COL[s], va="center")
    ax.axhline(100, color=GRAY, lw=0.6, ls=":")
    ax.set_ylabel(ylab); ax.set_xlabel("調査年"); ax.set_ylim(*ylim); ax.set_xticks(range(2002, 2026, 2)); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
    fig.suptitle(title, x=0.02, ha="left", fontsize=13, y=0.97); fig.text(0.02, 0.885, sub, fontsize=9, color=INK2)
    save(fig, name)
rr, ee, pp = m["researchers"], m["expenditure"], m["per_researcher_10k_yen"]
idx_plot(R, "fig1_researchers_by_sector.png", "研究者は企業と大学等で増え、公的機関と非営利団体で減った",
         f"2002〜04年→2023〜25年調査（対数差×100）：企業 {rr['business']['dlog']:+.0f}、大学等 {rr['university']['dlog']:+.0f}、公的機関 {rr['public']['dlog']:+.0f}、非営利団体 {rr['nonprofit']['dlog']:+.0f}",
         "研究者数の指数（2002〜04年調査平均＝100）", (50, 135), {"business": -2, "university": 2})
idx_plot(E, "fig2_expenditure_by_sector.png", "研究費は企業で大きく伸び、大学等は緩やかだった",
         f"内部使用研究費（名目、調査の前年度）。2002〜04年→2023〜25年：企業 {ee['business']['dlog']:+.0f}、大学等 {ee['university']['dlog']:+.0f}、公的機関 {ee['public']['dlog']:+.0f}。増えた分の {m['contrib_expenditure_pct']['business']:.0f}% が企業",
         "研究費の指数（2002〜04年調査平均＝100）", (50, 160), {"university": -2, "public": 2})
# 図3：1人当たり研究費
fig, ax = plt.subplots(figsize=(8.4, 5)); fig.subplots_adjust(left=0.09, right=0.85, top=0.83, bottom=0.14)
for s in ["public", "business", "university"]:
    ax.plot(x, P[s], color=COL[s], lw=2); ax.text(2025.4, P[s].iloc[-1], LAB[s], fontsize=9, color=COL[s], va="center")
ax.set_ylabel("研究者1人当たりの研究費（万円、名目）"); ax.set_xlabel("調査年"); ax.set_ylim(0, 7500); ax.set_xticks(range(2002, 2026, 2)); ax.grid(axis="y", color="#e6e5e1", lw=0.6)
fig.suptitle("大学等の研究者1人当たりの研究費は、20年あまり横ばい", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.885, f"2002〜04年→2023〜25年調査：大学等 {pp['university']['start']:.0f}万→{pp['university']['end']:.0f}万円（{pp['university']['dlog']:+.1f}）、企業 {pp['business']['dlog']:+.0f}、公的機関 {pp['public']['dlog']:+.0f}", fontsize=9, color=INK2)
save(fig, "fig3_per_researcher.png")
# 図4：直近3年の伸びの分解
t = pd.read_csv(RES / "requestion_recent.csv", index_col=0).loc[["business", "university", "public", "total"]]
fig, ax = plt.subplots(figsize=(8.4, 4.9)); fig.subplots_adjust(left=0.1, right=0.97, top=0.82, bottom=0.16)
xx = np.arange(len(t)); w = 0.38
ax.bar(xx - w / 2, t.res_dlog, w, color=GRAY, label="研究者数の伸び")
ax.bar(xx + w / 2, t.per_dlog, w, color=C6[0], label="1人当たり研究費の伸び")
for xi, v in zip(xx - w / 2, t.res_dlog): ax.text(xi, v + (0.4 if v >= 0 else -1.2), f"{v:+.1f}", ha="center", fontsize=8.5)
for xi, v in zip(xx + w / 2, t.per_dlog): ax.text(xi, v + 0.4, f"{v:+.1f}", ha="center", fontsize=8.5)
ax.axhline(0, color=INK2, lw=0.8); ax.set_xticks(xx); ax.set_xticklabels(["企業", "大学等", "公的機関", "全体"]); ax.set_ylim(-4, 24)
ax.set_ylabel("対数差×100（2020〜22年→2023〜25年調査）"); ax.grid(axis="y", color="#e6e5e1", lw=0.6); ax.legend(frameon=False, fontsize=9, loc="upper right")
fig.suptitle("直近の研究費の伸びは、人の数より1人当たりの増加", x=0.02, ha="left", fontsize=13, y=0.97)
fig.text(0.02, 0.875, f"研究費の総額 {q['total_2022_trillion']:.1f}兆円（2022年調査）→ {q['total_2025_trillion']:.1f}兆円（2025年調査）。直近3年の増加分の {q['recent']['business']['share_of_change']:.0f}% が企業（名目）", fontsize=9, color=INK2)
save(fig, "fig4_recent_decomposition.png")
print("ok")
