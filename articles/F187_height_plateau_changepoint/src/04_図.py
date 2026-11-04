"""04 図：5枚"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, GRAY = "#2f6db3", "#d9792b", "#999999"
SEXN = {"M": "男子", "F": "女子"}

d = pd.read_csv(RES / "height_panel.csv")
br = pd.read_csv(RES / "breaks_by_age.csv")


def two_break_fit(x, y, b1, b2):
    X = np.column_stack([np.ones_like(x), x - 1948, np.maximum(x - b1, 0), np.maximum(x - b2, 0)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return X @ coef


# 1. 推移（12歳・17歳）と折れ線
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
for ax, sex in zip(axes, ["M", "F"]):
    for age, col in [(12, ORANGE), (17, BLUE)]:
        s = d[(d.sex == sex) & (d.age == age)]
        pre = s[s.year <= 1939]
        ax.plot(pre.year, pre.height, color=col, alpha=.45, lw=1.2)
        po = s[s.year >= 1948]
        ax.plot(po.year, po.height, color=col, lw=1.6, label=f"{age}歳")
        r = br[(br.sex == sex) & (br.age == age)].iloc[0]
        f = s[(s.year >= 1948) & (s.year <= 2019) & (s.flag_covid == 0)]
        fit = two_break_fit(f.year.to_numpy(float), f.height.to_numpy(float), r.M4_break1, r.M4_break2)
        ax.plot(f.year, fit, color="k", lw=.9, ls="--")
        yb = np.interp(r.M4_break2, f.year, fit)
        ax.scatter([r.M4_break2], [yb], color="k", zorder=5, s=25)
        ax.annotate(f"止まる {int(r.M4_break2)}", (r.M4_break2, yb), xytext=(6, -16),
                    textcoords="offset points", fontsize=9)
    ax.axvspan(2019.5, 2023.5, color=GRAY, alpha=.25, lw=0)
    ax.axvspan(1939.5, 1947.5, color=GRAY, alpha=.12, lw=0)
    ax.set_title(f"{SEXN[sex]}の平均身長（灰色：調査なし／コロナ期）")
    ax.set_ylabel("cm")
    ax.legend(loc="lower right", frameon=False)
fig.text(0.01, 0.005, "破線：折れ目2つの折れ線（1948〜2019年度で推定）。1939年度以前は薄い線（調べ方が違う）。"
         "出典：文部科学省「学校保健統計調査」を加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, .03, 1, 1))
fig.savefig(FIG / "f187_trend.png", dpi=150)
plt.close(fig)

# 2. 年齢ごとの「鈍った年」と「止まった年」
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
for ax, sex in zip(axes, ["M", "F"]):
    b = br[br.sex == sex]
    ax.errorbar(b.age - .12, b.M1_break, yerr=[b.M1_break - b.M1_lo, b.M1_hi - b.M1_break],
                fmt="o", color=BLUE, capsize=3, label="伸びが鈍った年（折れ目1つ、95%区間）")
    ax.plot(b.age + .12, b.M4_break2, "s", color=ORANGE, label="止まった年（折れ目2つのあとの方）")
    ax.plot(b.age, b.M3_reach_max, "x", color="k", label="最高値−0.3cm に届いた年")
    ax.set_title(SEXN[sex])
    ax.set_xlabel("年齢")
    ax.set_xticks(range(5, 18))
    ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("年度")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, fontsize=9, frameon=False, loc="lower center", ncol=3)
fig.tight_layout(rect=(0, .07, 1, 1))
fig.savefig(FIG / "f187_breaks_by_age.png", dpi=150)
plt.close(fig)

# 3. 世代（生まれ年の目安）でみる
coh = pd.read_csv(RES / "cohort_heights.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
for sex, col in [("M", BLUE), ("F", ORANGE)]:
    c = coh[coh.sex == sex]
    axes[0].plot(c.cohort, c["17"], color=col, lw=1.8, label=f"{SEXN[sex]} 17歳")
    axes[0].plot(c.cohort, c["11"], color=col, lw=1.2, ls="--", label=f"{SEXN[sex]} 11歳")
    axes[1].plot(c.cohort, c.gain_11_17, color=col, lw=1.8, label=SEXN[sex])
axes[0].set_title("生まれ年の目安ごとの身長")
axes[0].set_ylabel("cm")
axes[0].legend(fontsize=9, frameon=False, ncol=2)
axes[1].set_title("11歳から17歳までに伸びた分")
axes[1].set_ylabel("cm")
axes[1].legend(frameon=False)
for ax in axes:
    ax.set_xlabel("生まれ年の目安（年度−年齢）")
    ax.grid(alpha=.3)
fig.text(0.01, 0.005, "同じ子どもを追った値ではなく、11歳の年度と17歳の年度の平均をつないだもの。コロナ期（2020〜2023年度）は除く。",
         fontsize=8, color="#555")
fig.tight_layout(rect=(0, .03, 1, 1))
fig.savefig(FIG / "f187_cohort.png", dpi=150)
plt.close(fig)

# 4. 方法で変わるか
rob = pd.read_csv(RES / "robustness_windows.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
meths = [("M1", "折れ目1つ", BLUE, "o"), ("M1b", "折れ目のあと傾き0", ORANGE, "s"),
         ("M2", "毎年の伸びの平均が変わる点", GRAY, "^"), ("M3", "最高値−0.3cm", "k", "x")]
for ax, sex in zip(axes, ["M", "F"]):
    r = rob[rob.sex == sex]
    ages = [11, 13, 14, 17]
    for j, (m, lab, col, mk) in enumerate(meths):
        for i, a in enumerate(ages):
            v = r[r.age == a][m]
            ax.scatter(np.full(len(v), i + (j - 1.5) * .17), v, color=col, marker=mk, s=22,
                       label=lab if i == 0 else None, alpha=.8)
    ax.set_xticks(range(len(ages)))
    ax.set_xticklabels([f"{a}歳" for a in ages])
    ax.set_title(f"{SEXN[sex]}：方法4つ×期間6通り")
    ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("変化点の年度")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, fontsize=9, frameon=False, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.03))
fig.text(0.01, 0.005, "2021年の×：コロナ期の値を含めた期間（2020〜2023年度は測定時期がずれた）", fontsize=8, color="#555")
fig.tight_layout(rect=(0, .1, 1, 1))
fig.savefig(FIG / "f187_methods.png", dpi=150)
plt.close(fig)

# 5. 止まったあと
post = pd.read_csv(RES / "post_plateau_slope.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
for sex, col, off in [("M", BLUE, -.15), ("F", ORANGE, .15)]:
    p = post[post.sex == sex]
    axes[0].errorbar(p.age + off, p.slope_cm10y, yerr=[p.slope_cm10y - p.lo, p.hi - p.slope_cm10y],
                     fmt="o", color=col, capsize=3, label=SEXN[sex])
    axes[1].bar(p.age + off, p.diff_2024_25, width=.3, color=col, label=SEXN[sex])
axes[0].axhline(0, color="k", lw=.8)
axes[0].set_title("1994〜2019年度の傾き（10年あたり、95%区間）")
axes[0].set_ylabel("cm／10年")
axes[1].axhline(0, color="k", lw=.8)
axes[1].set_title("2024・2025年度の平均 − 2015〜2019年度の平均")
axes[1].set_ylabel("cm")
for ax in axes:
    ax.set_xlabel("年齢")
    ax.set_xticks(range(5, 18))
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.005, "2024・2025年度の差は、調べ方の変化の影響が残っていないかを分けられない（本文「言えないこと」）。",
         fontsize=8, color="#555")
fig.tight_layout(rect=(0, .03, 1, 1))
fig.savefig(FIG / "f187_post_plateau.png", dpi=150)
plt.close(fig)
print("figures:", sorted(p.name for p in FIG.glob("*.png")))
