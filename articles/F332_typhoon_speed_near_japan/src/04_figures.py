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
SRC = "出典：気象庁 RSMC Tokyo「ベストトラック」をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
MM = M["main"]
P0, P1 = "1977〜2000年", "2001〜2025年"


def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)


# fig1 年平均の速さ
Y = pd.read_csv(RES / "yearly.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(Y.year, Y.speed, color=C[0], lw=1.4, marker="o", ms=3)
ax.plot(Y.year, Y.speed.rolling(11, center=True, min_periods=6).mean(), color="#0b0b0b", lw=2.2, label="11年移動平均")
ax.hlines(MM["speed0"], 1977, 2000, color=C[1], lw=2, ls="--")
ax.hlines(MM["speed1"], 2001, 2025, color=C[1], lw=2, ls="--")
ax.text(1977.5, 8, f"{P0}の平均 時速{MM['speed0']:.1f}km", fontsize=8.5, color=INK2)
ax.text(2001.5, 8, f"{P1}の平均 時速{MM['speed1']:.1f}km（{MM['chg_pct']:+.1f}%）", fontsize=8.5, color=INK2)
ax.set_ylim(0, None)
ax.set_xlabel("年"); ax.set_ylabel("日本付近での動く速さ（km/時、年平均）")
ax.set_title(f"日本付近の台風は少し遅くなったが、年ごとの差が大きい（傾向 p={MM['trend_p']:.2f}）", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_speed_trend.png", "北緯30〜45度・東経128〜148度を通る6時間ごとの区間（温帯低気圧に変わった後は除く）の平均。台風の強さに達したものだけ")

# fig2 緯度帯ごと（2期間を点で）
L = pd.read_csv(RES / "speed_by_lat.csv")
L = L[L.latb < 42.5]
fig, ax = plt.subplots(figsize=(8, 4.6))
yy = np.arange(len(L))
for i, r in enumerate(L.itertuples()):
    ax.plot([r[2], r[3]], [i, i], color="#b9b7b0", lw=2, zorder=1)
ax.scatter(L["1977-2000"], yy, s=70, color=C[0], edgecolor="white", linewidth=1.5, zorder=3, label=P0)
ax.scatter(L["2001-2025"], yy, s=70, color=C[1], edgecolor="white", linewidth=1.5, zorder=3, label=P1)
for i, r in enumerate(L.itertuples()):
    ax.text(max(r[2], r[3]) + 0.8, i, f"{100 * (r[3] / r[2] - 1):+.0f}%", va="center", fontsize=8.5, color=INK2)
ax.set_yticks(yy, [f"北緯{b:.1f}〜{b + 2.5:.1f}度" for b in L.latb]); ax.grid(axis="y", visible=False)
ax.set_xlim(20, 50); ax.set_xlabel("動く速さ（km/時、区間の平均）")
ax.set_title("遅くなったのは、本州付近より北（北緯35度以北）が中心", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.17, left=0.2, right=0.98, top=0.9)
save(fig, "fig2_by_latitude.png", "東経128〜148度。北緯42.5〜45度は区間が少ないため図から省いた（表は results/speed_by_lat.csv）")

# fig3 月ごと
Mo = pd.read_csv(RES / "speed_by_month.csv")
Mo = Mo[Mo.month.between(6, 10)]
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(Mo))
for i, r in enumerate(Mo.itertuples()):
    ax.plot([i, i], [getattr(r, "_2"), getattr(r, "_3")], color="#b9b7b0", lw=2, zorder=1)
ax.scatter(x, Mo["mean_1977-2000"], s=70, color=C[0], edgecolor="white", linewidth=1.5, zorder=3, label=P0)
ax.scatter(x, Mo["mean_2001-2025"], s=70, color=C[1], edgecolor="white", linewidth=1.5, zorder=3, label=P1)
for i, r in enumerate(Mo.itertuples()):
    ax.text(i - 0.1, min(r._2, r._3) - 4, f"区間 {int(r._4)}→{int(r._5)}", fontsize=7.5, color=INK2, va="center", ha="center")
ax.set_xticks(x, [f"{m}月" for m in Mo.month]); ax.set_ylim(0, 60); ax.grid(axis="x", visible=False)
ax.set_ylabel("動く速さ（km/時、区間の平均）")
ax.set_title("8月はもともと遅く変わらず、9〜10月に遅くなった", loc="left")
ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2)
fig.subplots_adjust(bottom=0.14, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_by_month.png", "北緯30〜45度・東経128〜148度。5月以前と11月以降は区間が少ないため省いた")

# fig4 頑健性（10年あたりの変化と95%信頼区間：月・緯度帯をそろえた回帰）
R = pd.read_csv(RES / "robustness.csv")
lab = ["基本", "箱を広げる", "箱を狭める", "温帯低気圧化の後も含む", "1951年から", "（中央値の行は基本と同じ回帰）"]
R = R.iloc[:5]
fig, ax = plt.subplots(figsize=(8, 4.4))
yy = np.arange(len(R))[::-1]
ax.errorbar(R.fe_decade, yy, xerr=1.96 * R.fe_se, fmt="o", color=C[0], ecolor=C[0], ms=8, capsize=0, lw=2,
            markeredgecolor="white")
for yi, r in zip(yy, R.itertuples()):
    ax.text(r.fe_decade, yi + 0.22, f"{r.fe_decade:+.1f}（p={r.fe_p:.3f}）", ha="center", fontsize=8.5, color=INK2)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(yy, lab[:5]); ax.grid(axis="y", visible=False); ax.set_ylim(-0.5, len(R) - 0.3)
ax.set_xlabel("動く速さの10年あたりの変化（km/時、月と緯度帯をそろえた回帰、95%信頼区間）")
ax.set_title("設定によって、はっきりしたりしなかったりする", loc="left")
fig.subplots_adjust(bottom=0.2, left=0.24, right=0.98, top=0.9)
save(fig, "fig4_robustness.png", "年でクラスター頑健標準誤差。箱：基本 北緯30〜45度・東経128〜148度、広げる 25〜45度・120〜150度、狭める 30〜40度・128〜145度")
