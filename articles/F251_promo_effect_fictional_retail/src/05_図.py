"""05 図（サンプルマート（架空）、合成データ）。図6は reports/promo_effect_report.html を playwright で画像にしたもの。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b2b", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, AQUA, GRAY, INK, MUTED, RED = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29d", "#0b0b0b", "#52514e", "#c8423b"
NOTE = "サンプルマート（架空）・合成データ。会社も数字も実在しません。"
m = json.load(open(RES / "main.json"))
A = pd.read_csv(RES / "A_estimates_seed0.csv").set_index("method")
IDX = pd.read_csv(RES / "A_weekly_index_seed0.csv", index_col=0)
EV = pd.read_csv(RES / "A_event_study_seed0.csv")
GAP = pd.read_csv(RES / "A_sc_gap_seed0.csv").set_index("k").gap
S = pd.read_csv(RES / "C_error_summary.csv")
MN = pd.read_csv(RES / "C_money_error.csv").set_index("method")
ORDER = ["M1_前後", "M2_前年比", "M3_前年比の差", "M4_DiD", "M5_DiD傾き", "M6_合成対照"]
LAB = {"M1_前後": "前後比較", "M2_前年比": "前年比", "M3_前年比の差": "前年比の差", "M4_DiD": "差の差",
       "M5_DiD傾き": "差の差＋\n店ごとの傾き", "M6_合成対照": "合成対照"}
TRUE = m["truth"]["promo"]["lift_pct"] * 100


def save(fig, name):
    fig.text(0.01, -0.06, NOTE, fontsize=8, color=MUTED)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


def shade(ax):
    ax.axvspan(-0.5, 7.5, color=ORANGE, alpha=0.10, lw=0)
    ax.axvspan(7.5, 11.5, color=ORANGE, alpha=0.04, lw=0)


# 図1：週の売上（期間の前52週の平均=100）。対象の6店・販促がなかった場合（答え）・対象外の14店
x = IDX.loc[-52:11]
fig, ax = plt.subplots(figsize=(9.4, 4.4))
shade(ax)
ax.plot(x.index, x.control, color=GRAY, lw=1.6, label="対象外の14店（都市・郊外）")
ax.plot(x.index, x.treated_no_promo, color=INK, lw=1.2, ls="--", label="対象の6店：販促がなかった場合（答え）")
ax.plot(x.index, x.treated, color=BLUE, lw=2.0, label="対象の6店（地方）：実際")
ax.text(3.5, ax.get_ylim()[1] * 0.995, "クーポン\n8週", ha="center", va="top", color=ORANGE, fontsize=9.5)
ax.set_xlabel("週（クーポンの1週目＝0、2025-10-06）"); ax.set_ylabel("週の売上（期間の前52週の平均＝100）")
ax.set_title("図1　週の売上：販促で対象の6店が上に離れた分（実線と点線の差）が答え", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper center")
save(fig, "fig1_weekly_index.png")

# 図2：事象研究（週ごとの差、直前の週＝0）
e = EV[EV.trend == 0].set_index("k").coef * 100
fig, ax = plt.subplots(figsize=(9.4, 4.2))
shade(ax)
pre = e[e.index < 0]; post = e[e.index >= 0]
ax.axhline(0, color=MUTED, lw=0.8)
ax.plot(pre.index, pre.values, "o", color=GRAY, ms=3.5, label="期間の前")
c = np.polyfit(pre.index, pre.values, 1)
ax.plot(pre.index, np.polyval(c, pre.index), color=GRAY, lw=1.4, ls="--", label=f"期間の前の直線（1年で {c[0] * 52:+.1f}pt）")
ax.plot(post.index, post.values, "o", color=BLUE, ms=4.5, label="期間・期間の後")
ax.axhline(TRUE, xmin=0.82, xmax=0.95, color=RED, lw=1.5)
ax.text(11.8, TRUE, f"入れた効果\n+{TRUE:.1f}%", color=RED, fontsize=9, va="center")
ax.set_xlabel("週（クーポンの1週目＝0）"); ax.set_ylabel("対象の6店 − 相手（%、直前の週＝0）")
ax.set_title("図2　週ごとに比べると、期間の前に「平行」になっていない", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper center")
save(fig, "fig2_event_study.png")

# 図3：合成対照の差（週ごと）
fig, ax = plt.subplots(figsize=(9.4, 4.2))
shade(ax)
g = GAP.loc[-52:11] * 100
ax.axhline(0, color=MUTED, lw=0.8)
ax.plot(g.index, g.values, color=BLUE, lw=1.8)
ax.plot(g.loc[0:7].index, [g.loc[0:7].mean()] * 8, color=BLUE, lw=3, alpha=0.5)
ax.text(7.8, g.loc[0:7].mean(), f"8週の平均\n{(np.exp(GAP.loc[0:7].mean()) - 1) * 100:+.1f}%", color=BLUE, fontsize=9, va="center")
ax.axhline(TRUE, xmin=0.82, xmax=0.95, color=RED, lw=1.5)
rm = m["sc"]["rmspe_pre"] * 100
ax.fill_between(g.loc[:-1].index, -rm, rm, color=GRAY, alpha=0.25, lw=0, label=f"期間の前の当てはまりの外れ（±{rm:.1f}%）")
w = m["sc"]["weights"]
ax.set_xlabel("週（クーポンの1週目＝0）"); ax.set_ylabel("対象の6店 − 合成した相手（%）")
ax.set_title("図3　合成対照：郊外の店 71%・都市の店 29% の組み合わせを相手にする", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "fig3_synthetic_control_gap.png")

# 図4：測り方ごとの値（乱数の種0）と、20通りの外れの幅
s = S[S.case == "weak_eff"].set_index("method")
fig, ax = plt.subplots(figsize=(9.4, 4.6))
y = np.arange(len(ORDER))[::-1]
for yi, k in zip(y, ORDER):
    b, hw = s.loc[k, "bias"] * 100, s.loc[k, "half90"] * 100
    ax.plot([TRUE + b - hw, TRUE + b + hw], [yi, yi], color=GRAY, lw=7, alpha=0.55, solid_capstyle="butt")
    v = A.loc[k, "promo_lift"] * 100
    ax.plot(v, yi, "o", color=BLUE if k in ("M4_DiD", "M5_DiD傾き", "M6_合成対照") else ORANGE, ms=8, zorder=3)
    ax.text(max(v, TRUE + b + hw) + 0.25, yi, f"{v:+.1f}%（20通りの平均の外れ {b:+.1f}pt）", va="center", fontsize=9)
ax.axvline(TRUE, color=RED, lw=1.5)
ax.text(TRUE, y[0] + 0.65, f"入れた効果 +{TRUE:.1f}%", color=RED, ha="center", fontsize=9.5)
ax.set_yticks(y); ax.set_yticklabels([LAB[k] for k in ORDER])
ax.set_xlim(-1, 13); ax.set_ylim(-0.7, len(ORDER) - 0.1)
ax.set_xlabel("測った効果（期間の8週、%）　●＝今回の値、灰色＝乱数を変えた20通りの90%")
ax.set_title("図4　同じデータでも、測り方で +1.3% 〜 +6.9%", loc="left", fontsize=12)
save(fig, "fig4_estimates_vs_truth.png")

# 図5：お金の勘定（差し引き）
fig, ax = plt.subplots(figsize=(9.4, 4.2))
tn = m["truth"]["net"] / 1e6
for yi, k in zip(y, ORDER):
    v = A.loc[k, "net"] / 1e6
    b, sd = MN.loc[k, "net_bias"] / 1e6, MN.loc[k, "net_sd"] / 1e6
    ax.plot([tn + b - 1.645 * sd, tn + b + 1.645 * sd], [yi, yi], color=GRAY, lw=7, alpha=0.55, solid_capstyle="butt")
    ax.plot(v, yi, "o", color=RED if v < 0 else BLUE, ms=8, zorder=3)
    ax.text(v, yi + 0.3, f"{v:+.1f}", ha="center", fontsize=9)
ax.axvline(0, color=MUTED, lw=0.8); ax.axvline(tn, color=RED, lw=1.5)
ax.text(tn, y[0] + 0.7, f"答え +{tn:.1f}百万円", color=RED, ha="center", fontsize=9.5)
ax.set_yticks(y); ax.set_yticklabels([LAB[k] for k in ORDER]); ax.set_ylim(-0.7, len(ORDER) + 0.1)
ax.set_xlabel("差し引き（百万円）＝ 増えた粗利 − クーポン 5.3 − 固定費 0.6　灰色＝20通りの90%")
ax.set_title("図5　「前年比の差」で測ると、黒字の販促が赤字に見える", loc="left", fontsize=12)
save(fig, "fig5_money.png")

# 図6：1枚の報告
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1030, "height": 800}, device_scale_factor=1.5)
    pg.goto((ROOT / "reports" / "promo_effect_report.html").as_uri()); pg.wait_for_timeout(300)
    pg.screenshot(path=str(FIG / "fig6_onepage_report.png"), full_page=True); b.close()
print(sorted(f.name for f in FIG.iterdir()))
