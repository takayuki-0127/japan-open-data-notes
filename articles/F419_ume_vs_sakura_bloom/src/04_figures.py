"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：気象庁「生物季節観測」累年値（うめ・さくらの開花）、「日本の月平均気温偏差」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
ym = pd.read_csv(R / "yearly_mean.csv")
t = pd.read_csv(R / "station_trends.csv")
NAME = {"ume": "うめ", "sakura": "さくら"}

# 図1 年ごとの偏差（地点平均からのずれ）の平均と11年移動平均
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, k in enumerate(["ume", "sakura"]):
    s = ym[ym.kind == k].set_index("year")["mean"]
    ax.plot(s.index, s.values, color=C[i], lw=0.8, alpha=0.45)
    ax.plot(s.index, s.rolling(11, center=True, min_periods=6).mean(), color=C[i], lw=2.4, label=f"{NAME[k]}（11年移動平均）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(1960, 2026)
ax.set_ylabel("開花日の平年からのずれ（日、負は早い）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
style(ax)
ax.set_title(f"1960年代→2016〜25年に、うめは{-m['shift_1960s_to_2016_25_ume']:.1f}日、さくらは{-m['shift_1960s_to_2016_25_sakura']:.1f}日早まった", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig1_yearly_anomaly.png", SRC, f"注：両方の観測がそろう{m['pair_n_pair']}地点。各地点の1961〜2025年の平均からのずれを、年ごとに地点で平均した。細線は年ごとの値。")

# 図2 地点ごとの傾き：うめ vs さくら
w = t.pivot(index="st", columns="kind", values="slope10").dropna()
lat = t.drop_duplicates("st").set_index("st").loc[w.index, "lat"]
fig, ax = plt.subplots(figsize=(7.6, 6.2))
for lab, msk, col in [("北緯36度以北", lat >= 36, C[0]), ("北緯36度より南", lat < 36, C[1])]:
    ax.scatter(w.sakura[msk], w.ume[msk], s=26, color=col, alpha=0.85, label=f"{lab}（{int(msk.sum())}地点）")
lim = [-8, 4.5]
ax.plot(lim, lim, color=INK2, lw=0.9, ls="--")
ax.text(-7.8, -7.3, "線より下：うめの方が速く早まった", fontsize=8.8, color=INK2)
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("さくらの開花の傾き（10年あたりの日数）")
ax.set_ylabel("うめの開花の傾き（10年あたりの日数）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title(f"北ではうめが速く（中央値 {m['north_ume_med']:.1f}日／{m['north_sakura_med']:.1f}日）、\n南ではさくらが速い（{m['south_ume_med']:.1f}日／{m['south_sakura_med']:.1f}日）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.17)
save(fig, F / "fig2_station_slopes.png", SRC, "注：1961〜2025年に正規の種目の観測が40年以上ある地点。傾きは最小二乗法。")

# 図3 うめとさくらの間隔と緯度
mean = t.pivot(index="st", columns="kind", values="mean_doy").dropna()
gap = mean.sakura - mean.ume
la = t.drop_duplicates("st").set_index("st").loc[gap.index, "lat"]
fig, ax = plt.subplots(figsize=(8.4, 5.2))
ax.scatter(la, gap, s=26, color=C[2])
b = np.polyfit(la, gap, 1)
xx = np.array([la.min(), la.max()])
ax.plot(xx, np.polyval(b, xx), color=INK2, lw=1)
ax.set_xlabel("地点の緯度（度）")
ax.set_ylabel("さくらの開花 − うめの開花（日、平均）")
style(ax)
ax.set_title(f"うめとさくらの間は、北緯36度より南で{m['gap_south_med']:.0f}日、以北で{m['gap_north_med']:.0f}日（中央値）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig3_gap_latitude.png", SRC, f"注：{len(gap)}地点、1961〜2025年の平均。順位の相関 {m['gap_lat_spearman']:.2f}。")

# 図4 実際の傾きと、気温から見込まれる傾き
fig, ax = plt.subplots(figsize=(8.8, 5.0))
labs, act, imp = [], [], []
for k in ["ume", "sakura"]:
    for y0 in (1961, 1991):
        labs.append(f"{NAME[k]}\n{y0}〜2025年")
        act.append(q[f"{k}_bloom_slope10_{y0}"]); imp.append(q[f"{k}_implied_slope10_{y0}"])
x = np.arange(len(labs))
ax.bar(x - 0.18, act, 0.36, color=C[0], label="実際の開花の傾き")
ax.bar(x + 0.18, imp, 0.36, color=C[3], label="咲く前の月の気温から見込まれる傾き")
for xi, v in zip(x - 0.18, act):
    ax.text(xi, v + (0.08 if v >= 0 else -0.22), f"{v:+.1f}", ha="center", fontsize=9)
for xi, v in zip(x + 0.18, imp):
    ax.text(xi, v - 0.22, f"{v:+.1f}", ha="center", fontsize=9)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x, labs)
ax.set_ylabel("10年あたりの日数（負は早まり）")
ax.set_ylim(-2.6, 1.2)
ax.legend(frameon=False, loc="upper right", fontsize=9)
style(ax)
ax.set_title("1991年以降、うめは気温から見込まれるほど早まっていない（実際の傾きはぶれの範囲内）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.91, bottom=0.2)
save(fig, F / "fig4_temp_implied.png", SRC, f"注：見込み＝気温1℃あたりの日数（うめ1〜2月 {q['ume_days_per_degC']:.1f}日、さくら2〜3月 {q['sakura_days_per_degC']:.1f}日）×気温の傾き。気温は都市化の影響が少ない15地点の平均。")
