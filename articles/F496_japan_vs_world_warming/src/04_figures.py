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
SRC = "出典：気象庁「日本の年平均気温」「世界の年平均気温」「海面水温の長期変化傾向（全球平均）」をもとに作成者が加工して作成"
META = {"Software": None}


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
A = pd.read_csv(R / "annual_with_land_est.csv")
S = pd.read_csv(R / "start_year_scan.csv")
W = pd.read_csv(R / "window30.csv")
Q = pd.read_csv(R / "requestion_seasons.csv")

# ---- 図1：日本と世界の偏差 ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
d = A[A.year >= 1891]
x = np.arange(1898, 2026)
for col, lab, c, k in [("japan", "日本（15地点の平均）", C[1], "japan_1898_2025"), ("world", "世界（陸の気温と海面水温の平均）", C[0], "world_1898_2025")]:
    ax.plot(d.year, d[col], color=c, lw=1.1, alpha=0.75, label=f"{lab}：100年あたり {m[k]:.2f}℃")
    dd = d[d.year.between(1898, 2025)].dropna(subset=[col]); p = np.polyfit(dd.year, dd[col], 1)
    ax.plot(x, np.polyval(p, x), color=c, lw=2.2, ls="--")
ax.axhline(0, color=INK2, lw=0.7)
ax.set_xlim(1891, 2025); ax.set_ylabel("1991〜2020年の平均からの差（℃）")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"同じ1898〜2025年でそろえると、日本の上がり方は世界の{m['ratio_world']:.2f}倍", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：破線は1898〜2025年の最小二乗法の直線。日本の年ごとのぶれ（直線からの標準偏差）は0.43℃で、世界（0.17℃）の約2.5倍。\n" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.15)
save(fig, "fig1_japan_world_series.png")

# ---- 図2：始まりの年ごとの倍率 ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
s = S[S.start <= 1990]
ax.plot(s.start, s.ratio_world, color=C[0], lw=2.2, label="世界全体（陸＋海）に対する倍率")
ax.plot(s.start, s.ratio_land, color=C[2], lw=2.2, label="世界の陸（海の割合0.71として逆算した近似）に対する倍率")
ax.axhline(1, color=INK2, lw=0.9)
ax.axhline(m["ratio_pub_japan_to_pub_land"], color=C[3], lw=1.4, ls=":", label=f"公表値どうし：日本1.44÷世界の陸0.93＝{m['ratio_pub_japan_to_pub_land']:.2f}（期間が違う）")
ax.set_xlim(1898, 1990); ax.set_ylim(0.6, 2.2)
ax.set_xlabel("比べ始める年（終わりは2025年）"); ax.set_ylabel("日本の上昇率 ÷ 相手の上昇率（倍）")
ax.legend(loc="upper left", frameon=False, fontsize=8.6)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"世界全体には{m['scan_min_ratio_world']:.1f}〜{m['scan_max_ratio_world']:.1f}倍。陸だけと比べると縮むが、どこまでかは確かめきれない", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：逆算は 世界＝0.71×海面水温＋0.29×陸 とした近似。気象庁の陸上のみの公表値（0.93℃/100年）より大きく出るので、緑の線は倍率を小さめに見せている可能性がある。\n" + SRC, fontsize=7.2, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig2_start_year_ratio.png")

# ---- 図3：30年ごとの差 ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
mid = W.start + 15
ax.fill_between(mid, W.lo90, W.hi90, color=C[3], alpha=0.25, lw=0, label="90%区間（自己相関を考えた幅）")
ax.plot(mid, W["diff"], color=C[3], lw=2.2, label="日本−世界の上昇率の差")
ax.axhline(0, color=INK2, lw=0.9)
ax.set_xlim(1913, 2011); ax.set_ylabel("差（℃/100年）")
ax.set_xlabel("30年の期間の真ん中の年")
ax.legend(loc="upper left", frameon=False, fontsize=9)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"30年で区切ると、{m['win30_n']}の期間のうち{m['win30_cross0']}で差は0と区別できない", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, f"注：1898〜1927年から1996〜2025年まで1年ずつずらした30年の期間。最近の1996〜2025年は日本{m['last30']['japan']:.1f}℃、世界{m['last30']['world']:.1f}℃（100年あたりに換算）。\n" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig3_window30_diff.png")

# ---- 図4：季節ごと ----
fig, ax = plt.subplots(figsize=(8.8, 4.9))
yy = np.arange(len(Q))
ax.barh(yy - 0.18, Q.japan, height=0.34, color=C[1], label="日本")
ax.barh(yy + 0.18, Q.world, height=0.34, color=C[0], label="世界")
for i, r in Q.iterrows():
    ax.text(max(r.japan, r.world) + 0.04, i, f"{r.ratio:.2f}倍", va="center", fontsize=9.5, color=INK)
ax.set_yticks(yy); ax.set_yticklabels(Q.label); ax.invert_yaxis()
ax.set_xlim(0, 2.0); ax.set_xlabel("上昇率（℃/100年、1898〜2025年）")
ax.legend(loc="lower right", frameon=False, fontsize=9)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title("季節で見ると、春と秋の倍率が大きく、冬が小さい", loc="left", fontsize=11.5)
fig.text(0.01, 0.01, "注：冬は前年12月〜2月。倍率は日本÷世界。\n" + SRC, fontsize=7.4, color=INK2)
fig.subplots_adjust(left=0.15, right=0.97, top=0.91, bottom=0.17)
save(fig, "fig4_seasons.png")
print("ok")
