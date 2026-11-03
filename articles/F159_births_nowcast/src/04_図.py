"""F159 04_図：図6枚"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.family"] = "Noto Sans CJK JP"
ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
C = {"A": "#9a9a9a", "B": "#e07a2f", "C": "#7a9e3b", "D": "#2a6f97", "E": "#8e44ad"}
LAB = {"A": "A 年初の予測（F55型）", "B": "B 速報だけ（前年の換算比）", "C": "C 概数だけ",
       "D": "D 速報＋概数（年初からの前年比で延ばす）", "E": "E 速報＋概数＋モデル（残りの月をモデルで）"}
bt = pd.read_csv(RES / "backtest_main.csv")
mae = pd.read_csv(RES / "mae_by_horizon.csv")
xl = [f"{'Y' if h < 12 else 'Y+1'}年\n{(h % 12) + 1}月" for h in range(22)]


def clean(ax):
    ax.spines[["top", "right"]].set_visible(False)


# 図1 その時点で分かっている月数（速報・概数）
fig, ax = plt.subplots(figsize=(9, 4.4))
h = mae.h.values
ax.step(h, mae.ks, where="post", color=C["B"], lw=2.2, label="速報（外国人を含む）：2か月後に公表")
ax.step(h, mae.kg, where="post", color=C["C"], lw=2.2, label="概数（日本人）：約5か月後に公表")
ax.axvline(17.8, color="#555", lw=0.8, ls=":")
ax.text(17.9, 1.0, "年計（概数）\n翌年6月", fontsize=9, color="#555")
ax.axvline(20.97, color="#555", lw=0.8, ls=":")
ax.text(19.2, 4.0, "確定数\n翌年9月末", fontsize=9, color="#555")
ax.set_xticks(range(0, 22, 2), [xl[i] for i in range(0, 22, 2)], fontsize=8)
ax.set_ylabel("その年の何か月分が分かっているか")
ax.set_ylim(0, 12.8)
ax.set_title("Y年の出生数について、各月1日の時点で公表されている月数（2012〜25年の中央値）", fontsize=11)
ax.legend(frameon=False, loc="upper left")
clean(ax)
fig.tight_layout(); fig.savefig(FIG / "fig1_release_timing.png", dpi=150); plt.close(fig)

# 図2 換算比（確定÷速報）
cr = pd.read_csv(RES / "conversion_ratio.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.plot(cr.index, cr.ratio, "o-", color=C["D"], lw=2)
for y in [2005, 2015, 2022, 2023, 2024, 2025]:
    ax.annotate(f"{cr.ratio[y]:.3f}", (y, cr.ratio[y]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
ax.set_ylabel("確定数 ÷ 速報（年計）")
ax.set_title("速報（外国人などを含む）を確定数（日本人）に直す比は、2023・24年に大きく下がった", fontsize=11)
ax.set_xticks(range(2005, 2026, 2))
clean(ax)
fig.tight_layout(); fig.savefig(FIG / "fig2_conversion_ratio.png", dpi=150); plt.close(fig)

# 図3 時点ごとの外れ（MAE）
fig, ax = plt.subplots(figsize=(9.5, 5))
for m in "ABCDE":
    ax.plot(mae.h, mae[f"MAE_{m}"], marker="o" if m in "DE" else None, ms=3.5, color=C[m], lw=2.4 if m == "E" else 1.6,
            ls="--" if m == "A" else "-", label=LAB[m])
ax.set_xticks(range(0, 22, 2), [xl[i] for i in range(0, 22, 2)], fontsize=8)
ax.set_ylabel("年間出生数（確定数）との外れ（平均絶対誤差、%）")
ax.set_title("いつの時点の推計か：速報を足すと、1〜3か月分では悪くなり、夏以降に年初の予測を下回る（2012〜25年）", fontsize=10.5)
ax.legend(frameon=False, fontsize=8.5)
ax.set_ylim(0, 3.0)
clean(ax)
fig.tight_layout(); fig.savefig(FIG / "fig3_mae_by_month.png", dpi=150); plt.close(fig)

# 図4 年ごとの外れ（11月1日時点）
b = bt[bt.h == 10].set_index("year")
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(len(b))
for i, m in enumerate("ADE"):
    ax.bar(x + (i - 1) * 0.26, b[f"err_{m}"], 0.26, color=C[m], label=LAB[m])
ax.axhline(0, color="#333", lw=0.8)
ax.set_xticks(x, b.index)
ax.set_ylabel("外れ（推計÷確定−1、%）")
ax.set_title("その年の11月1日時点（速報8か月・概数5か月）の推計は、確定数とどれだけずれたか", fontsize=11)
ax.legend(frameon=False, fontsize=8.5)
clean(ax)
fig.tight_layout(); fig.savefig(FIG / "fig4_error_by_year_nov.png", dpi=150); plt.close(fig)

# 図5 2026年の推計の推移
p = pd.read_csv(RES / "nowcast_2026_path.csv", parse_dates=["asof"])
p = p[p["asof"] != pd.Timestamp("2026-11-03")].dropna(subset=["B", "C", "D", "E"], how="all")  # 11月3日は11月1日と同じ情報
j = json.load(open(RES / "nowcast_2026.json"))
fig, ax = plt.subplots(figsize=(9.5, 5))
ax.axhspan(j["F55_lo95"] / 1e4, j["F55_hi95"] / 1e4, color="#dddddd", alpha=0.6, label="F55 の予測の95%区間（62.3〜71.4万人）")
ax.axhline(j["F55_median"] / 1e4, color="#777", lw=1, ls="--", label="F55 の予測の中央値（66.3万人）")
ax.axhline(j["actual_2025"] / 1e4, color="#333", lw=1, ls=":", label="2025年の確定数（67.1万人）")
for m in "BCDE":
    ax.plot(p["asof"], p[m] / 1e4, "-o", ms=4, color=C[m], label=LAB[m], lw=2.2 if m == "E" else 1.5)
ax.errorbar([p["asof"].iloc[-1] + pd.Timedelta(days=8)], [j["E"] / 1e4],
            yerr=[[(j["E"] - j["E_lo95"]) / 1e4], [(j["E_hi95"] - j["E"]) / 1e4]], color=C["E"], capsize=4, lw=1.5)
ax.set_ylim(64, 69)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%-m月"))
ax.set_ylabel("2026年の出生数（確定数ベース、万人）")
ax.set_title("2026年の出生数の推計は、公表が進むにつれてどう動いたか（2026年11月3日まで）", fontsize=11)
ax.legend(frameon=False, fontsize=7.8, loc="upper left", ncol=2)
clean(ax)
fig.tight_layout(); fig.savefig(FIG / "fig5_nowcast_2026.png", dpi=150); plt.close(fig)

# 図6 頑健性
r = pd.read_csv(RES / "robustness.csv")
lab = {"換算比=prev": "基本（前年の換算比）", "換算比=avg3": "換算比＝直近3年の平均", "換算比=trend5": "換算比＝5年の傾きで延ばす",
       "概数との差の補正なし": "概数との差で直さない", "延ばし方=直近3か月の前年比": "残りを直近3か月の前年比で延ばす",
       "公表を1か月遅く使う": "公表を1か月遅れで使う"}
hs = [5, 8, 11, 14]
fig, ax = plt.subplots(figsize=(9.5, 4.8))
checks = list(lab)
x = np.arange(len(checks))
cols = ["#c6dbef", "#6baed6", "#2171b5", "#08306b"]
for i, hh in enumerate(hs):
    v = [r[(r.check == c) & (r.h == hh)].MAE_D.iloc[0] for c in checks]
    ax.bar(x + (i - 1.5) * 0.2, v, 0.2, color=cols[i], label=f"{xl[hh].replace(chr(10), '')}1日時点")
ax.set_xticks(x, [lab[c] for c in checks], fontsize=8, rotation=12)
ax.set_ylabel("D の平均絶対誤差（%）")
ax.set_title("D（速報＋概数）の外れ：換算比や延ばし方ではほぼ変わらず、公表の遅れと概数での補正が効く", fontsize=10.5)
ax.legend(frameon=False, fontsize=8.5)
clean(ax)
fig.tight_layout(); fig.savefig(FIG / "fig6_robustness.png", dpi=150); plt.close(fig)
print("ok")
