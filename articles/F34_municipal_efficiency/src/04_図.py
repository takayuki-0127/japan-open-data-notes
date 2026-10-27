"""04 図：6枚（町の名前は出さない）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from statsmodels.nonparametric.smoothers_lowess import lowess
from common import RES, GLAB, GCOL, BLUE, ORANGE, GRAY, INK, save, dea_input

m = pd.read_csv(RES / "_eff_by_municipality.csv", dtype={"code": str})
rob = pd.read_csv(RES / "robustness.csv")
gcol = dict(zip(GLAB, GCOL))

# 図1 1人あたり歳出と人口
fig, ax = plt.subplots(figsize=(8, 5))
for g in GLAB:
    d = m[m.group == g]
    ax.scatter(d["pop"], d.spend / d["pop"] * 1000, s=7, alpha=.6, color=gcol[g], label=f"{g}（{len(d)}）")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("人口（2020年、対数）"); ax.set_ylabel("1人あたり歳出（千円、2022年度、対数）")
ax.set_title("小さな町ほど1人あたりの歳出は大きい。だから規模ごとに比べる")
ax.legend(fontsize=8, frameon=False, title="人口規模（市区町村数）", title_fontsize=8)
save(fig, "f01_spend_per_capita.png")

# 図2 DEA の考え方（3万〜10万人、出力を人口だけにした1入力1出力の例）
d = m[m.group == "3万〜10万人"].copy()
eff = dea_input(d[["spend"]].values, d[["pop"]].values, vrs=True)
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(d["pop"] / 1e4, d.spend / 1e3, s=9, color=GRAY, alpha=.6, label="市町村")
f = d[eff > 0.9999].sort_values("pop")
# 可変規模のフロンティア（左下から右上への階段状の下側の包絡線）
xs, ys = [], []
best = np.inf
for _, r in d.sort_values("pop", ascending=False).iterrows():
    if r.spend < best:
        best = r.spend; xs.append(r["pop"]); ys.append(r.spend)
xs, ys = np.array(xs[::-1]), np.array(ys[::-1])
ax.plot(xs / 1e4, ys / 1e3, color=BLUE, lw=2, drawstyle="steps-post", label="フロンティア（同じ人口をいちばん少ない歳出で）")
ax.scatter(f["pop"] / 1e4, f.spend / 1e3, s=30, color=BLUE, zorder=3)
ax.set_xlabel("人口（万人）"); ax.set_ylabel("歳出（億円、2022年度）")
ax.set_title("DEA の考え方：同じ規模の中で「いちばん少ないお金」を基準にする\n（3万〜10万人の市町村、出力を人口だけにした例）", fontsize=11)
ax.legend(fontsize=8, frameon=False)
save(fig, "f02_dea_concept.png")

# 図3 グループ別の効率の分布
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
for ax, col, ttl in [(axes[0], "dea_vrs", "DEA（BCC、規模ごとのフロンティア）"), (axes[1], "sfa", "SFA（費用フロンティア、全体で1本）")]:
    data = [m.loc[m.group == g, col] for g in GLAB]
    bp = ax.boxplot(data, tick_labels=[g.replace("〜", "〜\n") for g in GLAB], widths=.55, patch_artist=True, showfliers=False)
    for patch, c in zip(bp["boxes"], GCOL):
        patch.set_facecolor(c); patch.set_alpha(.8)
    for med in bp["medians"]:
        med.set_color(INK)
    ax.set_title(ttl, fontsize=11); ax.tick_params(axis="x", labelsize=8)
axes[0].set_ylabel("効率（1＝フロンティア上）")
fig.suptitle("DEA は大きな市ほど1に近く、SFA は規模による差が小さい", fontsize=13)
save(fig, "f03_eff_by_group.png")

# 図4 DEA と SFA の順位（グループ内のパーセント順位）
fig, ax = plt.subplots(figsize=(6.6, 6))
r1 = m.groupby("group").dea_vrs.rank(pct=True) * 100
r2 = m.groupby("group").sfa.rank(pct=True) * 100
for g in GLAB:
    ix = m.group == g
    rho = spearmanr(r1[ix], r2[ix]).correlation
    ax.scatter(r1[ix], r2[ix], s=6, alpha=.6, color=gcol[g], label=f"{g}：ρ={rho:.2f}")
ax.plot([0, 100], [0, 100], color=GRAY, lw=1, ls="--")
ax.set_xlabel("DEA での順位（規模グループ内、パーセント）"); ax.set_ylabel("SFA での順位（規模グループ内、パーセント）")
ax.set_title("2つの手法の順位はおおむね合うが、ずれも大きい", fontsize=12)
ax.legend(fontsize=8, frameon=False, loc="upper left")
save(fig, "f04_dea_vs_sfa.png")

# 図5 効率と人口密度
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, col, ttl in [(axes[0], "dea_vrs", "DEA（BCC）"), (axes[1], "sfa", "SFA")]:
    for g in GLAB:
        d = m[m.group == g]
        ax.scatter(np.log10(d.density), d[col], s=5, alpha=.35, color=gcol[g])
        if len(d) > 30:
            lw = lowess(d[col], np.log10(d.density), frac=.6)
            ax.plot(lw[:, 0], lw[:, 1], color=gcol[g], lw=2.2, label=g)
    ax.set_xlabel("可住地1km²あたり人口（log10）"); ax.set_title(ttl, fontsize=11)
axes[0].set_ylabel("効率"); axes[0].legend(fontsize=8, frameon=False)
fig.suptitle("DEA では密に住む町ほど効率が高いが、SFA ではいちばん密な町で効率が下がる", fontsize=13)
save(fig, "f05_eff_density.png")

# 図6 頑健性：基本の DEA との順位の相関
r = rob[rob.spec != "基本"].copy()
r["label"] = r.spec.str.replace("（需要だけ、災害復旧費を含む）vs 2022年（同じ形）", "（同じ形で2022年と比較）", regex=False)
r = r.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5))
cols = [ORANGE if ("SFA" in s or "2015" in s) else BLUE for s in r.spec]
ax.barh(r.label, r.spearman_with_base, color=cols)
for y, v in enumerate(r.spearman_with_base):
    ax.text(v + .01, y, f"{v:.2f}", va="center", fontsize=9)
ax.set_xlim(0, 1.1); ax.set_xlabel("順位の相関（規模グループ内、スピアマン）")
ax.set_title("出力の選び方では順位はあまり動かないが、入力を職員数に変えると大きく動く\n（青：基本の DEA との比較　橙：SFA どうし／2015年との比較）", fontsize=11)
save(fig, "f06_robustness.png")
print("図を6枚保存")
