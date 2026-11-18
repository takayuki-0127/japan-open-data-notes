"""04_figures.py：図3枚（PNG）。日付などのメタデータは入れない。"""
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
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f538"})
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#9a9893"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：財務省「法人企業統計調査」四半期別調査 時系列データ（金融業・保険業を除く全産業）をもとに作成者が加工して作成"
META = {"Software": None}
J = pd.read_csv(R / "yoy_jumps.csv")
T = pd.read_csv(R / "jump_ratios.csv")
S = pd.read_csv(R / "requestion_sign.csv")


def finish(fig, title):
    fig.suptitle(title, x=0.01, ha="left", fontsize=12.5, color=INK)
    fig.text(0.01, 0.012, SRC, fontsize=7.4, color=INK2)


# 図1：中小（D）の従業員数の前年同期比。4〜6月期を印で
s = J[(J["item"] == "employees") & (J["industry"] == "all_ex_fin") & (J["size"] == "D") & (J["year"] >= 1996)].copy()
x = s["year"] + (s["q"] - 1) / 4
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ax.plot(x, s["yoy"], color=GRAY, lw=1.2, label="前年同期比（すべての期）")
q2 = s["q"] == 2
ax.scatter(x[q2], s.loc[q2, "yoy"], color=ORANGE, s=26, zorder=3, label="4〜6月期（標本が入れ替わる期）")
ax.axvline(2009.25, color=BLUE, lw=1, ls="--")
ax.text(2009.4, ax.get_ylim()[1] * 0.92, "2009年4〜6月期から\n半分ずつの入れ替え", color=BLUE, fontsize=9, va="top")
ax.axhline(0, color=INK2, lw=0.6)
ax.set_ylabel("従業員数の前年同期比（％）")
ax.set_xlabel("年")
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="lower left", frameon=False, fontsize=9)
finish(fig, "資本金1千万〜1億円の会社の従業員数：2008年までは4〜6月期に前年同期比が大きく跳んだ")
fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.17)
fig.savefig(F / "fig1_employees_yoy_small.png", dpi=150, metadata=META); plt.close(fig)

# 図2：とびの大きさ（絶対値の平均）、4〜6月期とほかの期、規模×項目×時期
cases = [("employees", "D", "従業員数\n1千万〜1億円"), ("sales", "D", "売上高\n1千万〜1億円"),
         ("employees", "B", "従業員数\n10億円以上"), ("sales", "B", "売上高\n10億円以上")]
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.9), sharey=True)
for ax, (per, lab) in zip(axes, [("pre_1990_2008", "全部を入れ替えていた時期（1990〜2008年）"), ("post_2010_2026", "半分ずつ入れ替える時期（2010〜2026年）")]):
    xs = np.arange(len(cases))
    q2v = [float(T[(T["item"] == it) & (T["size"] == sz) & (T["period"] == per) & (T["industry"] == "all_ex_fin")]["q2"].iloc[0]) for it, sz, _ in cases]
    ov = [float(T[(T["item"] == it) & (T["size"] == sz) & (T["period"] == per) & (T["industry"] == "all_ex_fin")]["other"].iloc[0]) for it, sz, _ in cases]
    ax.bar(xs - 0.2, q2v, 0.38, color=ORANGE, label="4〜6月期")
    ax.bar(xs + 0.2, ov, 0.38, color=GRAY, label="ほかの期")
    for i, (a, b) in enumerate(zip(q2v, ov)):
        ax.text(i - 0.2, a + 0.08, f"{a:.1f}", ha="center", fontsize=8.5, color=INK)
        ax.text(i + 0.2, b + 0.08, f"{b:.1f}", ha="center", fontsize=8.5, color=INK2)
    ax.set_xticks(xs); ax.set_xticklabels([c[2] for c in cases], fontsize=8.8)
    ax.set_title(lab, fontsize=10, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylabel("前年同期比のとび（絶対値の平均、ポイント）")
axes[0].legend(frameon=False, fontsize=9, loc="upper right")
finish(fig, "4〜6月期のとびは、全部を入れ替えていた時期の中小の会社で大きかった")
fig.subplots_adjust(left=0.08, right=0.99, top=0.84, bottom=0.2, wspace=0.06)
fig.savefig(F / "fig2_jump_size_by_period.png", dpi=150, metadata=META); plt.close(fig)

# 図3（問い直し）：4〜6月期のとびの向き。D の売上高と従業員数、2010〜2026年
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=False)
for ax, (it, lab) in zip(axes, [("sales", "売上高"), ("employees", "従業員数")]):
    s = J[(J["item"] == it) & (J["industry"] == "all_ex_fin") & (J["size"] == "D") & (J["q"] == 2) & (J["year"].between(2010, 2026))]
    cols = [BLUE if v > 0 else ORANGE for v in s["jump"]]
    ax.bar(s["year"], s["jump"], color=cols, width=0.7)
    ax.axhline(0, color=INK2, lw=0.6)
    r = S[(S["item"] == it) & (S["size"] == "D") & (S["period"] == "post_2010_2026")].iloc[0]
    ax.set_title(f"{lab}：上向き {int(r['n_up'])}回・下向き {int(r['n'] - r['n_up'])}回", fontsize=10, color=INK)
    ax.set_xlabel("年（4〜6月期）")
    ax.set_xticks(range(2010, 2027, 4))
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
axes[0].set_ylabel("4〜6月期の前年同期比のとび（ポイント）")
finish(fig, "資本金1千万〜1億円：4〜6月期のとびの向きは、上と下でかたよらない（2010〜2026年）")
fig.subplots_adjust(left=0.08, right=0.99, top=0.84, bottom=0.17, wspace=0.18)
fig.savefig(F / "fig3_jump_direction.png", dpi=150, metadata=META); plt.close(fig)
print("ok")
