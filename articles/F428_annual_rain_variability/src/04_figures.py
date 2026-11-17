"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：気象庁「日本の年平均降水量偏差」「過去の気象データ検索（年ごとの値）」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
nat = pd.read_csv(D / "national.csv").set_index("year").anom_mm
roll = pd.read_csv(R / "national_rolling.csv").set_index("year")
per = pd.read_csv(R / "periods.csv")
ex = pd.read_csv(R / "extreme_years.csv")

# 図1 全国の偏差と30年移動標準偏差
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.bar(nat.index, nat.values, color=[C[0] if v >= 0 else C[1] for v in nat.values], width=0.8)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("年降水量の偏差（mm、1991〜2020年平均との差）")
ax2 = ax.twinx()
ax2.plot(roll.index, roll.sd30, color=INK, lw=2.2, label="30年移動標準偏差（右軸）")
ax2.set_ylim(0, 420); ax2.set_ylabel("30年移動標準偏差（mm）"); ax2.spines["top"].set_visible(False)
ax2.legend(frameon=False, loc="upper right", fontsize=9)
ax.set_ylim(-520, 420)
style(ax)
ax.set_title(f"ばらつきは1987年ごろを中心とする30年が最大（{m['rolling_sd_max']:.0f}mm）で、その後小さくなった", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.9, top=0.91, bottom=0.17)
save(fig, F / "fig1_national_anomaly.png", SRC, "注：国内51地点の平均。移動標準偏差は前後30年の窓の中心の年に置いた。")

# 図2 30年ごとの標準偏差と四分位範囲
fig, ax = plt.subplots(figsize=(8.8, 4.8))
p = per[per.period != "1898-1930"].reset_index(drop=True)
x = np.arange(len(p))
ax.bar(x - 0.2, p.sd, 0.4, color=C[0], label="標準偏差")
ax.bar(x + 0.2, p.iqr, 0.4, color=C[3], label="四分位範囲（外れ値に強い）")
for i, r in p.iterrows():
    ax.text(i - 0.2, r.sd + 4, f"{r.sd:.0f}", ha="center", fontsize=9)
    ax.text(i + 0.2, r.iqr + 4, f"{r.iqr:.0f}", ha="center", fontsize=9)
ax.set_xticks(x, [s.replace("-", "〜") + "年" for s in p.period])
ax.set_ylabel("全国の年降水量偏差のばらつき（mm）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"標準偏差は1901〜30年{m['sd_1901_1930']:.0f}mm→1971〜2000年{m['sd_1971_2000']:.0f}mm→1996〜2025年{m['sd_1996_2025']:.0f}mm", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.14)
save(fig, F / "fig2_period_spread.png", SRC, f"注：Levene 検定の p 値は、1901〜30年 対 1971〜2000年で{m['levene_p_early_vs_7100']:.3f}、1971〜2000年 対 1996〜2025年で{m['levene_p_7100_vs_recent']:.2f}。")

# 図3 地点の変動係数
st = pd.read_csv(R / "station_cv.csv")
fig, ax = plt.subplots(figsize=(7.2, 6.0))
ax.scatter(st.early * 100, st.late * 100, s=28, color=C[0], alpha=0.8)
lim = [5, 35]
ax.plot(lim, lim, color=INK2, ls="--", lw=0.9)
ax.text(6, 30, "線より上：ばらつきが大きくなった地点", fontsize=9, color=INK2)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("1901〜30年の変動係数（%、標準偏差÷平均）")
ax.set_ylabel("1971〜2000年の変動係数（%）")
style(ax)
ax.set_title(f"{m['station_n']}地点の{m['station_share_larger_0130_to_7100']:.0f}%でばらつきが大きくなった（1901〜30年→1971〜2000年）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.15)
save(fig, F / "fig3_station_cv.png", SRC, f"注：1901〜2025年に110年以上の記録がある地点。1971〜2000年→1996〜2025年（{m["station_n_recent"]}地点）では、大きくなったのは{m["station_share_larger_7100_to_recent"]:.0f}%の地点だけ。")

# 図4 少雨・多雨の年の数
fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = np.arange(len(ex))
ax.bar(x - 0.2, ex.dry_le_m200, 0.4, color=C[1], label="少雨の年（偏差 −200mm 以下）")
ax.bar(x + 0.2, ex.wet_ge_p200, 0.4, color=C[0], label="多雨の年（偏差 +200mm 以上）")
ax.set_xticks(x, [s.replace("-", "〜") + "年" for s in ex.period])
ax.set_ylabel("30年のうちの年数")
ax.set_ylim(0, 8)
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title("1971〜2000年は少雨の年が6回。2008年以降は −200mm 以下の年がない", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.14)
save(fig, F / "fig4_extreme_years.png", SRC, "注：全国（51地点平均）の偏差。少雨の年：1973・78・84・86・94・96・2002・05・07年など。")
