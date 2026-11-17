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
SRC = "出典：総務省「家計調査」（二人以上の世帯）、「消費者物価指数」（2025年基準）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "national.csv").set_index("year")
M = pd.read_csv(R / "mobile_by_age.csv").set_index("year")
tr = pd.read_csv(R / "requestion_trend.csv")
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
C6 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]

# ---- 図1：支出額と物価（上下2段） -----------------------------------------------------------------
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.8, 6.0), sharex=True)
a1.plot(t.index, t.mobile_yen / 1000, color=C[1], lw=2.2, marker="o", ms=5)
for y in [2015, 2019, 2021, 2025]:
    a1.text(y, t.mobile_yen.loc[y] / 1000 + 1.6, f"{t.mobile_yen.loc[y]/1000:.1f}", ha="center", fontsize=9, color=INK)
a1.set_ylabel("携帯電話通信料\n（千円/年・1世帯）", labelpad=8); a1.set_ylim(90, 140)
a1.grid(axis="y", color=GRID, lw=0.8); a1.set_axisbelow(True)
a2.plot(t.index, t.cpi_mobile, color=C[0], lw=2.2, marker="o", ms=5)
for y in [2015, 2019, 2021, 2025]:
    a2.text(y, t.cpi_mobile.loc[y] + 8, f"{t.cpi_mobile.loc[y]:.0f}", ha="center", fontsize=9, color=INK)
a2.set_ylabel("物価指数 通信料\n（携帯電話、2025年＝100）", labelpad=8); a2.set_ylim(60, 230)
a2.grid(axis="y", color=GRID, lw=0.8); a2.set_axisbelow(True)
a2.set_xticks(range(2015, 2026)); a2.set_xticklabels([str(y) for y in range(2015, 2026)], fontsize=9)
a2.axvline(2021, color=INK2, lw=0.8, ls=":"); a1.axvline(2021, color=INK2, lw=0.8, ls=":")
a1.set_title(f"物価は2019→2025年に{abs(main['cpi_mobile_change_2019_2025_pct']):.0f}%下がり、支出は{abs(main['mobile_change_2019_2025_pct']):.1f}%減った", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：二人以上の世帯の1世帯あたり年間支出（2019年までは「移動電話通信料」）。点線は低料金プランが広がった2021年。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.17, right=0.97, top=0.93, bottom=0.12, hspace=0.12)
save(fig, "fig1_spending_and_price.png")

# ---- 図2：年齢別 2019→2025（ダンベル） -----------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
ys = np.arange(len(AGES))
for i, a in enumerate(AGES):
    v0, v1 = M.loc[2019, a] / 1000, M.loc[2025, a] / 1000
    ax.plot([v0, v1], [i, i], color=GRID, lw=3, zorder=1)
    ax.scatter([v0], [i], s=70, color=C[0], zorder=2, label="2019年" if i == 0 else None)
    ax.scatter([v1], [i], s=70, color=C[1], zorder=3, label="2025年" if i == 0 else None)
    pct = main["by_age_change_pct"][a]
    ax.text(max(v0, v1) + 4, i, f"{pct:+.1f}%".replace("-", "−"), va="center", fontsize=9.5, color=INK)
ax.set_yticks(ys); ax.set_yticklabels([f"世帯主 {a}" for a in AGES]); ax.invert_yaxis()
ax.set_xlim(50, 210); ax.set_xlabel("携帯電話通信料（千円/年・1世帯）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("60歳未満の世帯は2〜3割減、70歳以上の世帯は25%増えた", loc="left", fontsize=12)
fig.text(0.01, 0.01, f"注：二人以上の世帯。70歳以上の世帯の割合は{main['share70_2019_pct']:.1f}%（2019年）→{main['share70_2025_pct']:.1f}%（2025年）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.2, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig2_by_age.png")

# ---- 図3：年齢別の推移 ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
offs = {"29歳以下": 3, "30～39歳": -4, "40～49歳": -2, "50～59歳": 3, "60～69歳": 2, "70歳以上": 0}
for a, col in zip(AGES, C6):
    ax.plot(M.index, M[a] / 1000, color=col, lw=2)
    ax.text(2025.2, M.loc[2025, a] / 1000 + offs[a], a, va="center", fontsize=9, color=INK)
ax.axvline(2021, color=INK2, lw=0.8, ls=":")
ax.set_xlim(2015, 2027.2); ax.set_ylim(30, 200)
ax.set_xticks(range(2015, 2026))
ax.set_ylabel("携帯電話通信料（千円/年・1世帯）")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("年齢による差は縮んだ。70歳以上は値下げのあとも増え続けた", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：世帯主の年齢階級別、二人以上の世帯。点線は2021年。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_age_lines.png")

# ---- 図4：値下げ前の伸びの延長との比較（問い直し） -----------------------------------------------
avg = tr[tr.age == "平均"].set_index("year")
fig, ax = plt.subplots(figsize=(8.8, 4.8))
ax.plot(avg.index, avg.actual / 1000, color=C[1], lw=2.2, marker="o", ms=5, label="実際")
ax.plot(avg.index, avg.trend_2015_2019 / 1000, color=C[0], lw=2, ls="--", label="2015〜2019年の直線を延ばした値")
ax.fill_between(avg.loc[2021:].index, avg.loc[2021:, "actual"] / 1000, avg.loc[2021:, "trend_2015_2019"] / 1000, color=C[0], alpha=0.12, lw=0)
ax.annotate(f"2025年：実際 {req['actual_2025']/1000:.1f}千円\n延長 {req['cf_2025_avg_direct']/1000:.1f}千円", (2025, avg.loc[2025, "trend_2015_2019"] / 1000),
            xytext=(2019.6, 150), fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xlim(2015, 2025.5); ax.set_ylim(90, 165); ax.set_xticks(range(2015, 2026))
ax.set_ylabel("携帯電話通信料（千円/年・1世帯）")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"値下げ前の伸びが続いた場合より、2025年は{abs(req['gap_2025_weighted_pct']):.0f}%少ない", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：年齢別に延ばし、各年の年齢構成で平均した値との差も同じ程度（results/requestion.json）。延長は仮の比べ方で、値下げの効果そのものではない。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig4_trend_gap.png")
print("ok")
