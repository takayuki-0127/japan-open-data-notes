"""F234 図（5枚。6枚目はダッシュボードの画面写真で 05_ダッシュボード.py が作る）"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import *

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
o = json.load(open(RES / "main.json"))
A = pd.read_csv(RES / "A_item_estimates.csv")
G = pd.read_csv(RES / "D_group_elasticity_and_risk.csv")
C = pd.read_csv(RES / "C_cross_elasticities.csv")

# 図1 推定の仕方で弾力性はどれだけ変わるか
fig, ax = plt.subplots(figsize=(10, 5.6))
cols = [("levels", "品目ごと：値段と量の水準を\nそのまま回帰"), ("trend", "品目ごと：\n年のトレンドを入れる"), ("diff", "品目ごと：\n前年からの変化どうし")]
data = [A[c].dropna().clip(-4, 3) for c, _ in cols]
ax.boxplot(data, positions=[1, 2, 3], widths=0.5, showfliers=False)
for i, (c, _) in enumerate(cols):
    y = A[c].dropna().clip(-4, 3)
    ax.scatter(np.random.default_rng(1).normal(i + 1, 0.06, len(y)), y, s=8, alpha=.35, color="#4c72b0")
pts = [(4, o["A"]["panel_fd_yearFE"], "全品目まとめて\n前年差＋年の効果"),
       (5, o["A"]["panel_fd_yearFE_weighted"], "同じ・支出の\n重みつき"),
       (6, o["B"]["main_narrow_food+energy"], f"操作変数\n（輸入物価）\nF={o['B']['main_narrow_food+energy']['first_stage_F']:.1f}")]
for x, r, lab in pts:
    ax.errorbar(x, r["b"], yerr=[[r["b"] - r["lo"]], [r["hi"] - r["b"]]], fmt="o", color="#c44e52", capsize=5, ms=8)
    ax.text(x + 0.12, r["b"], f"{r['b']:.2f}", va="center", fontsize=10)
ax.axhline(0, color="gray", lw=.8)
ax.axhline(-1, color="gray", lw=.8, ls=":")
ax.set_xticks(range(1, 7)); ax.set_xticklabels([l for _, l in cols] + [p[2] for p in pts], fontsize=9)
ax.set_ylabel("価格弾力性（値段1%上昇で量が何%変わるか）")
ax.set_title("同じ家計調査130品目でも、推定の仕方で弾力性は −0.3〜−0.9 と変わる", fontsize=12)
ax.set_ylim(-4.2, 3.2)
fig.tight_layout(); fig.savefig(FIG / "f234_01_methods.png", dpi=150); plt.close()

# 図2 群ごとの弾力性
fig, ax = plt.subplots(figsize=(9, 5))
G2 = G.sort_values("b")
y = np.arange(len(G2))
ax.errorbar(G2.b, y, xerr=[G2.b - G2.lo, G2.hi - G2.b], fmt="o", color="#4c72b0", capsize=4)
for yi, (b, n) in enumerate(zip(G2.b, G2["items"])):
    ax.text(G2.hi.iloc[yi] + 0.05, yi, f"{b:.2f}（{n}品目）", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(G2.group)
ax.axvline(0, color="gray", lw=.8); ax.axvline(-1, color="gray", lw=.8, ls=":")
ax.set_xlabel("価格弾力性（前年差・全品目の年の効果を除く、95%区間は品目のブートストラップ）")
ax.set_title("魚介・果物は −1 前後、野菜・調味料・肉・乳卵は −0.3〜−0.5。穀類ははっきりしない", fontsize=12)
ax.set_xlim(-2.4, 1.8)
fig.tight_layout(); fig.savefig(FIG / "f234_02_groups.png", dpi=150); plt.close()

# 図3 判断表：5%値上げで利益はどう変わるか（粗利率×弾力性）
eps = np.linspace(-9, 0, 361)
fig, ax = plt.subplots(figsize=(9.5, 5.4))
for m, c in [(0.1, "#c44e52"), (0.2, "#dd8452"), (0.3, "#4c72b0"), (0.5, "#55a868")]:
    r = (((1.05) - (1 - m)) / m * 1.05 ** eps - 1) * 100
    ax.plot(eps, r, color=c, label=f"粗利率 {int(m*100)}%")
    be = np.log(m / (m + 0.05)) / np.log(1.05)
    ax.scatter([be], [0], color=c, zorder=5)
    ax.text(be, 3, f"{be:.1f}", color=c, ha="center", fontsize=9)
ax.axhline(0, color="gray", lw=.8)
ax.axvspan(G.lo.min(), G.hi.max(), color="#bbbbbb", alpha=.3)
ax.text((G.lo.min() + G.hi.max()) / 2, -45, "家計調査の\n群ごとの\n弾力性の範囲", ha="center", fontsize=9)
ax.set_xlabel("その商品の価格弾力性"); ax.set_ylabel("5%値上げしたときの利益の変化（%）")
ax.set_ylim(-60, 60); ax.set_xlim(-9.3, 1.5)
ax.set_title("利益が減るのは弾力性が「分かれ目」より小さいときだけ。家計全体の弾力性はその手前にある", fontsize=11.5)
ax.legend(loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "f234_03_decision.png", dpi=150); plt.close()

# 図4 店・ブランドの弾力性：利益を最大にしている店なら 弾力性 ≒ −1/粗利率
m = np.linspace(0.08, 0.6, 100)
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(m * 100, -1 / m, color="#4c72b0", label="利益が最大のときの弾力性（−1÷粗利率）")
ax.axhspan(G.lo.min(), G.hi.max(), color="#bbbbbb", alpha=.35, label="家計全体（市場）の弾力性の範囲")
for mm in [0.1, 0.2, 0.3, 0.5]:
    ax.scatter([mm * 100], [-1 / mm], color="#4c72b0"); ax.text(mm * 100 + 1.2, -1 / mm - 0.45, f"{-1/mm:.1f}", fontsize=9)
ax.set_xlabel("粗利率（%）"); ax.set_ylabel("価格弾力性")
ax.set_ylim(-13, 0.5)
ax.set_title("1つの店・ブランドの弾力性は、市場全体より数倍大きいはず（客がほかへ移るため）", fontsize=12)
ax.legend(loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f234_04_firm_vs_market.png", dpi=150); plt.close()

# 図5 交差弾力性
fig, axes = plt.subplots(1, 3, figsize=(12, 4.4))
for ax, g in zip(axes, ["肉", "主食", "飲み物"]):
    sub = C[C.group == g]
    items = list(dict.fromkeys(sub["item"]))
    M = np.full((len(items), len(items)), np.nan); S = np.zeros_like(M, dtype=bool)
    for _, r in sub.iterrows():
        i = items.index(r["item"]); j = i if r.partner == "（自分）" else items.index(r.partner)
        M[i, j] = r.b; S[i, j] = (r.lo > 0) or (r.hi < 0)
    im = ax.imshow(np.clip(M, -2, 2), cmap="RdBu", vmin=-2, vmax=2)
    for i in range(len(items)):
        for j in range(len(items)):
            ax.text(j, i, f"{M[i,j]:.2f}" + ("*" if S[i, j] else ""), ha="center", va="center", fontsize=9)
    lab = [s.replace("発泡酒・ビール風アルコール飲料1)", "発泡酒") for s in items]
    ax.set_xticks(range(len(items))); ax.set_xticklabels(lab, fontsize=9)
    ax.set_yticks(range(len(items))); ax.set_yticklabels(lab, fontsize=9)
    ax.set_xlabel("値段が上がった品目"); ax.set_title(g)
axes[0].set_ylabel("買う量の変化")
fig.suptitle("交差弾力性：プラス＝代わりに買われる。22年分では多くがはっきりしない（*＝95%区間が0をまたがない）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f234_05_cross.png", dpi=150); plt.close()
print("ok")
