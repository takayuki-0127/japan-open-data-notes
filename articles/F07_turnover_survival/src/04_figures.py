"""図を作る"""
import json
from common import *

hz = pd.read_csv(RES / "hazard_by_education.csv")
sv = pd.read_csv(RES / "survival_by_cohort_group.csv")
ind = pd.read_csv(RES / "hazard_by_industry_2010_2022.csv")
sz = pd.read_csv(RES / "hazard_by_size_2003_2023.csv")
R = pd.read_csv(RES / "hazard_model_coefs.csv")

# f01 卒業年代別の残存曲線（高校・大学）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
groups = ["1996-2000", "2001-05", "2006-10", "2011-15", "2016-20", "2021-25"]
cols = plt.cm.Blues(np.linspace(0.35, 1, len(groups)))
for ax, ed in zip(axes, ["高校", "大学"]):
    for g, c in zip(groups, cols):
        d = sv[(sv.education == ed) & (sv.cohort_group == g)]
        x = [0] + d.k.tolist(); y = [100] + (d.survival * 100).tolist()
        ax.step(x, y, where="post", color=c, lw=2, label=f"{g}年卒")
        ax.plot(x[1:], y[1:], "o", color=c, ms=4)
    ax.set_title(f"{ed}卒：就職した会社に残っている人の割合")
    ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["就職時", "1年目の終わり", "2年目の終わり", "3年目の終わり"])
    ax.set_ylim(50, 101); ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("%"); axes[1].legend(fontsize=8, frameon=False, loc="lower left")
fig.text(0.01, -0.06, "2021-25年卒は、2024年卒は2年目まで、2025年卒は1年目までの値を含む。\n" + SOURCE, fontsize=8, color=GRAY, va="top")
fig.savefig(FIG / "f01_survival.png"); plt.close(fig)

# f02 経過年数別のハザードの推移（高校・大学）
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
kc = {1: BLUE, 2: ORANGE, 3: GREEN}
for ax, ed in zip(axes, ["高校", "大学"]):
    for k in (1, 2, 3):
        d = hz[(hz.education == ed) & (hz.k == k)]
        ax.plot(d.grad_year, d.hazard * 100, color=kc[k], lw=2, marker="o", ms=3, label=f"{k}年目")
    ax.set_title(f"{ed}卒：経過年数別のハザード")
    ax.set_xlabel("卒業年（3月卒）"); ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("%"); axes[0].legend(frameon=False)
note(fig); fig.savefig(FIG / "f02_hazard_trend.png"); plt.close(fig)

# f03 景気の効き方（モデルからの計算）
eff = json.load(open(RES / "effects.json"))
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.4, 1]})
ax = axes[0]
labs = [("就職年0.5・その後1.0", "就職した年が\n不景気（0.5倍）", ORANGE), ("就職年1.5・その後1.0", "就職した年が\n好景気（1.5倍）", LIGHT),
        ("就職年1.0・その後0.5", "辞める年が\n不景気（0.5倍）", BLUE), ("就職年1.0・その後1.5", "辞める年が\n好景気（1.5倍）", "#9ec5f0")]
