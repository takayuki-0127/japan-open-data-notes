"""図を作る（figures/ に PNG）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, setup_font

setup_font()
C14, C19, GRAY = "#2a6fb0", "#d0631b", "#bbbbbb"
paths = pd.read_csv(RES / "event_paths.csv")
band = pd.read_csv(RES / "placebo_band.csv")
summ = pd.read_csv(RES / "pull_payback_summary.csv")

def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.axhline(0, color="#555", lw=0.8)
    ax.axvline(-0.5, color="#555", lw=0.8, ls=":")

# 図1 グループ別のイベントスタディ（2014 と 2019）
groups = ["消費支出", "耐久財", "日用品", "被服及び履物", "食料（酒類・外食を除く）", "外食"]
fig, axes = plt.subplots(2, 3, figsize=(12, 6.8), sharex=True)
for ax, g in zip(axes.flat, groups):
    b = band[band.group == g]
    ax.fill_between(b.k, b.lo * 100, b.hi * 100, color=GRAY, alpha=0.45, lw=0, label="増税のない年（95%の範囲）")
    for ev, c in [(2014, C14), (2019, C19)]:
        p = paths[(paths.event == ev) & (paths.group == g)]
        if ev == 2019:
            ax.plot(p[p.k <= 4].k, p[p.k <= 4].gap_pct * 100, color=c, lw=2, marker="o", ms=3, label="2019年10月（8→10%）")
            ax.plot(p[p.k >= 4].k, p[p.k >= 4].gap_pct * 100, color=c, lw=1.2, ls="--", alpha=0.6, label="2019年（2020年3月以降はコロナ）")
        else:
            ax.plot(p.k, p.gap_pct * 100, color=c, lw=2, marker="o", ms=3, label="2014年4月（5→8%）")
    ax.set_title(g, fontsize=11)
    style(ax)
    ax.set_xticks(range(-12, 13, 3))
for ax in axes[1]:
    ax.set_xlabel("増税の月からの月数（0 = 税率が上がった月）")
for ax in axes[:, 0]:
    ax.set_ylabel("「増税がなかった場合」との差（%）")
h, l = axes[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=9)
fig.suptitle("増税の前後で、実質の支出は「なかった場合」と比べてどれだけ動いたか（二人以上の世帯）", fontsize=12)
fig.tight_layout(rect=(0, 0.05, 1, 0.96))
fig.savefig(FIG / "f11_event_study.png", dpi=150)
plt.close(fig)

# 図2 駆け込みと反動の累積（消費支出・耐久財）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
for ax, g in zip(axes, ["消費支出", "耐久財"]):
    for ev, c in [(2014, C14), (2019, C19)]:
        p = paths[(paths.event == ev) & (paths.group == g) & (paths.k >= -6)].copy()
        if ev == 2019:
            p = p[p.k <= 4]
        p["cum"] = p.gap.cumsum()
        ax.plot(p.k, p.cum / 1000, color=c, lw=2.2, marker="o", ms=3.5, label=f"{ev}年")
    style(ax)
    ax.set_title(f"{g}：6か月前からの差の累計", fontsize=11)
    ax.set_xticks(range(-6, 13, 2))
    ax.set_xlabel("増税の月からの月数")
    ax.set_ylabel("1世帯あたりの累計（千円、2015年の価格）")
    ax.legend(frameon=False)
fig.text(0.5, 0.005, "2019年は2020年2月（4か月後）まで。それ以降はコロナの影響が大きいので含めない", ha="center", fontsize=9, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(FIG / "f11_cumulative.png", dpi=150)
plt.close(fig)

# 図3 軽減税率：食料（酒類・外食を除く）と日用品
did = json.load(open(RES / "reduced_rate_did.json"))
fig, ax = plt.subplots(figsize=(8.5, 4.3))
labels = ["食料\n増税前3か月", "日用品\n増税前3か月", "食料\n増税後5か月", "日用品\n増税後5か月"]
keys = [("pre_food"), ("pre_daily"), ("post_food"), ("post_daily")]
x = np.arange(4)
w = 0.38
v14 = [did["2014"][k] * 100 for k in keys]
v19 = [did["2019"][k] * 100 for k in keys]
b1 = ax.bar(x - w / 2, v14, w, color=C14, label="2014年（食料も5→8%）")
b2 = ax.bar(x + w / 2, v19, w, color=C19, label="2019年（食料は8%のまま＝軽減税率）")
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + (0.4 if r.get_height() >= 0 else -1.2), f"{r.get_height():+.1f}", ha="center", fontsize=9)
ax.set_xticks(x, labels)
ax.axhline(0, color="#555", lw=0.8)
ax.spines[["top", "right"]].set_visible(False)
ax.set_ylabel("「なかった場合」との差の月平均（%）")
ax.set_title("食料（軽減税率の対象の近似）は、2019年に反動がなかった", fontsize=11)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "f11_reduced_rate.png", dpi=150)
plt.close(fig)

# 図4 品目（小分類）別の駆け込み：増税前3か月の上乗せが平常の何か月分か
it = pd.read_csv(RES / "items_pull.csv")
it = it[it.base_yen >= 300]
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8))
for ax, (ev, c) in zip(axes, [(2014, C14), (2019, C19)]):
    t = it[it.event == ev].sort_values("pull_months", ascending=False).head(10).iloc[::-1]
    ax.barh(t.item, t.pull_months, color=c)
    for yv, v in enumerate(t.pull_months):
        ax.text(v + 0.03, yv, f"{v:.2f}", va="center", fontsize=9)
    ax.set_title(f"{ev}年：駆け込みの大きかった品目（上位10）", fontsize=11)
    ax.set_xlabel("増税前3か月の上乗せ（平常の1か月分＝1）")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, max(2.6, t.pull_months.max() * 1.15))
fig.tight_layout()
fig.savefig(FIG / "f11_items.png", dpi=150)
plt.close(fig)

# 図5 頑健性：駆け込みと反動（平常の何か月分か）
rob = pd.read_csv(RES / "robustness.csv")
specs = list(dict.fromkeys(rob.spec))
gs = ["消費支出", "耐久財", "日用品", "食料（酒類・外食を除く）"]
fig, axes = plt.subplots(1, 4, figsize=(14, 4.8), sharey=True)
for ax, g in zip(axes, gs):
    for j, s in enumerate(specs):
        for ev, c, off in [(2014, C14, -0.15), (2019, C19, 0.15)]:
            r = rob[(rob.spec == s) & (rob.group == g) & (rob.event == ev)].iloc[0]
            ax.plot([r.pull_months], [j + off], "o", color=c, ms=6)
            ax.plot([r.payback_months], [j + off], "s", color=c, ms=5, mfc="white")
    ax.axvline(0, color="#555", lw=0.8)
    ax.set_title(g, fontsize=10)
    ax.set_xlabel("平常の1か月分＝1")
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_yticks(range(len(specs)), [s.replace("（", "\n（") for s in specs], fontsize=8)
axes[0].invert_yaxis()
from matplotlib.lines import Line2D
hl = [Line2D([], [], color=C14, marker="o", ls=""), Line2D([], [], color=C19, marker="o", ls=""),
      Line2D([], [], color="#333", marker="o", ls=""), Line2D([], [], color="#333", marker="s", mfc="white", ls="")]
fig.legend(hl, ["2014年", "2019年", "駆け込み（6か月）", "反動（5か月）"], loc="lower center", ncol=4, frameon=False, fontsize=9)
fig.suptitle("設定を変えても、耐久財の駆け込みは2014年のほうが大きく、食料の反動は2019年にはなかった", fontsize=11)
fig.tight_layout(rect=(0, 0.06, 1, 0.95))
fig.savefig(FIG / "f11_robustness.png", dpi=150)
plt.close(fig)
print("ok")
