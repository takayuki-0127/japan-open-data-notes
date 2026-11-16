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
ym = pd.read_csv(R / "yearly_group_mean.csv").set_index("year")
T = pd.read_csv(R / "station_slopes.csv")
S = pd.read_csv(R / "urban_share.csv")
P = pd.read_csv(R / "requestion_pairs.csv")
ma = lambda s: s.rolling(5, center=True, min_periods=3).mean()

# ---- 図1：区分の平均 -------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.9))
for col, lab, c in [("city_mean", "大都市11地点の平均", C[1]), ("rural_mean", "都市化の影響が小さい15地点の平均", C[0])]:
    ax.plot(ym.index, ym[col], color=c, lw=0.8, alpha=0.35)
    ax.plot(ym.index, ma(ym[col]), color=c, lw=2.4, label=f"{lab}（5年移動平均）")
ax.set_xlim(1961, 2025); ax.set_ylim(0, 66)
ax.set_ylabel("日最低気温25℃以上の日数（日/年）")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"熱帯夜は大都市で{main['city_tn_1961_1990_mean']:.0f}日→{main['city_tn_1996_2025_mean']:.0f}日、15地点で{main['rural_tn_1961_1990_mean']:.0f}日→{main['rural_tn_1996_2025_mean']:.0f}日", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：日数は1961〜1990年と1996〜2025年の地点の平均。15地点には熱帯夜の多い名瀬・石垣島と、ほとんどない北の地点が含まれる。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_group_mean.png")

# ---- 図2：地点ごとの増え方（北から南の順） ----------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 6.2))
T2 = T.reset_index(drop=True)
for i, r in T2.iterrows():
    c = C[1] if r.group == "city" else C[0]
    ax.barh(i, r.tn_slope, color=c, height=0.65)
    vv = 0.0 if abs(r.tn_slope) < 0.05 else r.tn_slope
    ax.text(max(vv, 0) + 0.15, i, f"{vv:.1f}", va="center", fontsize=8, color=INK)
ax.set_yticks(range(len(T2))); ax.set_yticklabels(T2.station, fontsize=8.6); ax.invert_yaxis()
ax.set_xlim(0, 11); ax.set_xlabel("日最低気温25℃以上の日数の増え方（日/10年、1961〜2025年）")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C[1], label=f"大都市（中央値 {main['city_tn_slope_median']:.2f}）"), Patch(color=C[0], label=f"15地点（中央値 {main['rural_tn_slope_median']:.2f}）")],
          loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"大都市の増え方は15地点の{main['ratio_city_rural']:.1f}倍（中央値）", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：区分ごとに北から南の順。Theil–Sen の傾き。北の地点は熱帯夜がほとんどなく0に近い。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.11, right=0.97, top=0.93, bottom=0.13)
save(fig, "fig2_station_slopes.png")

# ---- 図3：都市の上乗せの見込み -----------------------------------------------------------------------
S2 = S[S.station != "札幌"].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.8, 4.9))
x = np.arange(len(S2))
ax.bar(x, S2.tn_increase_with_rural_rise, color=C[0], width=0.6, label="15地点と同じだけ最低気温が上がった場合の増え方")
ax.bar(x, S2.tn_increase_with_city_rise - S2.tn_increase_with_rural_rise, bottom=S2.tn_increase_with_rural_rise, color=C[1], width=0.6,
       label="その都市の最低気温の上がり方による上乗せ")
for xi, r in S2.iterrows():
    ax.text(xi, r.tn_increase_with_city_rise + 1, f"{r.urban_extra_share_pct:.0f}%", ha="center", fontsize=8.6, color=INK)
ax.set_xticks(x); ax.set_xticklabels(S2.station)
ax.set_ylabel("1961→2025年の熱帯夜の増え方の見込み（日/年）"); ax.set_ylim(0, 75)
ax.legend(loc="upper left", frameon=False, fontsize=8.8)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"上乗せの割合は都市で0〜50%、中央値{main['urban_extra_share_median_pct']:.0f}%", loc="left", fontsize=12)
fig.text(0.01, 0.01, "注：各都市で熱帯夜の日数を日最低気温の年平均で説明する2次の式から見込んだ値。数字は上乗せの割合。札幌は熱帯夜がほとんどないため省いた（中央値には含む）。\n" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, "fig3_urban_extra.png")

# ---- 図4：組での差の増え方 ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8.8, 4.7))
y = np.arange(len(P))
ax.barh(y, P.tn_diff_slope_per_decade, color=[C[1] if v > 0 else C[0] for v in P.tn_diff_slope_per_decade], height=0.6)
for yi, r in P.iterrows():
    v = r.tn_diff_slope_per_decade
    tm = 0.0 if abs(r.tmin_diff_slope_per_decade) < 0.005 else r.tmin_diff_slope_per_decade
    ax.text(max(v, 0) + 0.1, yi, f"{v:+.2f}日（最低気温の差 {tm:+.2f}℃）".replace("-", "−"), va="center", ha="left", fontsize=8.6, color=INK)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(y); ax.set_yticklabels(P.pair); ax.invert_yaxis()
ax.set_xlim(-3, 8.5); ax.set_xlabel("大都市 − 近くの15地点 の熱帯夜の日数の差の増え方（日/10年）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("差が広がった組が多いが、東京・京都・大阪はほとんど広がっていない", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：1961〜2025年、Theil–Sen。かっこ内は日最低気温の年平均の差の増え方（℃/10年）。\n" + SRC, fontsize=7.6, color=INK2)
fig.subplots_adjust(left=0.13, right=0.97, top=0.91, bottom=0.18)
save(fig, "fig4_pairs.png")
print("ok")
