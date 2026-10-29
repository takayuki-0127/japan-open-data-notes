"""図（5枚）"""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from f119common import ROOT

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP"], "axes.unicode_minus": False, "figure.dpi": 130,
                     "axes.spines.top": False, "axes.spines.right": False, "savefig.bbox": "tight"})
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, GREEN, GRAY, INK = "#2a78d6", "#eb6834", "#3aa07a", "#9aa0a6", "#202124"


def src(fig, t):
    fig.text(0.01, -0.03, t, fontsize=7, color=GRAY, ha="left", va="top")


# 図1 答え合わせの一覧（時期）
fig, ax = plt.subplots(figsize=(9, 3.8))
items = [("F22 電力（1時間ごと）", "2026-10-01", "2026-10-28", True),
         ("F92 電力のピークの上振れ", "2026-10-01", "2026-10-28", True),
         ("F55 出生数（1〜5月）", "2026-07-10", "2026-10-06", True),
         ("F86 平均寿命（2025年）", "2026-07-25", "2026-07-25", True),
         ("F13 失業率（9・10月）", "2026-10-30", "2026-11-28", False),
         ("F18 GDP（7-9月期）", "2026-11-16", "2026-11-16", False),
         ("F55 出生数（2026年の年間）", "2027-06-05", "2027-06-05", False),
         ("F86 平均寿命（2026年）", "2027-07-25", "2027-07-25", False)]
for i, (lab, a, b, done) in enumerate(items[::-1]):
    a, b = pd.Timestamp(a), pd.Timestamp(b)
    c = GREEN if done else GRAY
    if a == b:
        ax.plot(a, i, "o", color=c, ms=8)
    else:
        ax.plot([a, b], [i, i], color=c, lw=6, solid_capstyle="round")
    ax.text(pd.Timestamp("2026-06-01"), i, lab, va="center", ha="right", fontsize=9)
ax.axvspan(pd.Timestamp("2026-10-22"), pd.Timestamp("2026-10-29"), color=ORANGE, alpha=.15)
ax.text(pd.Timestamp("2026-11-02"), -0.9, "← 記事を作った週（10/22〜28）", color=ORANGE, ha="left", fontsize=8)
ax.set_ylim(-1.3, len(items) - .4)
ax.set_yticks([]); ax.set_xlim(pd.Timestamp("2026-06-01"), pd.Timestamp("2027-08-15"))
ax.spines["left"].set_visible(False)
ax.set_title("実績が出た予測（緑）と、まだ出ていない予測（灰色）：実績の公表時期", fontsize=11, loc="left")
src(fig, "公表時期は各統計の公表日（未公表分は例年の時期からの見込み）")
fig.savefig(FIG / "fig1_timeline.png"); plt.close(fig)

