"""04 図：figures/ に6枚"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, YEARS, CUTOFFS, H, save, fit_line, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, RED

df = pd.read_csv(DATA / "lfs_single_age.csv")
main = pd.read_csv(RES / "rd_main.csv")
rob = pd.read_csv(RES / "rd_robustness.csv")
plac = pd.read_csv(RES / "rd_placebo.csv")
pv = pd.read_csv(RES / "rd_vs_placebo.csv")
un = pd.read_csv(RES / "rd_unemployment.csv")
pf = pd.read_csv(RES / "rd_pref2020.csv")
YC = {2000: "#c9d9ee", 2005: "#93b6e0", 2010: "#5b93d1", 2015: "#2a78d6", 2020: "#0b3f7a"}

# f01 年齢別の就業率
fig, ax = plt.subplots(figsize=(8, 4.6))
for y in YEARS:
    d = df[(df.year == y) & (df.sex == "総数") & df.age.between(50, 75)]
    ax.plot(d.age, d.emp_rate * 100, marker="o", ms=3, lw=1.6, color=YC[y], label=f"{y}年")
for c in CUTOFFS:
    ax.axvline(c - 0.5, color=GRAY, ls="--", lw=1)
    ax.text(c - 0.4, 92, f"{c}歳", color=GRAY, fontsize=9)
ax.set(xlabel="年齢（各歳）", ylabel="就業率（%）", ylim=(20, 95),
       title="年齢別の就業率（男女計）：60歳の段差は小さくなり、65歳に段差ができた")
ax.legend(frameon=False, ncol=1, loc="lower left")
save(fig, "f01_emp_by_age.png")

# f02 回帰不連続の図（2000年と2020年、60歳・65歳）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, y in zip(axes, [2000, 2020]):
    d = df[(df.year == y) & (df.sex == "総数") & df.age.between(52, 72)]
    ax.scatter(d.age, d.emp_rate * 100, s=16, color=GRAY, zorder=3)
    for c, col in zip(CUTOFFS, [BLUE, ORANGE]):
        for side in ["left", "right"]:
            xs, ys = fit_line(df[(df.year == y) & (df.sex == "総数")], c, side=side)
            ax.plot(xs, ys, color=INK, lw=1.8)
        j = main[(main.year == y) & (main.sex == "総数") & (main.cutoff == c)].iloc[0]
        ax.axvline(c - 0.5, color=col, ls=":", lw=1)
        ax.text(c + 0.2, (j.rate_left + 4) if c == 60 else (j.rate_left + 6), f"{c}歳 {j.jump:+.1f}pt", color=col, fontsize=10)
    ax.set(title=f"{y}年", xlabel="年齢（各歳）")
axes[0].set_ylabel("就業率（%）")
fig.suptitle("境界の左右5歳に直線を当てはめ、境界での食い違いを「段差」とした", fontsize=12, y=1.03)
save(fig, "f02_rd_2000_2020.png")

# f03 段差の大きさの推移（男女別）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
for ax, sx in zip(axes, ["男", "女"]):
    for c, col in zip(CUTOFFS, [BLUE, ORANGE]):
        m = main[(main.sex == sx) & (main.cutoff == c)]
        ax.errorbar(m.year + (-0.6 if c == 60 else 0.6), m.jump, yerr=1.96 * m.se, fmt="o-", color=col, capsize=3, label=f"{c}歳の段差")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set(title=sx, xticks=YEARS, xlabel="国勢調査の年")
axes[0].set_ylabel("就業率の段差（ポイント）")
axes[0].legend(frameon=False, loc="lower right")
fig.suptitle("60歳の段差は20年で5分の1に、65歳の段差は男性で3.5倍に", fontsize=12, y=1.03)
save(fig, "f03_jump_trend.png")

# f04 頑健性：設定を変えた段差（2000・2020年）
specs = [s for s in rob.spec.unique() if s != "日本人のみ"]
fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
for ax, c in zip(axes, CUTOFFS):
    for y, col, off in [(2000, LIGHT, -0.15), (2010, "#5b93d1", 0), (2020, "#0b3f7a", 0.15)]:
        r = rob[(rob.year == y) & (rob.cutoff == c)].set_index("spec").reindex(specs)
        ax.errorbar(r.jump, np.arange(len(specs)) + off, xerr=1.96 * r.se, fmt="o", color=col, ms=4, capsize=2, label=f"{y}年")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set(title=f"{c}歳", xlabel="段差（ポイント）")
axes[0].set_yticks(range(len(specs))); axes[0].set_yticklabels(specs, fontsize=9); axes[0].invert_yaxis()
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.55, -0.06))
fig.suptitle("60歳の段差は設定によらず縮んだ。65歳は2000年だけ設定で揺れ、2020年は−4〜−6ポイント", fontsize=12, y=1.03)
save(fig, "f04_robustness.png")

# f05 偽の境界との比較（男女計、h=3）
fig, ax = plt.subplots(figsize=(8, 4.4))
for i, y in enumerate(YEARS):
    p = plac[(plac.year == y) & (plac.sex == "総数")]
    ax.scatter(np.full(len(p), i) + np.random.default_rng(1).uniform(-0.12, 0.12, len(p)), p.jump, s=12, color=GRAY, alpha=0.7,
               label="段差がないはずの年齢（45〜57歳・68〜80歳）" if i == 0 else None)
    t = pv[(pv.year == y) & (pv.sex == "総数")].set_index("cutoff")
    ax.scatter(i, t.loc[60, "jump_h3"], s=60, color=BLUE, marker="D", label="60歳" if i == 0 else None, zorder=4)
    ax.scatter(i, t.loc[65, "jump_h3"], s=60, color=ORANGE, marker="D", label="65歳" if i == 0 else None, zorder=4)
ax.axhline(0, color=INK, lw=0.8)
ax.set(xticks=range(len(YEARS)), xticklabels=[f"{y}年" for y in YEARS], ylabel="段差（ポイント、左右3歳）",
       title="段差がないはずの年齢での「段差」は±1.4ポイント以内")
ax.legend(frameon=False, loc="lower right", fontsize=9)
save(fig, "f05_placebo.png")

# f06 男性の完全失業率の段差
fig, ax = plt.subplots(figsize=(8, 4.2))
for c, col in zip(CUTOFFS, [BLUE, ORANGE]):
    m = un[(un.sex == "男") & (un.cutoff == c)]
    ax.errorbar(m.year + (-0.6 if c == 60 else 0.6), m.jump, yerr=1.96 * m.se, fmt="o-", color=col, capsize=3, label=f"{c}歳")
ax.axhline(0, color=INK, lw=0.8)
ax.set(xticks=YEARS, xlabel="国勢調査の年", ylabel="完全失業率の段差（ポイント）",
       title="男性の完全失業率：60歳で跳ね上がる幅は縮み、65歳で跳ね上がるようになった")
ax.legend(frameon=False)
save(fig, "f06_unemployment_men.png")
print("ok")
