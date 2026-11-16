"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

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
SRC = "出典：気象庁「過去の梅雨入りと梅雨明け」（梅雨の時期の降水量の地域平均平年比、梅雨入りと梅雨明け）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
MM = M["main"]
NS = ["東北北部", "東北南部", "北陸", "関東甲信", "東海", "近畿", "中国", "四国", "九州北部", "九州南部", "奄美", "沖縄"]  # 北から


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 12地域平均
Y = pd.read_csv(RES / "yearly.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Y.year, Y.mean_ratio, color=C[0], lw=1.4, marker="o", ms=3)
ax.plot(Y.year, Y.mean_ratio.rolling(11, center=True, min_periods=6).mean(), color="#0b0b0b", lw=2.2, label="11年移動平均")
ax.axhline(100, color=INK2, lw=0.8)
ax.hlines(MM["mean0"], 1951, 1987, color=C[1], lw=2, ls="--"); ax.hlines(MM["mean1"], 1988, 2025, color=C[1], lw=2, ls="--")
ax.text(1952, 30, f"1951〜1987年の平均 {MM['mean0']:.1f}%", fontsize=8.5, color=INK2)
ax.text(1989, 30, f"1988〜2025年の平均 {MM['mean1']:.1f}%", fontsize=8.5, color=INK2)
for yv in [2020, 1994]:
    r = Y[Y.year == yv].iloc[0]
    ax.annotate(f"{yv}年 {r.mean_ratio:.0f}%", (yv, r.mean_ratio), xytext=(-55, 8 if r.mean_ratio > 100 else -16), textcoords="offset points", fontsize=8.5, color=INK2)
ax.set_ylim(0, 180)
ax.set_xlabel("年"); ax.set_ylabel("梅雨の時期の降水量の平年比（%、12地域の平均）")
ax.set_title("梅雨の時期の雨量は、長い目で見るとほぼ横ばい", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_national.png", "6〜7月（沖縄・奄美は5〜6月）の降水量の、1991〜2020年平均に対する比。12地域の単純平均")

# fig2 地域×年（発散する色：少ない＝茶、多い＝青、100%＝灰）
D = pd.read_csv(ROOT / "data" / "panel.csv")
D = D[D.year <= 2025]
T = D.pivot(index="region", columns="year", values="ratio").reindex(NS)
cmap = LinearSegmentedColormap.from_list("div", ["#8a5a1f", "#d9b98a", "#eeeeec", "#8fb7e6", "#1d5fb0"])
fig, ax = plt.subplots(figsize=(8, 4.6))
im = ax.imshow(T.values, aspect="auto", cmap=cmap, norm=TwoSlopeNorm(vcenter=100, vmin=20, vmax=200),
               extent=[T.columns.min() - 0.5, T.columns.max() + 0.5, len(NS) - 0.5, -0.5])
ax.set_yticks(range(len(NS)), NS); ax.grid(False)
ax.set_xlabel("年")
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.01); cb.set_label("平年比（%）")
ax.set_title("とても多い年（濃い青）は前半に多く、2020年は8地域で150%以上", loc="left", fontsize=10)
fig.subplots_adjust(bottom=0.17, left=0.11, right=0.93, top=0.9)
save(fig, "fig2_heatmap.png", "地域は北から順に並べた。茶は少ない、青は多い、灰は平年並み")

# fig3 地域ごとの傾向
K = pd.read_csv(RES / "region_trends.csv").set_index("region").reindex(NS)
fig, ax = plt.subplots(figsize=(8, 4.8))
yy = np.arange(len(NS))[::-1]
sig = K.p < 0.05
ax.scatter(K.theil10[~sig], yy[~sig.values], s=60, color="#b9b7b0", edgecolor="white", linewidth=1.2, zorder=3, label="はっきりしない（p≧0.05）")
ax.scatter(K.theil10[sig], yy[sig.values], s=70, color=C[0], edgecolor="white", linewidth=1.2, zorder=3, label="はっきりした（p<0.05）")
for yi, (r, k) in zip(yy, K.iterrows()):
    tv = 0.0 if abs(k.theil10) < 0.05 else k.theil10
    ax.text(k.theil10 + 0.25, yi, f"{tv:+.1f}（p={k.p:.2f}）", va="center", fontsize=8, color=INK2)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(yy, NS); ax.grid(axis="y", visible=False); ax.set_xlim(-5, 6.5)
ax.set_xlabel("平年比の10年あたりの変化（ポイント、Theil–Sen、1951〜2025年）")
ax.set_title("はっきり増えたのは九州南部だけ", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
fig.subplots_adjust(bottom=0.17, left=0.13, right=0.98, top=0.92)
save(fig, "fig3_region_trends.png", "p は Mann–Kendall 検定（年と平年比の Kendall の順位相関）。地域は北から順")

# fig4 梅雨期間の長さと雨量
D2 = D.dropna(subset=["length"]).copy()
D2["r_dm"] = D2.ratio - D2.groupby("region").ratio.transform("mean")
D2["l_dm"] = D2.length - D2.groupby("region").length.transform("mean")
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.scatter(D2.l_dm, D2.r_dm, s=16, color=C[2], alpha=0.6, edgecolor="none")
k = np.polyfit(D2.l_dm, D2.r_dm, 1)
xx = np.linspace(D2.l_dm.min(), D2.l_dm.max(), 10)
ax.plot(xx, np.polyval(k, xx), color="#0b0b0b", lw=1.4, ls="--")
ax.axhline(0, color=INK2, lw=0.7); ax.axvline(0, color=INK2, lw=0.7)
ax.set_xlabel("梅雨の期間の長さ（地域の平均との差、日）")
ax.set_ylabel("平年比（地域の平均との差、ポイント）")
ax.set_title(f"梅雨が長い年ほど雨はやや多いが、関係は弱い（相関 {MM['corr_len']:.2f}）", loc="left")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.92)
save(fig, "fig4_length.png", f"1点が1地域×1年（梅雨入りか明けを特定しなかった年を除く）。破線は最小二乗の直線（10日長いと {10 * k[0]:+.1f} ポイント）")
