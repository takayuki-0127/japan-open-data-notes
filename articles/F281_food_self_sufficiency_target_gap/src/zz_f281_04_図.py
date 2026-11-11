"""F281 04 図：6枚（figures/）"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["svg.hashsalt"] = "f281"
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, RES, FIG = ROOT / "data" / "processed", ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
main = json.loads((RES / "main.json").read_text())
ssr = pd.read_csv(P / "ssr_series.csv")
plans = pd.read_csv(ROOT / "data" / "plans.csv").set_index("plan")
A = pd.read_csv(RES / "A_h27_items.csv", index_col=0)
C = pd.read_csv(RES / "C_production_achievement.csv")
D = pd.read_csv(RES / "D_feed.csv")
F = pd.read_csv(RES / "F_n_changes.csv", index_col=0)
reask = json.loads((RES / "F_reask.json").read_text())
BLUE, ORANGE, GRAY, RED, GREEN = "#2b6cb0", "#dd6b20", "#888888", "#c53030", "#2f855a"
NAME = {"H12": "2000年計画", "H17": "2005年計画", "H22": "2010年計画", "H27": "2015年計画", "R2": "2020年計画", "R7": "2025年計画"}


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


# 図1：目標と実績
r = ssr[ssr.indicator == "供給熱量ベースの総合食料自給率"].set_index("fy").value
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(r.loc[1990:].index, r.loc[1990:].values, color="black", lw=2, label="実績（カロリーベース）")
cols = {"H12": BLUE, "H17": GREEN, "H22": RED, "H27": ORANGE, "R2": "#6b46c1", "R7": "#975a16"}
for pl, p in plans.iterrows():
    ax.plot([p.base_fy, p.target_fy], [p.ssr_base, p.ssr_target], "--", color=cols[pl], lw=1.6)
    ax.plot(p.target_fy, p.ssr_target, "o", color=cols[pl])
    ax.annotate(f"{NAME[pl]}\n目標{int(p.ssr_target)}%", (p.target_fy, p.ssr_target), textcoords="offset points",
                xytext=(4, 6 if pl != "R7" else -26), fontsize=8, color=cols[pl])
ax.set_xlim(1990, 2032); ax.set_ylim(30, 55)
ax.set_ylabel("%")
ax.set_title("図1 食料自給率の目標（点線）と実績（黒）：目標年度を過ぎた4つの計画はどれも届いていない", loc="left", fontsize=11)
ax.legend(loc="upper right", frameon=False)
save(fig, "f281_1_targets_vs_actual.png")

# 図2：2015年計画の目標45%→実績37.1%の分け方（滝の図）
grp = {"米": ["米"], "畜産物（飼料自給率）": None, "畜産物（生産）": None, "魚介類": ["魚介類"], "野菜": ["野菜"],
       "果実・大豆・いも・麦": ["果実", "大豆", "かんしょ", "ばれいしょ", "小麦", "大麦・はだか麦"], "表にない品目・換算の差": ["表にない品目・換算の差"]}
LIVE = ["生乳", "牛肉", "豚肉", "鶏肉", "鶏卵"]
k_num = A["num_pt"].sum() / -(A["shortfall_kcal"].sum()) if A["shortfall_kcal"].sum() else 0
h2 = main["H2"]
live_num = A.loc[LIVE, "num_pt"].sum()
feed_share = h2["livestock_from_feed"] / h2["livestock_shortfall_kcal"]
steps = [("目標（2015年計画）", main["H1"]["ssr_target"])]
num_items = [("米", A.loc["米", "num_pt"]), ("畜産物：飼料自給率", live_num * feed_share), ("畜産物：生産", live_num * (1 - feed_share)),
             ("魚介類", A.loc["魚介類", "num_pt"]), ("野菜", A.loc["野菜", "num_pt"]),
             ("果実・大豆・いも・麦", A.loc[["果実", "大豆", "かんしょ", "ばれいしょ", "小麦", "大麦・はだか麦"], "num_pt"].sum()),
             ("表にない品目・換算の差", A.loc["表にない品目・換算の差", "num_pt"]), ("分母：全体の熱量が減った分", A["den_pt"].sum())]
fig, ax = plt.subplots(figsize=(10, 5))
cur = steps[0][1]
ax.bar(0, cur, color=GRAY); ax.text(0, cur + 0.3, f"{cur:.1f}", ha="center", fontsize=9)
for i, (lab, v) in enumerate(num_items, start=1):
    ax.bar(i, v, bottom=cur, color=(RED if v < 0 else GREEN))
    ax.text(i, max(cur, cur + v) + 0.3, f"{v:+.1f}", ha="center", fontsize=9)
    cur += v
ax.bar(len(num_items) + 1, cur, color="black"); ax.text(len(num_items) + 1, cur + 0.3, f"{cur:.1f}", ha="center", fontsize=9)
labels = [steps[0][0]] + [l for l, _ in num_items] + ["実績（2025年度）"]
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8.5)
ax.set_ylim(30, 48); ax.set_ylabel("自給率（%）")
ax.set_title("図2 2015年計画の目標45%と2025年度の実績37.1%の差を分ける（ポイント）", loc="left", fontsize=11)
save(fig, "f281_2_waterfall_2025.png")

# 図3：品目ごとの国産熱量 目標と実績
items = ["米", "生乳", "魚介類", "野菜", "果実", "大豆", "鶏卵", "牛肉", "豚肉", "鶏肉", "ばれいしょ", "かんしょ", "小麦"]
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(items)); w = 0.38
ax.bar(x - w / 2, A.loc[items, "N_t"], w, color=ORANGE, label="目標から組み立てた国産熱量")
ax.bar(x + w / 2, A.loc[items, "N_a"], w, color=BLUE, label="2025年度の実績")
ax.set_xticks(x); ax.set_xticklabels(items, fontsize=9)
ax.set_ylabel("kcal／人・日")
ax.set_yscale("log")
ax.set_yticks([5, 10, 20, 50, 100, 200, 500]); ax.set_yticklabels(["5", "10", "20", "50", "100", "200", "500"])
for i, it in enumerate(items):
    ax.text(i + w / 2, A.loc[it, "N_a"] * 1.05, f"{A.loc[it, 'N_a']:.0f}", ha="center", fontsize=7, color=BLUE)
ax.legend(frameon=False)
ax.set_title("図3 品目ごとの国産熱量：2015年計画から組み立てた値と実績（縦軸は対数）", loc="left", fontsize=11)
save(fig, "f281_3_items_kcal.png")

# 図4：目標の高さと実際の伸び（レビュー対応で、届いた割合から実際の伸びに替えた）
G = pd.read_csv(RES / "G_h4_growth.csv")
rv = json.loads((RES / "G_review.json").read_text())["H4_growth"]
fig, ax = plt.subplots(figsize=(8.5, 5.8))
for pl, mk in zip(["H12", "H17", "H22", "H27"], ["o", "s", "^", "D"]):
    sub = G[G.plan == pl]
    ax.scatter(sub.ambition, sub.growth, marker=mk, s=40, alpha=0.8, label=f"{NAME[pl]}（目標{int(plans.loc[pl,'target_fy'])}年度）")
for _, rr in G[G.ambition > 1.5].iterrows():
    ax.annotate(rr["item"], (rr.ambition, rr.growth), xytext=(3, 3), textcoords="offset points", fontsize=7.5, color="#444")
lim = [0.6, 2.5]
ax.plot(lim, lim, color=GRAY, lw=1, ls="--", label="目標どおり（線より下は届かなかった）")
ax.axhline(1, color=GRAY, lw=0.8, ls=":")
ax.set_xscale("log"); ax.set_yscale("log")
tk = [0.6, 0.8, 1, 1.2, 1.5, 2, 2.5]
for f_ in (ax.set_xticks, ax.set_yticks):
    f_(tk)
ax.set_xticklabels([f"{v:g}" for v in tk]); ax.set_yticklabels([f"{v:g}" for v in tk])
ax.minorticks_off()
ax.set_xlim(*lim); ax.set_ylim(0.45, 2.5)
ax.set_xlabel("目標の高さ（生産努力目標 ÷ 基準年度の生産量、対数）")
ax.set_ylabel("実際の伸び（目標年度の生産量 ÷ 基準年度、対数）")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title(f"図4 目標を高くしても生産は伸びていない（順位相関 {rv['spearman_ambition_growth']:+.2f}）：その分、高い目標ほど届かない", loc="left", fontsize=10.5)
save(fig, "f281_4_ambition_vs_achievement.png")

# 図5：飼料自給率
fig, ax = plt.subplots(figsize=(8, 4.5))
f = ssr[ssr.indicator == "飼料自給率"].set_index("fy").value.loc[1990:]
ax.plot(f.index, f.values, color="black", lw=2, label="飼料自給率の実績")
for pl, p in plans.iterrows():
    ax.plot([p.base_fy, p.target_fy], [p.feed_base, p.feed_target], "--", color=cols[pl])
    ax.plot(p.target_fy, p.feed_target, "o", color=cols[pl])
    ax.annotate(f"{NAME[pl]} {int(p.feed_target)}%", (p.target_fy, p.feed_target), xytext=(3, 4) if pl != "H17" else (4, -13), textcoords="offset points", fontsize=8, color=cols[pl])
ax.set_xlim(1990, 2032); ax.set_ylim(15, 45); ax.set_ylabel("%")
ax.set_title("図5 飼料自給率の目標と実績：25%前後のまま、目標は2025年計画で28%に", loc="left", fontsize=11)
ax.legend(frameon=False, loc="upper left")
save(fig, "f281_5_feed.png")

# 図6：国産熱量の5年ごとの変化と、今の目標に要る変化
fig, ax = plt.subplots(figsize=(9, 4.8))
c = F["N_chg5"].dropna()
ax.bar(c.index, c.values, color=[GREEN if v > 0 else GRAY for v in c.values], width=0.8)
for pl, col in [("R7", "#975a16"), ("R2", "#6b46c1")]:
    v = reask["need"][pl]["N_change_needed_pct"]
    ax.axhline(v, color=col, ls="--")
    ax.text(1967, v + 0.8, f"{NAME[pl]}の目標に2025→2030年度で要る変化 +{v:.1f}%", color=col, fontsize=8.5)
ax.set_ylabel("5年前と比べた変化（%）")
ax.set_title("図6 1人1日当たり国産熱量の5年ごとの変化（1970〜2025年度）：いちばん大きく増えた5年でも+7.2%", loc="left", fontsize=11)
ax.axhline(0, color="black", lw=0.8)
save(fig, "f281_6_reask_n_change.png")
print("ok", sorted(p.name for p in FIG.glob("*.png")))
