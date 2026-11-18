"""図4枚（PNG）。日付などのメタデータは入れない。地点は北から南の順。"""
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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "20261116"})
C1, C2, GRAY = "#2a78d6", "#eb6834", "#9a9893"
INK2, GRID = "#52514e", "#e4e3df"
SRC = "出典：気象庁「過去の気象データ・ダウンロード」（日平均気温の日別値）をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.text(0.01, 0.012, SRC, fontsize=8, color=INK2)
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def md(doy):
    d = pd.Timestamp("2025-01-01") + pd.Timedelta(int(doy) - 1, unit="D")
    return f"{d.month}/{d.day}"


M = json.load(open(R / "main.json", encoding="utf-8"))
Y = pd.read_csv(R / "yearly.csv").set_index("year")
T = pd.read_csv(R / "station_table.csv")
TA = T[T.definition == "abs25_w7"].reset_index(drop=True)
TP = T[T.definition == "p75_w7"].reset_index(drop=True)

# ---- 図1：夏の長さ（本線の地点の平均）の推移 ----------------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 4.6))
y = Y[Y.n_stations >= len(M["stations_main"]) - 1]
ax.plot(y.index, y.len_mean, color=GRAY, lw=0.8, label="年ごとの値")
ax.plot(Y.index, Y.len_mean_11yr, color=C1, lw=2.2, label="前後11年の平均")
for (a, b), v in [((1901, 1930), M["yearly_len_mean_1901_1930"]), ((1996, 2025), M["yearly_len_mean_1996_2025"])]:
    ax.hlines(v, a, b, color=C2, lw=2)
    ax.text((a + b) / 2, v - 5, f"{a}〜{b}年 平均{v:.0f}日", ha="center", va="top", color=C2, fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.2", fc="#fcfcfb", ec="none", alpha=0.9))
ax.set_title(f"夏の長さは、1901〜30年の{M['yearly_len_mean_1901_1930']:.0f}日から最近30年の{M['yearly_len_mean_1996_2025']:.0f}日へ",
             loc="left", fontsize=12.5)
ax.set_ylabel("夏の長さ（日、11地点の平均）")
ax.set_xlabel("年")
ax.grid(axis="y", color=GRID, lw=0.7)
ax.legend(frameon=False, loc="upper left")
ax.text(0.99, 0.03, "夏＝日平均気温の7日移動平均が25℃以上の最初の日から最後の日まで\n都市化の影響が比較的小さい地点のうち、ふだん25℃に届く11地点",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color=INK2)
fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.17)
save(fig, "fig1_length_trend.png")

# ---- 図2：始まりと終わりの日付（地点別、北から南） -----------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 5.6))
n = len(TA)
yy = np.arange(n)[::-1]
for i, r in TA.iterrows():
    ax.plot([r.start_p1, r.end_p1], [yy[i] + 0.17] * 2, color=GRAY, lw=5, solid_capstyle="butt")
    ax.plot([r.start_p2, r.end_p2], [yy[i] - 0.17] * 2, color=C2, lw=5, solid_capstyle="butt")
ax.plot([], [], color=GRAY, lw=5, label="1901〜1930年の平均")
ax.plot([], [], color=C2, lw=5, label="1996〜2025年の平均")
ax.set_yticks(yy, TA.station)
ticks = [121, 152, 182, 213, 244, 274, 305, 335]
ax.set_xticks(ticks, ["5/1", "6/1", "7/1", "8/1", "9/1", "10/1", "11/1", "12/1"])
ax.set_xlim(105, 330)
ax.grid(axis="x", color=GRID, lw=0.7)
ax.set_xlabel("日付（夏の始まり〜終わり）")
ax.set_title(f"始まりは{abs(M['H2_start_diff_median_days']):.0f}日早まり、終わりは{M['H2_end_diff_median_days']:.0f}日遅れた（地点の中央値）",
             loc="left", fontsize=12.5)
ax.legend(frameon=False, loc="upper right")
ax.text(0.0, -0.16, "上から北→南の順。夏＝日平均気温の7日移動平均が25℃以上の期間（届かない年は始まり・終わりの平均から除く）",
        transform=ax.transAxes, fontsize=8.5, color=INK2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.92, bottom=0.2)
save(fig, "fig2_start_end.png")

# ---- 図3：地点ごとの基準での延び（15地点、北から南） ---------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 5.4))
n = len(TP)
yy = np.arange(n)[::-1]
ax.barh(yy, -TP.start_diff, left=0, color=C1, height=0.6, label="始まりが早まった日数")
ax.barh(yy, TP.end_diff, left=-TP.start_diff, color=C2, height=0.6, label="終わりが遅れた日数")
for i, r in TP.iterrows():
    ax.text(r.len_diff + 0.8, yy[i], f"+{r.len_diff:.0f}日", va="center", fontsize=9, color=INK2)
ax.set_yticks(yy, TP.station)
ax.set_xlabel("1901〜1930年→1996〜2025年 の夏の長さの変化（日）")
ax.set_xlim(0, 50)
ax.grid(axis="x", color=GRID, lw=0.7)
ax.set_title(f"地点ごとの基準で見ると、北海道の3地点を含む15地点すべてで延びた（中央値+{M['H3_len_diff_median_all15']:.0f}日）",
             loc="left", fontsize=12)
ax.legend(frameon=False, loc="upper right")
ax.text(0.0, -0.16, "上から北→南の順。夏＝7日移動平均が、その地点の1961〜1990年の日平均気温の上位25%の境（網走14.3℃〜石垣島27.8℃）以上の期間",
        transform=ax.transAxes, fontsize=8.3, color=INK2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.92, bottom=0.2)
save(fig, "fig3_relative_threshold.png")

# ---- 図4：延びる速さ（1901〜1960年と1961〜2025年） ---------------------------------------------
fig, ax = plt.subplots(figsize=(8.4, 5.0))
n = len(TA)
yy = np.arange(n)[::-1]
ax.barh(yy + 0.2, TA.slope_len_1901_1960, height=0.38, color=GRAY, label="1901〜1960年")
ax.barh(yy - 0.2, TA.slope_len_1961_2025, height=0.38, color=C2, label="1961〜2025年")
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy, TA.station)
ax.set_xlabel("夏の長さの傾き（10年あたりの日数、最小二乗法の直線）")
ax.grid(axis="x", color=GRID, lw=0.7)
ax.set_title(f"延びる速さは、1961年以降に10年あたり{M['H4_slope_1901_1960_median']:.1f}日→{M['H4_slope_1961_2025_median']:.1f}日（地点の中央値）",
             loc="left", fontsize=12.5)
ax.set_xlim(0, 7.5)
ax.legend(frameon=False, loc="upper right")
ax.text(0.0, -0.16, "上から北→南の順。夏の定義は図1・図2と同じ（7日移動平均が25℃以上）", transform=ax.transAxes, fontsize=8.5, color=INK2)
fig.subplots_adjust(left=0.1, right=0.98, top=0.92, bottom=0.2)
save(fig, "fig4_pace.png")
print("figures done")
