"""04 図：results/ の数字から図を5枚作る（figures/）。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RES, FIG, DATA = ROOT / "results", ROOT / "figures", ROOT / "data"
FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 110})
COL = ["#2b6cb0", "#dd6b20", "#2f855a", "#805ad5", "#c53030"]
summ = json.load(open(RES / "summary.json"))

# 1. 関数主成分：平均の形と、各主成分で動かした形
comp = pd.read_csv(RES / "fpc_components.csv")
sc = pd.read_csv(RES / "fpc_scores.csv", dtype={"code": str})
fig, axs = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
age = comp.age
for j, ax in enumerate(axs):
    sd = sc[f"fpc{j+1}"].std()
    ax.plot(age, comp["mean"] * 100, color="0.3", lw=2, label="平均の形")
    ax.plot(age, (comp["mean"] + 2 * sd * comp[f"phi{j+1}"]) * 100, color=COL[1], lw=1.6, label="＋2標準偏差")
    ax.plot(age, (comp["mean"] - 2 * sd * comp[f"phi{j+1}"]) * 100, color=COL[0], lw=1.6, label="−2標準偏差")
    ax.set_title(f"第{j+1}主成分（形の違いの {summ['fpc_ratio'][j]*100:.0f}%）")
    ax.set_xlabel("年齢")
axs[0].set_ylabel("その年齢の人の割合（%）")
axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("人口ピラミッドの形の違いは、ほとんどが第1主成分（若い↔高齢）で説明できる", y=1.02)
fig.tight_layout()
fig.savefig(FIG / "f171_1_fpca.png", bbox_inches="tight")
plt.close(fig)

# 2. いくつに分けるか
ck = pd.read_csv(RES / "choose_k.csv")
ckp = pd.read_csv(RES / "choose_k_pref.csv")
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.2))
axs[0].plot(ck.k, ck.silhouette, "o-", color=COL[0], label="市区町村（1,740）")
axs[0].plot(ckp.k, ckp.silhouette, "s--", color=COL[1], label="都道府県（47）")
axs[0].set_title("まとまりのよさ（シルエット）")
axs[0].set_xlabel("型の数 k")
axs[0].legend(frameon=False)
axs[1].plot(ck.k, ck.boot_ari_mean, "o-", color=COL[0], label="市区町村：平均")
axs[1].plot(ck.k, ck.boot_ari_p10, "o:", color=COL[0], alpha=.6, label="市区町村：下位10%")
axs[1].plot(ckp.k, ckp.boot_ari_mean, "s--", color=COL[1], label="都道府県：平均")
axs[1].axhline(0.8, color="0.6", lw=1)
axs[1].set_ylim(0, 1.02)
axs[1].set_title("標本を引き直しても同じ分け方になるか（ARI）")
axs[1].set_xlabel("型の数 k")
axs[1].legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "f171_2_choose_k.png", bbox_inches="tight")
plt.close(fig)

# 3. 3つに分けたときの型ごとの平均の形
mc = pd.read_csv(RES / "type_mean_curves_k3.csv")
ts = pd.read_csv(RES / "type_summary.csv")
t3 = ts[ts.k == 3].reset_index(drop=True)
names = ["型1（平均年齢が低め）", "型2（中間）", "型3（平均年齢が高め）"]
fig, ax = plt.subplots(figsize=(9, 4.6))
for i in range(3):
    r = t3.iloc[i]
    ax.plot(mc.age, mc[f"type{i+1}"] * 100, color=COL[i], lw=2.2,
            label=f"{names[i]}：{int(r.n)}市区町村・人口の{r.pop_share*100:.0f}%")
ax.set_xlabel("年齢")
ax.set_ylabel("その年齢の人の割合（%）")
ax.set_title("3つに分けたときの、型ごとの平均の形（2020年）")
ax.legend(frameon=False, fontsize=9.5)
fig.tight_layout()
fig.savefig(FIG / "f171_3_types_k3.png", bbox_inches="tight")
plt.close(fig)

# 4. 第1主成分の分布と、型の境目／2015年との比較
ub = pd.read_csv(RES / "types_by_unit.csv", dtype={"code": str})
sc = sc.set_index(sc.columns[0])
x = sc["fpc1"]
lab = ub.set_index("code")["type_k3"].reindex(x.index)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2))
bins = np.linspace(x.min(), x.max(), 45)
for i in range(3):
    axs[0].hist(x[lab == i + 1], bins=bins, color=COL[i], alpha=.85, label=names[i])
axs[0].set_title("第1主成分の得点：山は1つで、型は切れ目なく並ぶ")
axs[0].set_xlabel("第1主成分の得点（右ほど高齢寄りの形）")
axs[0].set_ylabel("市区町村の数")
axs[0].legend(frameon=False, fontsize=9)
ma = ub.set_index("code")["mean_age"]
axs[1].scatter(ma.reindex(x.index), x, s=6, c=[COL[int(v) - 1] for v in lab], alpha=.6)
axs[1].set_xlabel("平均年齢（歳）")
axs[1].set_ylabel("第1主成分の得点")
axs[1].set_title("第1主成分は平均年齢とほぼ同じもの（相関0.99）")
fig.tight_layout()
fig.savefig(FIG / "f171_4_continuum.png", bbox_inches="tight")
plt.close(fig)

# 5. 頑健性
rob = pd.read_csv(RES / "robustness_ari.csv")
pv = rob.pivot_table(index="check", columns="k", values="ari")
order = ["平滑化 λ=0", "平滑化 λ=1", "平滑化 λ=100", "平滑化 λ=1000", "年齢 0〜84歳", "年齢 0〜99歳",
         "人口1,000人以上だけ", "人口5,000人以上だけ", "男性だけ", "女性だけ", "2015年（同じ手順で分け直し）",
         "ウォード法（階層）", "混合正規分布"]
pv = pv.loc[order]
fig, ax = plt.subplots(figsize=(7.5, 6.2))
im = ax.imshow(pv.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(pv.shape[1]), [f"k={k}" for k in pv.columns])
ax.set_yticks(range(len(pv)), pv.index)
for i in range(pv.shape[0]):
    for j in range(pv.shape[1]):
        v = pv.values[i, j]
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="white" if v > .6 else "black", fontsize=10)
ax.set_title("条件を変えても同じ分け方になるか（主の分け方との ARI）")
fig.colorbar(im, ax=ax, fraction=.04)
fig.tight_layout()
fig.savefig(FIG / "f171_5_robustness.png", bbox_inches="tight")
plt.close(fig)
print("figures:", sorted(p.name for p in FIG.glob("*.png")))
