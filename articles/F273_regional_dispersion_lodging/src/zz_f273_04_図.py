"""04 図：6枚"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name(); break
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 150})
R = pathlib.Path(__file__).resolve().parents[1]
F = R / "figures"
M = pd.read_csv(R / "results/A_metrics_by_year.csv")
res = json.loads((R / "results/main.json").read_text())
fo = M[M.who == "foreign"].set_index("year"); jp = M[M.who == "japanese"].set_index("year")
C1, C2, C3 = "#2b6cb0", "#c05621", "#718096"

# 図1 地方部の割合
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(fo.index, 100 * fo.local_share, "-o", color=C1, label="外国人")
ax.plot(jp.index, 100 * jp.local_share, "-o", color=C2, label="日本人")
wp = {int(k): v["published"] for k, v in res["whitepaper_check"].items() if k.isdigit()}
ax.scatter(list(wp), list(wp.values()), marker="x", s=60, color="k", zorder=5, label="審議会資料の公表値（2025年は速報）")
ax.axvspan(2019.5, 2022.5, color="#edf2f7", zorder=0)
ax.text(2021, 72, "コロナの時期", ha="center", color=C3, fontsize=9)
for y in [2017, 2025]:
    ax.annotate(f"{100*fo.local_share[y]:.1f}%", (y, 100 * fo.local_share[y]), xytext=(0, 10), textcoords="offset points", ha="center", color=C1)
ax.set_ylim(20, 75); ax.set_ylabel("三大都市圏以外（地方部）の割合（%）")
ax.set_title("図1 延べ宿泊者数のうち地方部の割合（暦年）")
ax.legend(fontsize=9, loc="center", bbox_to_anchor=(0.5, 0.56), frameon=False)
fig.tight_layout(); fig.savefig(F / "f273_fig1_local_share.png"); plt.close(fig)

# 図2 集中の物差し
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
ax = axs[0]
ax.plot(fo.index, fo.gini47, "-o", color=C1, label="外国人")
ax.set_title("47都道府県のジニ係数（外国人）"); ax.set_ylabel("ジニ係数（1に近いほど偏る）")
ax.axvspan(2019.5, 2022.5, color="#edf2f7", zorder=0)
ax2 = axs[1]
ax2.plot(fo.index, 100 * fo.top5_local, "-o", color=C1, label="地方部39道県の上位5")
ax2.plot(fo.index, 100 * fo.top5_47, "-s", color=C3, label="47都道府県の上位5")
ax2.axvspan(2019.5, 2022.5, color="#edf2f7", zorder=0)
ax2.set_title("上位5道府県が占める割合（外国人）"); ax2.set_ylabel("%"); ax2.legend(fontsize=9, frameon=False)
fig.suptitle("図2 集中の物差し：全国の偏りはコロナ前より強いまま、地方部の中の偏りも少し強まった", fontsize=11)
fig.tight_layout(); fig.savefig(F / "f273_fig2_concentration.png"); plt.close(fig)

# 図3 2019→2025 の都道府県ごとの増え方
G = pd.read_csv(R / "results/B_pref_growth_2019_2025.csv")
fig, ax = plt.subplots(figsize=(8, 4.2))
rng = np.random.default_rng(273)
for i, (lab, sub, c) in enumerate([("三大都市圏（8）", G[~G.local], C2), ("地方部（39）", G[G.local], C1)]):
    y = i + rng.uniform(-0.15, 0.15, len(sub))
    ax.scatter(sub.ratio, y, color=c, alpha=0.75, s=30)
    ax.plot([sub.ratio.median()] * 2, [i - 0.3, i + 0.3], color="k", lw=2)
ax.axvline(1, color=C3, ls="--"); ax.text(1.01, -0.45, "2019年と同じ", color=C3, fontsize=9)
ax.set_yticks([0, 1]); ax.set_yticklabels(["三大都市圏（8）", "地方部（39）"])
ax.set_xscale("log"); ax.set_xticks([0.7, 1, 1.5, 2, 3]); ax.set_xticklabels(["0.7", "1", "1.5", "2", "3"]); ax.minorticks_off(); ax.set_ylim(-0.6, 1.5); ax.set_xlabel("2025年 ÷ 2019年（外国人の延べ宿泊者数、対数目盛）")
ax.set_title("図3 2019年→2025年の増え方（1点が1都道府県、黒線は真ん中）")
fig.tight_layout(); fig.savefig(F / "f273_fig3_pref_growth.png"); plt.close(fig)

# 図4 地方部の増加の分け方
fig, ax = plt.subplots(figsize=(8, 4))
labs = ["2019→2025年", "2023→2025年"]
for i, k in enumerate(["decomp_2019_2025", "decomp_2023_2025"]):
    d = res[k]
    a, b = d["from_total_growth_mil"], d["from_share_change_mil"]
    ax.barh(i, a, color=C1, label="全体が増えた分" if i == 0 else None)
    ax.barh(i, b, left=a if b > 0 else 0, color=C2 if b > 0 else "#e53e3e", label="地方部の割合が変わった分" if i == 0 else None)
    ax.text(max(a, a + b) + 60, i, f"地方部の増加 {d['local_increase_mil']:,.0f}万人泊", va="center", fontsize=9)
ax.axvline(0, color="k", lw=0.8)
ax.set_yticks([0, 1]); ax.set_yticklabels(labs); ax.set_xlabel("万人泊")
ax.set_xlim(-900, 3700)
ax.set_title("図4 地方部の外国人の増加を「全体の伸び」と「割合の変化」に分ける")
ax.legend(fontsize=9, frameon=False, loc="lower right")
fig.tight_layout(); fig.savefig(F / "f273_fig4_decomposition.png"); plt.close(fig)

# 図5 頑健性：定義を変えた地方部の割合
RB = pd.read_csv(R / "results/C_robustness.csv")
r1 = RB[RB.check == "R1 三大都市圏の定義"].pivot(index="year", columns="variant", values="value")
r4 = RB[RB.check.str.startswith("R4")].set_index("year").value
fig, ax = plt.subplots(figsize=(8, 4.3))
ys = r1.index.astype(str)
for c, col in zip([C1, C2, C3], r1.columns):
    ax.plot(ys, 100 * r1[col], "-o", color=c, label=col)
ax.plot(ys, 100 * r4, "-o", color="#38a169", label="基本から北海道・沖縄を除く")
ax.set_ylabel("地方部の割合（%）"); ax.legend(fontsize=9, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.set_title("図5 地方部の定義を変えても、2025年は2017年に届かない")
fig.tight_layout(); fig.savefig(F / "f273_fig5_robustness.png"); plt.close(fig)

# 図6 問い直し：2030年の目標
D = pd.read_csv(R / "results/D_reask_target.csv")
D = D[D["地方部の割合"] != "目標に要る割合"]
fig, ax = plt.subplots(figsize=(8.6, 4.4))
groups = list(dict.fromkeys(D["全体の伸び"]))
shs = list(dict.fromkeys(D["地方部の割合"]))
w = 0.26
for j, sh in enumerate(shs):
    v = [D[(D["全体の伸び"] == g) & (D["地方部の割合"] == sh)]["2030年の地方部（万人泊）"].iloc[0] for g in groups]
    ax.bar(np.arange(len(groups)) + (j - 1) * w, v, w, color=[C1, C2, C3][j], label=sh)
ax.axhline(13000, color="k", ls="--"); ax.text(2.45, 12400, "目標 1億3,000万人泊", ha="right", fontsize=9)
lab = {g: g.replace("の全体の伸び", "") + f"\n（年{D[D['全体の伸び']==g]['年率'].iloc[0]*100:.1f}%）" for g in groups}
ax.set_xticks(range(len(groups))); ax.set_xticklabels([lab[g] for g in groups], fontsize=9)
ax.set_ylabel("2030年の地方部（万人泊）"); ax.legend(fontsize=9, frameon=False, title="地方部の割合", title_fontsize=9, loc="upper left", ncol=3); ax.set_ylim(0, 19500)
ax.set_title("図6 2030年の目標に届くか（2025年から全体の伸びと割合を置いた単純な計算）")
fig.tight_layout(); fig.savefig(F / "f273_fig6_reask_target.png"); plt.close(fig)
print(sorted(p.name for p in F.glob("*.png")))
