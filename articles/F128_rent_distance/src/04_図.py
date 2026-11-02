"""04 図"""
import numpy as np
import pandas as pd
from common import DATA, RES, FIG, RADIUS, setup_fig

plt = setup_fig()
FIG.mkdir(exist_ok=True)
COL = {"東京": "#1f5fa8", "名古屋": "#d9822b", "大阪": "#2e9e6a"}
SRC = "出典：総務省「住宅・土地統計調査」（2018・2023年）を加工して作成"

# 図1 距離帯ごとの民営借家の1畳当たり家賃（0〜10km=1）
rel = pd.read_csv(RES / "band_relative.csv")
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for m, c in COL.items():
    for y, ls in [(2023, "-"), (2018, ":")]:
        g = rel[(rel.metro == m) & (rel.year == y)].sort_values("mid")
        ax.plot(g.mid, g.rel, ls, color=c, marker="o" if y == 2023 else None, ms=4,
                label=f"{m}（{y}年）" if y == 2023 else f"{m}（2018年）")
ax.axhline(1, color="gray", lw=0.6)
ax.set_xlabel("都心（都庁・市役所）からの距離帯の中央（km）")
ax.set_ylabel("0〜10km 圏を1とした家賃の比")
ax.set_title("民営借家の1畳当たり家賃は、東京では60〜70km 圏で都心の3分の1強")
ax.legend(fontsize=8, ncol=2)
ax.text(0, -0.17, SRC + "（距離帯別の集計）", transform=ax.transAxes, fontsize=7, color="gray")
fig.tight_layout()
fig.savefig(FIG / "fig1_band_curve.png", dpi=150)
plt.close(fig)

# 図2 市区町村の散布図と GAM
df = pd.read_csv(DATA / "muni_analysis.csv", dtype={"code": str})
df["rad"] = df.metro3.map(RADIUS)
M = df[(df.dist3 <= df.rad) & df.rent_m2_2023.notna()]
cur = pd.read_csv(RES / "gam_curve_2023.csv")
fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
for ax, (m, c) in zip(axes, COL.items()):
    g = M[M.metro3 == m]
    ax.scatter(g.dist3, g.rent_m2_2023, s=10, alpha=0.5, color=c, edgecolor="none")
    k = cur[cur.metro == m]
    ax.plot(k.dist, k.rent, color="black", lw=1.6, label="GAM（なめらかな曲線）")
    ax.fill_between(k.dist, k.lo, k.hi, color="black", alpha=0.12)
    ax.set_yscale("log")
    ax.yaxis.set_minor_formatter(plt.matplotlib.ticker.NullFormatter())
    ax.set_yticks([500, 1000, 2000, 4000])
    ax.set_yticklabels(["500", "1,000", "2,000", "4,000"])
    ax.set_title(f"{m}圏（{len(g)}市区町村）")
    ax.set_xlabel("都心からの直線距離（km）")
axes[0].set_ylabel("民営借家の延べ面積1m²当たり家賃（円/月）")
axes[0].legend(fontsize=8)
fig.suptitle("市区町村で見ても、家賃は都心から十数km までで大きく下がり、その先はゆるやかになる", fontsize=11)
fig.text(0.01, 0.01, SRC + "。1点が1市区町村（政令市は区）", fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.04, 1, 0.95))
fig.savefig(FIG / "fig2_muni_gam.png", dpi=150)
plt.close(fig)

# 図3 建築の時期をそろえても変わらない
adj = pd.read_csv(RES / "band_age_adjusted.csv")
adj = adj[adj.year == 2023]
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for m, c in COL.items():
    g = adj[adj.metro == m].sort_values("mid")
    ax.plot(g.mid, g.rel_raw, "-o", color=c, ms=4, label=f"{m}：そのまま")
    ax.plot(g.mid, g.rel_age_adj, "--s", color=c, ms=4, mfc="white", label=f"{m}：建築の時期をそろえる")
ax.set_xlabel("都心からの距離帯の中央（km）")
ax.set_ylabel("0〜10km 圏を1とした家賃の比（2023年）")
ax.set_title("建物の古さの違いをそろえても、距離による下がり方はほぼ同じ")
ax.legend(fontsize=7.5, ncol=2)
ax.text(0, -0.17, SRC + "。建築の時期10区分ごとの比を平均", transform=ax.transAxes, fontsize=7, color="gray")
fig.tight_layout()
fig.savefig(FIG / "fig3_age_adjusted.png", dpi=150)
plt.close(fig)

# 図4 都心からの距離と駅からの距離（GAM の部分効果）
pdp = pd.read_csv(RES / "gam2_partial.csv")
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, (t, xl) in zip(axes, [("dist", "都心からの直線距離（km）"), ("station", "駅まで1km 未満に住む世帯の割合")]):
    g = pdp[pdp.term == t]
    ref = 5.0 if t == "dist" else 0.2
    r0 = np.interp(ref, g.x, g.eff)
    ax.plot(g.x, np.exp(g.eff - r0), color="#1f5fa8")
    ax.fill_between(g.x, np.exp(g.lo - r0), np.exp(g.hi - r0), color="#1f5fa8", alpha=0.15)
    ax.axhline(1, color="gray", lw=0.6)
    ax.set_xlabel(xl)
    if t == "station":
        ax.xaxis.set_major_formatter(plt.matplotlib.ticker.PercentFormatter(1.0))
axes[0].set_ylabel("家賃の比（左：5km=1、右：20%=1）")
axes[0].set_title("駅の近さを入れたあとの、都心からの距離")
axes[1].set_title("都心からの距離を入れたあとの、駅の近さ")
fig.suptitle("都心からの距離と駅の近さは、それぞれ別に家賃と関係していた（3大都市圏、2023年）", fontsize=11)
fig.text(0.01, 0.01, SRC + "。駅までの距離は主世帯の分布（市区町村別）。都市圏の違いを含めて推定", fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.04, 1, 0.94))
fig.savefig(FIG / "fig4_station_partial.png", dpi=150)
plt.close(fig)

# 図5 頑健性
rob = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(figsize=(7.6, 5.2))
yy = np.arange(len(rob))[::-1]
lo = np.expm1(rob.slope10 - 1.96 * rob.se) * 100
hi = np.expm1(rob.slope10 + 1.96 * rob.se) * 100
ax.errorbar(rob.pct_per10, yy, xerr=[rob.pct_per10 - lo, hi - rob.pct_per10], fmt="o", color="#1f5fa8", capsize=3)
ax.set_yticks(yy)
ax.set_yticklabels([f"{c}（{n}）" for c, n in zip(rob.check, rob.n)], fontsize=8)
ax.axvline(0, color="gray", lw=0.6)
ax.axvline(rob.pct_per10.iloc[0], color="#1f5fa8", lw=0.6, ls=":")
ax.set_xlabel("都心から10km 離れるごとの家賃の変化（%、95%区間）")
ax.set_title("条件を変えても、10km 離れるごとに家賃は7〜15%下がる。\n大きさは都市圏で違い、東京が最も急")
fig.text(0.01, 0.01, "出典：総務省「住宅・土地統計調査」を加工して作成。かっこ内は市区町村（距離帯）の数", fontsize=7, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "fig5_robustness.png", dpi=150)
plt.close(fig)
print("figures done")
