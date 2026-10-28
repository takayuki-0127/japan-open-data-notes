"""図（5枚）"""
import json
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f: font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
from common import DATA, RES, FIG
FIG.mkdir(exist_ok=True)
R = json.load(open(RES / "results.json", encoding="utf-8"))
CUR = pd.read_csv(RES / "apc_effects_by_constraint.csv")
ROB = pd.read_csv(RES / "robustness.csv")
SRC = "出典：国立社会保障・人口問題研究所「人口統計資料集（2025）」表6-24・6-23（総務省「国勢調査」）を加工"
CONS = ["IE（最小ノルム）", "時代に直線の流れなし", "コホートに直線の流れなし", "最初の2時代が等しい", "最初の2コホートが等しい"]
CC = ["#333333", "#2e86c1", "#c0392b", "#27ae60", "#8e44ad"]

def foot(fig, s=SRC, y=-0.03):
    fig.text(.01, y, s, fontsize=8, color="gray")

# 1 年齢×年の未婚割合（ヒートマップ）
u = pd.read_csv(DATA / "unmarried_pct.csv")
ages = ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54"]
yrs = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2015, 2020]
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
for ax, sex in zip(axs, ["女", "男"]):
    M = u[(u.sex == sex)].pivot(index="age", columns="year", values="unmarried_pct").loc[ages, yrs]
    im = ax.imshow(M.values, cmap="YlOrRd", vmin=0, vmax=100, aspect="auto")
    for i in range(len(ages)):
        for j in range(len(yrs)):
            v = M.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 60 else "black")
    ax.set_xticks(range(len(yrs))); ax.set_xticklabels(yrs, rotation=45)
    ax.set_yticks(range(len(ages))); ax.set_yticklabels([a.replace("-", "～") + "歳" for a in ages])
    ax.set_title(f"{sex}性", loc="left")
fig.colorbar(im, ax=axs, shrink=.8, label="未婚の割合（%）")
fig.suptitle("年齢×調査年の未婚割合：右へ（時代）も、斜め右下へ（同じ生まれ年）も濃くなる", x=.01, ha="left")
foot(fig); fig.savefig(FIG / "f87_lexis.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 2 50歳時未婚割合を生まれ年で
r = pd.DataFrame(R["unmarried50"]).sort_values("birth")
fig, ax = plt.subplots(figsize=(9, 4.8))
for sex, c in [("男", "#2e86c1"), ("女", "#c0392b")]:
    ax.plot(r.birth, r[sex], marker="o", ms=4, color=c, label=f"{sex}性")
ax.set_xlabel("生まれ年（調査年−50）"); ax.set_ylabel("50歳時の未婚割合（%）")
ax.set_title("50歳時の未婚割合を「生まれ年」で並べる\n1930年代生まれまでは数%、1940年代生まれから上がり始め、1960年代生まれで急に上がる", loc="left")
ax.grid(alpha=.3); ax.legend(frameon=False)
foot(fig, SRC + "。50歳時は45～49歳と50～54歳の平均"); fig.savefig(FIG / "f87_unmarried50.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 3 制約を変えた時代効果・コホート効果（女）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.8))
for k, (kind, ttl, xl) in enumerate([("period", "時代効果", "調査年"), ("cohort", "コホート効果", "生まれ年（10年ごと、調査年−年齢の下端）")]):
    ax = axs[k]
    for nm, c in zip(CONS, CC):
        d = CUR[(CUR.sex == "女") & (CUR.constraint == nm) & (CUR.kind == kind)]
        ax.plot(d.level.astype(int), d.effect, marker="o", ms=4, color=c, label=nm, lw=2.2 if nm == "IE（最小ノルム）" else 1.4)
    ax.axhline(0, color="gray", lw=.8); ax.set_title(f"{ttl}（女性）", loc="left"); ax.set_xlabel(xl); ax.grid(alpha=.3)
axs[0].set_ylabel("既婚側のロジット（大きいほど結婚している人が多い）")
axs[1].legend(frameon=False, fontsize=8)
fig.suptitle("当てはまりがまったく同じ5つの答え：制約の置き方で「時代」と「世代」の取り分が入れ替わる", x=.01, ha="left")
foot(fig); fig.savefig(FIG / "f87_constraints.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 4 t を動かしたときの1970→2020の時代効果
fig, ax = plt.subplots(figsize=(9, 4.8))
for sex, c in [("女", "#c0392b"), ("男", "#2e86c1")]:
    tp = pd.DataFrame(R[sex]["t_path"])
    ax.plot(tp.t, tp.period_1970_2020, color=c, label=f"{sex}性：1970→2020の時代効果")
    for nm, cc in zip(CONS, CC):
        t = R[sex]["constraints_t"][nm]
        y = np.interp(t, tp.t, tp.period_1970_2020)
        ax.scatter([t], [y], color=cc, zorder=3, s=30)
for nm, cc in zip(CONS, CC):
    ax.scatter([], [], color=cc, label=nm, s=30)
ax.axhline(0, color="gray", lw=.8)
ax.set_xlabel("t：時代から年齢・コホートへ移す直線の傾き（10年あたり、ロジット）\nどの t でも当てはまりは同じ")
ax.set_ylabel("1970→2020 の時代効果（ロジット差）")
ax.set_title("「時代のせい」の大きさは、データではなく制約が決める\n同じデータでも、ほぼ0から−3まで動く", loc="left")
ax.grid(alpha=.3); ax.legend(frameon=False, fontsize=8, ncol=2)
foot(fig, y=-0.07); fig.savefig(FIG / "f87_t_path.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 5 識別できる比較：年齢＋時代 vs 年齢＋コホート（BIC差）
ROB["dBIC"] = ROB["BIC_年齢+コホート"] - ROB["BIC_年齢+時代"]
fig, ax = plt.subplots(figsize=(9, 5.4))
y = np.arange(len(ROB))[::-1]
cols = ["#c0392b" if v < 0 else "#2e86c1" for v in ROB.dBIC]
ax.barh(y, ROB.dBIC, color=cols)
ax.set_yticks(y); ax.set_yticklabels(ROB["設定"].str.replace("・10歳階級", "").replace({"男": "基本と同じ設定（男）"}), fontsize=8)
ax.axvline(0, color="black", lw=.8)
ax.set_xlabel("BIC（年齢＋コホート）− BIC（年齢＋時代）　　左（赤）＝世代で説明するほうが当てはまる")
ax.set_title("制約なしで比べられること：「年齢＋世代」と「年齢＋時代」のどちらが当てはまるか\n未婚割合では、どの設定でも世代のほうが当てはまる。初婚率（毎年の流れ）では逆か互角", loc="left")
ax.grid(alpha=.3, axis="x")
foot(fig, SRC + "、表6-9（厚生労働省「人口動態統計」）", y=-0.06); fig.savefig(FIG / "f87_two_factor.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("ok")
