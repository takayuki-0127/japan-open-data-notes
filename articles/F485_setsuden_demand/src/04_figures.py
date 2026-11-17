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
SRC = "出典：九州電力送配電「エリア需給実績データ」、気象庁「過去の気象データ検索」（福岡・鹿児島）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
D = pd.read_csv(R / "daily_fit.csv", parse_dates=["date"]).set_index("date")
rob = pd.read_csv(R / "robustness.csv")
bm = pd.read_csv(R / "requestion_by_month.csv")

# ---- 図1：気温と需要 ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
oth = D[(D.summer22 == 0) & (D.winter22 == 0)]
ax.scatter(oth.temp, oth.demand_gwh, s=6, color="#b9b8b2", alpha=0.6, edgecolors="none", label="要請のない日（2018〜2024年度）")
for k, col, lab in [("summer22", C[1], "2022年夏の要請期間"), ("winter22", C[0], "2022年度冬の要請期間")]:
    g = D[D[k] == 1]
    ax.scatter(g.temp, g.demand_gwh, s=12, color=col, alpha=0.8, edgecolors="none", label=f"{lab}（{len(g)}日）")
ax.set_xlabel("日平均気温（℃、福岡と鹿児島の平均）"); ax.set_ylabel("1日のエリア需要（GWh）")
ax.legend(loc="upper center", frameon=False, fontsize=9)
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("需要は気温で大きく動く。要請期間の日も、ほかの日の帯の中にある", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：九州本土のエリア需要（1日の合計）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_temp_demand.png")

# ---- 図2：見込みからの差（7日移動平均） ------------------------------------------------------------
x = D.loc["2021-04-01":"2024-03-31"]
r7 = x.resid_pct.rolling(7, center=True).mean()
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for a, b in [("2022-07-01", "2022-09-30"), ("2022-12-01", "2023-03-31")]:
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b), color="#efeeea", lw=0)
ax.plot(r7.index, r7, color=C[0], lw=1.6)
ax.axhline(0, color=INK2, lw=0.8)
ax.text(pd.Timestamp("2022-08-15"), 6.3, "夏の要請", ha="center", fontsize=9, color=INK)
ax.text(pd.Timestamp("2023-02-01"), 6.3, "冬の要請", ha="center", fontsize=9, color=INK)
ax.set_ylim(-10, 7.5); ax.set_ylabel("見込みからの差（%、7日移動平均）")
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y年%-m月"))
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("要請期間の差は、ふだんの揺れと区別がつかない大きさ", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：見込み＝気温・曜日・祝日・月・年度で説明する回帰の予測（要請の効果は0とした値）。網掛けは要請期間。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_residual.png")

# ---- 図3：推定値の比べ -----------------------------------------------------------------------------
items = [("夏（2022年7〜9月）1日の需要", main["summer22"]), ("冬（2022年12月〜2023年3月）1日の需要", main["winter22"]),
         ("夏 夕方17〜19時台", main["evening_summer22"]), ("冬 夕方17〜19時台", main["evening_winter22"]),
         ("偽の検定：2023年夏（要請なし）", main["placebo_summer23"]), ("偽の検定：2023年度冬（要請なし）", main["placebo_winter23"])]
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for i, (lab, v) in enumerate(items):
    col = C[1] if i < 4 else "#8a8984"
    ax.plot([v["lo"], v["hi"]], [i, i], color=col, lw=2.2)
    ax.scatter([v["pct"]], [i], s=60, color=col, zorder=3)
    ax.text(v["hi"] + 0.15, i, f"{v['pct']:+.2f}%".replace("-", "−"), va="center", fontsize=9, color=INK)
ax.axvline(0, color=INK2, lw=0.8); ax.axvline(-1, color=INK2, lw=0.8, ls=":")
ax.set_yticks(range(len(items))); ax.set_yticklabels([i[0] for i in items]); ax.invert_yaxis()
ax.set_xlim(-4, 3.6); ax.set_xlabel("見込みからの差（%、線は95%区間）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("1日の需要で見た低さは1%未満。夕方は少し大きいが、区間は0をまたぐ", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：回帰の係数。標準誤差は自己相関を考えた HAC（7日）。点線は仮説の基準（−1%）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.33, right=0.97, top=0.91, bottom=0.16)
save(fig, "fig3_estimates.png")

# ---- 図4：月ごと ----------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.8))
for i, r in bm.iterrows():
    col = C[1] if r.request == 1 else "#8a8984"
    ax.plot([i, i], [r.lo, r.hi], color=col, lw=2.2)
    ax.scatter([i], [r.pct], s=60, color=col, zorder=3)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(len(bm))); ax.set_xticklabels([m.replace("-", "年") + "月" for m in bm.month], fontsize=8.6)
ax.set_ylabel("見込みからの差（%、線は95%区間）"); ax.set_ylim(-5.5, 3.8)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.scatter([], [], color=C[1], label="要請のあった月"); ax.scatter([], [], color="#8a8984", label="要請のなかった月（10・11月）")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.set_title(f"要請のなかった10・11月も見込みより低い（{bm.pct[3]:.1f}%・{bm.pct[4]:.1f}%）".replace("-", "−"), loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：2022年7月〜2023年3月の各月に別々のダミーを置いた回帰。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_by_month.png")
print("ok")
