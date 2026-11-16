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
SRC = "出典：気象庁「生物季節観測累年値（さくらの開花）」「日本の月平均気温偏差」「過去の気象データ検索（月平均気温）」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
MM = M["main"]


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 開花日の平年差と、全国の2〜3月の気温偏差（2段）
Y = pd.read_csv(RES / "yearly.csv")
fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True)
a1.plot(Y.year, Y.anom, color=C[4], lw=1.4, marker="o", ms=3)
r1 = Y.anom.rolling(11, center=True, min_periods=6).mean()
a1.plot(Y.year, r1, color="#0b0b0b", lw=2.2, label="11年移動平均")
a1.axhline(0, color=INK2, lw=0.7)
a1.set_ylabel("開花日の差（日）\n＋は遅い、−は早い"); a1.invert_yaxis()
a1.legend(frameon=False, fontsize=8.5, loc="lower left")
a1.set_title("開花日（50地点の平均との差）は、2〜3月の全国の気温と鏡写しに動く", loc="left")
a2.plot(Y.year, Y.N, color=C[1], lw=1.4, marker="o", ms=3)
a2.plot(Y.year, Y.N.rolling(11, center=True, min_periods=6).mean(), color="#0b0b0b", lw=2.2)
a2.axhline(0, color=INK2, lw=0.7)
a2.set_ylabel("全国の2〜3月の\n気温偏差（℃）"); a2.set_xlabel("年")
a2.text(0.01, 0.95, f"年ごとの相関 {M['corr_year_anom_N']:.2f}（上の図は縦軸を上下逆にしている）", transform=a2.transAxes,
        fontsize=8.5, color=INK2, va="top")
fig.subplots_adjust(bottom=0.14, left=0.13, right=0.98, top=0.93, hspace=0.12)
save(fig, "fig1_trend.png", "気温偏差は都市化の影響が少ない15地点の平均（1991〜2020年平均との差）。開花日は1961〜2025年に50年以上値がある50地点（ソメイヨシノ）")

# fig2 早まりの分け方（横棒、0から）
lab = ["開花の早まり（実際）", "全国並みの温暖化の分", "地点の上乗せの分", "残り（説明できない分）"]
val = [MM["d_doy_mean"], MM["by_N_mean"], MM["by_U_mean"], MM["rest_mean"]]
col = ["#0b0b0b", C[1], C[0], "#b9b7b0"]
fig, ax = plt.subplots(figsize=(8, 4.2))
y = np.arange(len(lab))[::-1]
ax.barh(y, val, color=col, height=0.55)
for yi, v in zip(y, val):
    ax.text(v - 0.1, yi, f"{v:+.1f}日", ha="right", va="center", fontsize=9.5, color="#0b0b0b")
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(y, lab); ax.set_xlim(-7.5, 0.5); ax.grid(axis="y", visible=False)
ax.set_xlabel("1961〜1990年平均 → 1996〜2025年平均の変化（日、48地点の平均）")
ax.set_title(f"5.8日の早まりのうち、{-MM['by_N_mean']:.1f}日は全国並みの温暖化、{-MM['by_U_mean']:.1f}日は地点の上乗せで説明できる",
             loc="left", fontsize=10)
fig.subplots_adjust(bottom=0.24, left=0.24, right=0.98, top=0.9)
save(fig, "fig2_decompose.png",
     f"2〜3月の気温1℃あたりの早まり（地点固定効果つき回帰）：全国並みの分 {-MM['b_N']:.1f}日、上乗せの分 {-MM['b_U']:.1f}日。上乗せには都市化のほか、観測場所の移転なども含まれる")

# fig3 地点ごと：上乗せの傾向 × 開花の傾向
S = pd.read_csv(RES / "station_trends.csv", dtype={"st": str})
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(S.trend_U, S.trend_doy, s=42, color=C[0], edgecolor="white", linewidth=1.2, zorder=3)
k = np.polyfit(S.trend_U, S.trend_doy, 1)
xx = np.linspace(S.trend_U.min(), S.trend_U.max(), 10)
ax.plot(xx, np.polyval(k, xx), color=INK2, lw=1, ls="--")
show = ["東京", "大阪", "名古屋", "福岡", "札幌", "京都", "宇都宮", "鹿児島", "室蘭", "輪島", "神戸", "徳島"]
for _, r in S[S.name.isin(show)].iterrows():
    ax.annotate(r["name"], (r.trend_U, r.trend_doy), xytext=(4, 3), textcoords="offset points", fontsize=8, color=INK2)
ax.axhline(0, color=INK2, lw=0.7); ax.axvline(0, color=INK2, lw=0.7)
ax.set_xlabel("地点の上乗せの傾向（2〜3月、10年あたり℃）")
ax.set_ylabel("開花日の傾向（10年あたり日）")
ax.set_title(f"上乗せが大きい地点ほど早まりがやや大きいが、ばらつきが大きい（順位相関 {MM['rho_U_doy']:.2f}）", loc="left", fontsize=10)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.92)
save(fig, "fig3_station_scatter.png", "傾向は Theil–Sen 推定（1961〜2025年）。50地点。破線は最小二乗の直線")

# fig4 もともとの暖かさ × 気温への反応
fig, ax = plt.subplots(figsize=(8, 5))
q = M["h5"]["q75_T"]
w = S.mean_T >= q
ax.scatter(S.mean_T[~w], -S.sens[~w], s=42, color=C[2], edgecolor="white", linewidth=1.2, zorder=3, label="ほかの地点")
ax.scatter(S.mean_T[w], -S.sens[w], s=42, color=C[3], edgecolor="white", linewidth=1.2, zorder=3, label="2〜3月が暖かい上位4分の1")
for _, r in S[S.name.isin(["鹿児島", "宮崎", "東京", "札幌", "長崎", "仙台", "高知", "銚子"])].iterrows():
    ax.annotate(r["name"], (r.mean_T, -r.sens), xytext=(4, 3), textcoords="offset points", fontsize=8, color=INK2)
ax.axvline(q, color=INK2, lw=0.7, ls=":")
ax.set_ylim(0, None)
ax.set_xlabel("2〜3月の平均気温（1961〜2025年の平均、℃）")
ax.set_ylabel("2〜3月が1℃高い年に早まる日数")
ax.set_title(f"暖かい地点ほど、気温1℃あたりの早まりは小さい（中央値 {-M['h5']['sens_warm_median']:.1f}日 と {-M['h5']['sens_other_median']:.1f}日）",
             loc="left", fontsize=10)
ax.legend(frameon=True, facecolor="white", edgecolor="none", fontsize=8.5, loc="lower left", markerscale=1.2, scatterpoints=1)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.92)
save(fig, "fig4_warm_sites.png", "地点ごとに、開花日を2〜3月の平均気温に回帰した傾き（最小二乗）")