# 図2 電力（1時間ごと）
p = pd.read_csv(RES / "power_oct2026_hourly_pred.csv", index_col=0, parse_dates=True)
M = pd.read_csv(RES / "power_oct2026_hourly_metrics.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"width_ratios": [2.2, 1]})
w = p.loc["2026-10-19":"2026-10-28"]
a1.plot(w.index, w.actual / 1000, color=INK, lw=1.4, label="実績")
a1.plot(w.index, w.lgbm / 1000, color=GREEN, lw=1.1, label="LightGBM（9月30日までで学習）")
a1.plot(w.index, w.naive_week / 1000, color=GRAY, lw=.9, ls="--", label="1週間前の同じ時刻")
a1.set_ylabel("需要（GW）"); import matplotlib.dates as mdates; a1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d")); a1.legend(fontsize=8, frameon=False, loc="upper left")
a1.set_title("記事のあとの10日間（10月19〜28日）", fontsize=10, loc="left")
h = M[M.設定.str.contains("バックテスト") & (M.model == "lgbm")].copy()
h["年"] = h.設定.str[:4]
a2.bar(h.年, h["MAPE(%)"], color=GRAY, label="過去の10月")
now = M[(M.設定.str.startswith("基本")) & (M.model == "lgbm")]["MAPE(%)"].iloc[0]
a2.bar(["2026"], [now], color=GREEN, label="2026年10月（記事のあと）")
for x, v in zip(list(h.年) + ["2026"], list(h["MAPE(%)"]) + [now]):
    a2.text(x, v + .03, f"{v:.2f}", ha="center", fontsize=8)
a2.set_ylabel("平均の外れ（MAPE, %）"); a2.set_title("LightGBM の10月の外れ", fontsize=10, loc="left")
a2.legend(fontsize=7, frameon=False, loc="lower right")
src(fig, "出典：東京電力パワーグリッド「エリア需給実績データ」、気象庁「過去の気象データ」をもとに作成者が加工して作成。気温は実測値を使用")
fig.savefig(FIG / "fig2_power_hourly.png"); plt.close(fig)

# 図3 ピークの上振れ
q = pd.read_csv(RES / "power_oct2026_peak_pred.csv", parse_dates=["date"])
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.fill_between(q.date, q.point / 1000, q["conf_0.99"] / 1000, color=BLUE, alpha=.12, label="99%の上限まで")
ax.plot(q.date, q["conf_0.95"] / 1000, color=BLUE, lw=1.2, label="95%の上限（点予測＋残差の分位点）")
ax.plot(q.date, q.point / 1000, color=GRAY, lw=1, ls="--", label="点予測")
ax.plot(q.date, q.actual / 1000, "o-", color=INK, ms=3.5, lw=1, label="実績のピーク")
ax.set_ylabel("1日のピーク需要（GW）"); import matplotlib.dates as mdates; ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper right")
ax.set_title("F92 の上振れの見込みと、記事のあとの10月の実績（28日すべてが95%の上限以下）", fontsize=10, loc="left")
src(fig, "出典：東京電力パワーグリッド「エリア需給実績データ」、気象庁「過去の気象データ」をもとに作成者が加工して作成")
fig.savefig(FIG / "fig3_power_peak.png"); plt.close(fig)

# 図4 出生数
mm = pd.read_csv(RES / "births_monthly_2026.csv")
B = pd.read_csv(RES / "births_jan_may_2026.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [2, 1]})
x = np.arange(5)
for k, (mname, col, dx) in enumerate([("BSTS", BLUE, -.12), ("SARIMA", ORANGE, .12)]):
    g = mm[mm.model == mname]
    a1.errorbar(x + dx, g.中央値 / 1e4, yerr=[(g.中央値 - g["95%下"]) / 1e4, (g["95%上"] - g.中央値) / 1e4],
                fmt="o", color=col, capsize=3, label=f"{mname} の予測（95%区間）")
g = mm[mm.model == "BSTS"]
a1.plot(x, g["実績(確定ベースに直した値)"] / 1e4, "D", color=INK, ms=6, label="実績（概数を確定数ベースに直した値）")
a1.set_xticks(x); a1.set_xticklabels([f"{i}月" for i in range(1, 6)])
a1.set_ylabel("出生数（万人）"); a1.legend(fontsize=7.5, frameon=False, loc="upper left")
a1.set_title("2026年1〜5月の月ごと", fontsize=10, loc="left")
b = B[B.直し方.str.contains("基本")]
for i, (_, r) in enumerate(b.iterrows()):
    col = BLUE if r.model == "BSTS" else ORANGE
    a2.errorbar(i, r.予測の中央値 / 1e4, yerr=[[(r.予測の中央値 - r["95%下"]) / 1e4], [(r["95%上"] - r.予測の中央値) / 1e4]],
                fmt="o", color=col, capsize=4)
    a2.text(i + .08, r.予測の中央値 / 1e4, f"{r['誤差(%)']:+.1f}%", fontsize=8, color=col, va="center")
a2.axhline(b["実績(1〜5月)"].iloc[0] / 1e4, color=INK, lw=1.2)
a2.text(-.4, b["実績(1〜5月)"].iloc[0] / 1e4 + .1, "実績", fontsize=8)
a2.set_xticks([0, 1]); a2.set_xticklabels(["BSTS", "SARIMA"]); a2.set_xlim(-.6, 1.6)
a2.set_ylabel("1〜5月の合計（万人）"); a2.set_title("1〜5月の合計", fontsize=10, loc="left")
src(fig, "出典：厚生労働省「人口動態統計（確定数）」「人口動態統計月報（概数）」をもとに作成者が加工して作成。概数は2025年1〜5月の確定数÷概数の比（1.0117）で確定数ベースに直した")
fig.savefig(FIG / "fig4_births.png"); plt.close(fig)

# 図5 平均寿命
E = pd.read_csv(RES / "e0_2025_check.csv")
fig, axs = plt.subplots(1, 2, figsize=(10, 3.4))
for ax, (_, r) in zip(axs, E.iterrows()):
    ax.plot([r["95%下"], r["95%上"]], [2, 2], color=BLUE, lw=2, alpha=.4)
    ax.plot([r["80%下"], r["80%上"]], [2, 2], color=BLUE, lw=6, alpha=.6)
    ax.plot(r["Lee–Carter 中央"], 2, "o", color=BLUE)
    ax.plot(r["過去10年の伸びを延ばす"], 1, "s", color=GRAY)
    ax.plot(r["前年のまま"], 0, "s", color=GRAY)
    ax.axvline(r["実績2025（簡易生命表）"], color=INK, lw=1.2)
    ax.text(r["実績2025（簡易生命表）"], 2.45, f"実績 {r['実績2025（簡易生命表）']:.2f}", ha="center", fontsize=8)
    ax.set_yticks([0, 1, 2]); ax.set_yticklabels(["前年（2024年）のまま", "過去10年の伸びを延ばす", "Lee–Carter（F86）"])
    ax.set_ylim(-.5, 2.8); ax.set_title(f"{r.sex}の平均寿命（2025年）", fontsize=10, loc="left")
    ax.set_xlabel("年")
src(fig, "出典：厚生労働省「令和7年簡易生命表」、国立社会保障・人口問題研究所「日本版死亡データベース」をもとに作成者が加工して作成。太い帯は80%、細い線は95%の予測区間")
fig.tight_layout(); fig.savefig(FIG / "fig5_e0.png"); plt.close(fig)
print("ok")