x = np.arange(2); w = 0.2
for i, (key, lab, c) in enumerate(labs):
    v = [eff[f"{ed}_3年以内_{key}"] for ed in ["高校", "大学"]]
    bars = ax.bar(x + (i - 1.5) * w, v, w, color=[ORANGE, "#f6b48f", BLUE, LIGHT][i], label=lab.replace("\n", ""))
    for bx, bv in zip(x + (i - 1.5) * w, v): ax.text(bx, bv + 0.4, f"{bv:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(["高校卒", "大学卒"]); ax.set_ylim(0, 62)
ax.set_ylabel("3年以内の離職率（%、モデルの計算）"); ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper right")
ax.set_title("求人倍率だけを変えたときの3年以内の離職率"); ax.grid(axis="y", alpha=.3)
ax = axes[1]
e1, e2 = eff["傷跡モデル_就職年の効果_1年目"], eff["傷跡モデル_就職年の効果_2・3年目"]
for yy, (v, lab) in enumerate([(e1, "1年目"), (e2, "2・3年目")][::-1]):
    ax.errorbar(v[0], yy, xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="o", color=ORANGE, capsize=4, ms=7)
ax.axvline(0, color=INK, lw=.8); ax.set_yticks([0, 1]); ax.set_yticklabels(["2・3年目", "1年目"]); ax.set_ylim(-.6, 1.6)
ax.set_xlabel("就職した年の求人倍率（log）の係数"); ax.set_title("就職した年の景気が効くのは1年目だけ"); ax.grid(axis="x", alpha=.3)
fig.text(0.01, -0.03, "全学歴の離散時間ハザードモデル（経過年数×学歴の固定効果、辞める年の求人倍率、トレンド）。左は2010年卒・求人倍率1.0倍を基準に、一方だけを変えた計算。\n" + SOURCE, fontsize=8, color=GRAY, va="top")
fig.savefig(FIG / "f03_business_cycle.png"); plt.close(fig)

# f04 産業別のハザード（大学、2010〜2022年卒の合計）
d = ind[(ind.education == "大学") & (ind.industry != "調査産業計")].sort_values("within3")
fig, ax = plt.subplots(figsize=(9, 6))
y = np.arange(len(d))
for k, off in zip((1, 2, 3), (-0.25, 0, 0.25)):
    ax.barh(y + off, d[f"h{k}"] * 100, height=0.25, color=kc[k], label=f"{k}年目")
ax.set_yticks(y); ax.set_yticklabels(d.industry, fontsize=9)
tot = ind[(ind.education == "大学") & (ind.industry == "調査産業計")].iloc[0]
ax.axvline(tot.h1 * 100, color=GRAY, ls=":", lw=1)
ax.set_xlabel("ハザード（%）"); ax.set_title("大学卒の産業別ハザード（2010〜2022年3月卒の合計）")
ax.legend(frameon=False, loc="lower right"); ax.grid(axis="x", alpha=.3)
fig.text(0.01, -0.03, "点線は産業計の1年目。各年目までの累積は、それぞれ卒業の翌年・翌々年・3年後の6月に把握した値。\n" + SOURCE, fontsize=8, color=GRAY, va="top")
fig.savefig(FIG / "f04_industry.png"); plt.close(fig)

# f05 規模別のハザード（大学・高校、2003〜2023年卒の合計）
order = ["5人未満", "5～29人", "30～99人", "100～499人", "500～999人", "1000人以上"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), sharey=True)
for ax, ed in zip(axes, ["高校", "大学"]):
    d = sz[sz.education == ed].set_index("size").loc[order]
    for k in (1, 2, 3):
        ax.plot(range(1, 4), [0]*3, alpha=0)
    for i, s in enumerate(order):
        c = plt.cm.viridis(i / (len(order) - 1))
        ax.plot([1, 2, 3], [d.loc[s, f"h{k}"] * 100 for k in (1, 2, 3)], marker="o", color=c, lw=2, label=s)
    ax.set_xticks([1, 2, 3]); ax.set_xticklabels(["1年目", "2年目", "3年目"])
    ax.set_title(f"{ed}卒：事業所の規模別のハザード"); ax.grid(axis="y", alpha=.3)
axes[0].set_ylabel("%"); axes[1].legend(fontsize=8, frameon=False, ncol=2)
fig.text(0.01, -0.03, "2003〜2023年3月卒の合計。\n" + SOURCE, fontsize=8, color=GRAY, va="top")
fig.savefig(FIG / "f05_size.png"); plt.close(fig)

# f06 頑健性：2つの景気の係数
order_m = ["基本（全学歴）", "高校と大学だけ", "中学だけ", "高校だけ", "短大等だけ", "大学だけ", "2009〜2012年卒を除く", "2020・2021年の離職を除く", "トレンドなし"]
fig, ax = plt.subplots(figsize=(9, 4.8))
for j, (term, c, lab) in enumerate([("ljr_entry", ORANGE, "就職した年の求人倍率（log）"), ("ljr_cur", BLUE, "辞める年の求人倍率（log）")]):
    d = R[(R.term == term)].set_index("model").loc[order_m]
    yy = np.arange(len(d))[::-1] + (0.15 if j == 0 else -0.15)
    ax.errorbar(d.coef, yy, xerr=[d.coef - d.lo, d.hi - d.coef], fmt="o", color=c, capsize=3, label=lab)
ax.axvline(0, color=INK, lw=.8)
ax.set_yticks(np.arange(len(order_m))[::-1]); ax.set_yticklabels(order_m, fontsize=9)
ax.set_xlabel("係数（ロジット、95%区間は卒業年でクラスター）"); ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
ax.set_title("2つの景気の係数は、条件を変えても向きが同じか"); ax.grid(axis="x", alpha=.3)
fig.text(0.01, -0.1, SOURCE, fontsize=8, color=GRAY, va="top"); fig.savefig(FIG / "f06_robustness.png"); plt.close(fig)
print("ok")
