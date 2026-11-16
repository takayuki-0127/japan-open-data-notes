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
SRC = "出典：気象庁「過去の気象データ検索」（年ごとの値）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
ym = pd.read_csv(R / "yearly.csv").set_index("year")
T = pd.read_csv(R / "station_table.csv")
B = pd.read_csv(R / "requestion_baseline.csv")
ma = lambda s: s.rolling(5, center=True, min_periods=3).mean()
GC = {"rural": C[0], "city": C[1], "cold": C[2]}
GL = {"rural": "15地点", "city": "大都市", "cold": "寒い地域の6地点"}

# ---- 図1：冬日の推移 ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("rural10_mean", f"15地点（冬日10日以上の{len(main['rural10_stations'])}地点）の平均", C[0]), ("city10_mean", "大都市11地点の平均", C[1])]:
    ax.plot(ym.index, ym[col], color=c, lw=0.8, alpha=0.35)
    ax.plot(ym.index, ma(ym[col]), color=c, lw=2.4, label=lab + "（5年移動平均）")
ax.set_xlim(1961, 2025); ax.set_ylim(0, 95)
ax.set_ylabel("冬日（日最低気温0℃未満）の日数（日/年）")
ax.legend(loc="upper right", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"冬日は15地点で{main['rural10_fuyubi_a_mean']:.0f}日→{main['rural10_fuyubi_b_mean']:.0f}日、大都市で{main['city10_fuyubi_a_mean']:.0f}日→{main['city10_fuyubi_b_mean']:.0f}日", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：日数は1961〜1990年と1996〜2025年の地点の平均。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig1_fuyubi.png")

# ---- 図2：真冬日（5日以上の地点、北から南の区分ごと） ----------------------------------------------
M = T[T.station.isin(main["mafuyu5_stations"])].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, r in M.iterrows():
    ax.plot([r.days_tmax_lt0_a, r.days_tmax_lt0_b], [i, i], color=GRID, lw=3, zorder=1)
    ax.scatter([r.days_tmax_lt0_a], [i], s=60, color=C[0], zorder=2, label="1961〜1990年" if i == 0 else None)
    ax.scatter([r.days_tmax_lt0_b], [i], s=60, color=C[1], zorder=3, label="1996〜2025年" if i == 0 else None)
    ax.text(r.days_tmax_lt0_a + 2, i, f"{r.days_tmax_lt0_pct:+.0f}%".replace("-", "−"), va="center", fontsize=8.6, color=INK)
ax.set_yticks(range(len(M))); ax.set_yticklabels([f"{s}（{GL[g]}）" for s, g in zip(M.station, M.group)], fontsize=8.6); ax.invert_yaxis()
ax.set_xlim(0, 92); ax.set_xlabel("真冬日（日最高気温0℃未満）の日数（日/年、30年の平均）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"真冬日の減り方の割合（中央値−{abs(main['mafuyu_pct_median']):.0f}%）は、冬日（−{abs(main['fuyubi_pct_median_same_stations']):.0f}%）の倍", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：真冬日が年5日以上ある地点。区分の中は北から南の順。数字は30年の平均の変化の割合。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.24, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig2_mafuyubi.png")

# ---- 図3：もともとの冬日と減った日数 ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for g, c in GC.items():
    b = B[B.group == g]
    ax.scatter(b.days_tmin_lt0_a, b.drop_days, s=45, color=c, edgecolors="#fcfcfb", linewidths=0.8, label=GL[g], zorder=3)
xx = np.linspace(B.days_tmin_lt0_a.min(), B.days_tmin_lt0_a.max(), 100)
ax.plot(xx, np.polyval(req["coef"], xx), color=INK2, lw=1, ls="--")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("1961〜1990年の冬日の平均（日/年）"); ax.set_ylabel("1996〜2025年までに減った冬日（日/年）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"冬日が年{req['largest_drop_at_baseline_days']:.0f}日ほどの地点で最も減る。とても寒い地点は減りにくい", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：冬日が年10日以上の30地点。点線は2次の式の当てはめ。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_baseline_drop.png")

# ---- 図4：年の最低気温と最低気温の年平均の上がり方（15地点） ---------------------------------------------------
U = T[T.group == "rural"].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.8, 5.0))
y = np.arange(len(U)); h = 0.38
ax.barh(y - h / 2, U.tmin_lowest_slope, height=h, color=C[1], label=f"年の最低気温（中央値 {main['rural_lowest_slope_median']:.2f}）")
ax.barh(y + h / 2, U.tmin_mean_slope, height=h, color=C[0], label=f"日最低気温の年平均（中央値 {main['rural_tminmean_slope_median']:.2f}）")
ax.set_yticks(y); ax.set_yticklabels(U.station, fontsize=8.8); ax.invert_yaxis()
ax.set_xlabel("上がり方（℃/10年、1961〜2025年）"); ax.set_xlim(0, 0.9)
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("いちばん寒い朝の気温は、ふだんの朝より速く上がった（15地点の中央値）", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：15地点、北から南の順。Theil–Sen の傾き。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig4_lowest_vs_mean.png")
print("ok")
