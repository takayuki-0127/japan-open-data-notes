"""図4枚（PNG）。日付などのメタデータは入れない。地点は北から南の順に並べる（順位は作らない）。"""
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
LAT = {"札幌": 43.06, "仙台": 38.26, "東京": 35.69, "横浜": 35.44, "名古屋": 35.17, "京都": 35.01, "大阪": 34.68, "神戸": 34.70,
       "広島": 34.40, "福岡": 33.58, "鹿児島": 31.55, "網走": 44.02, "根室": 43.33, "寿都": 42.80, "山形": 38.25, "石巻": 38.43,
       "伏木": 36.79, "飯田": 35.52, "銚子": 35.74, "境": 35.54, "浜田": 34.90, "彦根": 35.28, "宮崎": 31.94, "多度津": 34.27,
       "名瀬": 28.38, "石垣島": 24.34}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
Y = pd.read_csv(R / "yearly_group_mean.csv")
T = pd.read_csv(R / "station_slopes.csv")
FT = pd.read_csv(R / "requestion_fit.csv")
ma = lambda s: s.rolling(5, center=True, min_periods=3).mean()

# ---- 図1：相対湿度の区分の平均 ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("rh_city", "大都市11地点の平均", C[1]), ("rh_rural", "都市化の影響が小さい15地点の平均", C[0])]:
    ax.plot(Y.year, Y[col], color=c, lw=0.8, alpha=0.35)
    ax.plot(Y.year, ma(Y[col]), color=c, lw=2.4, label=f"{lab}（5年移動平均）")
ax.set_xlim(1961, 2025); ax.set_ylim(60, 80)
ax.set_ylabel("相対湿度の年平均（％）")
ax.legend(loc="lower left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"相対湿度は大都市で{main['city_rh_1961_1990']:.1f}％→{main['city_rh_1996_2025']:.1f}％、15地点で{main['rural_rh_1961_1990']:.1f}％→{main['rural_rh_1996_2025']:.1f}％", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：数字は1961〜1990年と1996〜2025年の地点の平均。資料不足値の年は除いた。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_rh_group_mean.png")

# ---- 図2：地点ごとの分解（北から南） ----
fig, axes = plt.subplots(1, 2, figsize=(9.6, 6.6), sharex=True)
for ax, grp, ttl in [(axes[0], "city", "大都市11地点"), (axes[1], "rural", "15地点")]:
    d = T[T.group == grp].copy(); d["lat"] = d.station.map(LAT); d = d.sort_values("lat", ascending=False).reset_index(drop=True)
    yy = np.arange(len(d))
    ax.barh(yy - 0.18, d.temp_part, height=0.34, color=C[1], label="気温が上がった分")
    ax.barh(yy + 0.18, d.vapor_part, height=0.34, color=C[0], label="水蒸気（蒸気圧）が変わった分")
    ax.scatter(d.rh_slope, yy, color=INK, s=22, zorder=3, label="相対湿度の実際の変化")
    ax.set_yticks(yy); ax.set_yticklabels(d.station); ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=0.8)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    ax.set_title(ttl, loc="left", fontsize=10.5)
    ax.set_xlabel("相対湿度の変化（ポイント/10年）")
axes[0].set_xlim(-2.4, 2.0)
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper left", bbox_to_anchor=(0.01, 0.955), ncol=3, frameon=False, fontsize=8.6)
fig.suptitle("相対湿度を下げたのは気温の上昇で、水蒸気はほとんどの地点で増えていた（1961〜2025年）", x=0.01, ha="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：地点は北から南の順（順位ではない）。分解は 相対湿度＝蒸気圧÷飽和水蒸気圧（年平均気温から求めた近似）。\n黒い点と2本の棒の合計の差は近似の誤差。傾きは最小二乗法。" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.15, wspace=0.28)
save(fig, "fig2_decomposition.png")

# ---- 図3：蒸気圧の区分の平均 ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("vp_city", "大都市11地点の平均", C[1]), ("vp_rural", "15地点の平均", C[0])]:
    ax.plot(Y.year, Y[col], color=c, lw=0.8, alpha=0.35)
    ax.plot(Y.year, ma(Y[col]), color=c, lw=2.4, label=f"{lab}（5年移動平均）")
ax.set_xlim(1961, 2025); ax.set_ylim(12, 16.5)
ax.set_ylabel("蒸気圧の年平均（hPa）")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"空気中の水蒸気は減っていない：大都市{main['city_vp_1961_1990']:.1f}→{main['city_vp_1996_2025']:.1f}hPa、15地点{main['rural_vp_1961_1990']:.1f}→{main['rural_vp_1996_2025']:.1f}hPa", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：蒸気圧は空気中の水蒸気の量の目安。数字は1961〜1990年と1996〜2025年の地点の平均。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig3_vapor_pressure.png")

# ---- 図4：問い直し（折れ線） ----
fig, axes = plt.subplots(2, 1, figsize=(8.8, 6.6), sharex=True, gridspec_kw={"height_ratios": [1.6, 1]})
ax = axes[0]
for col, lab, c in [("rh_city", "大都市", C[1]), ("rh_rural", "15地点", C[0])]:
    d = FT[FT.series == col]
    ax.plot(d.year, d.value, color=c, lw=0.9, alpha=0.45)
    k = req[col]["break_year"]
    ax.plot(d.year, d.fit, color=c, lw=2.4, label=f"{lab}：{k}年まで {req[col]['slope_before_per10y']:+.2f}、その後 {req[col]['slope_after_per10y']:+.2f}（ポイント/10年）")
ax.set_ylabel("相対湿度（％）"); ax.set_ylim(62, 80)
ax.legend(loc="upper right", frameon=False, fontsize=8.6)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("乾き方は一直線ではなく、2000年代半ばから両方とも戻っている", loc="left", fontsize=11.5)
ax = axes[1]
d = FT[FT.series == "gap"]
ax.plot(d.year, d.value, color=C[3], lw=1.0)
ax.plot(d.year, ma(d.value), color=C[3], lw=2.4, label="大都市−15地点（5年移動平均）")
ax.set_ylabel("差（ポイント）"); ax.set_ylim(-10, -3)
ax.legend(loc="upper right", frameon=False, fontsize=8.6)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_xlim(1961, 2025)
fig.text(0.01, 0.01, f"注：折れ線は折れる年を1975〜2015年から残差が最小になる年に選んだ。差は1961〜1970年の平均{req['gap_1961_1970']:.1f}→2016〜2025年{req['gap_2016_2025']:.1f}ポイント。\n" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.93, bottom=0.12, hspace=0.12)
save(fig, "fig4_requestion_hinge.png")
print("ok")
