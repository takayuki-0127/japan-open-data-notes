"""F295 04：図6枚。"""
import json, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from zz_f295_common import *

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 120})
D = os.path.join(os.path.dirname(__file__), "..")
R = os.path.join(D, "results"); F = os.path.join(D, "figures"); os.makedirs(F, exist_ok=True)
A = json.load(open(os.path.join(R, "A_main.json")))
B = pd.read_csv(os.path.join(R, "B_robustness.csv"))
C = json.load(open(os.path.join(R, "C_reask.json")))
KINDS = ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン", "共単調"]
COL = {"独立": "#9aa5b1", "ガウス": "#2b6cb0", "t": "#d97706", "グンベル": "#c53030",
       "裏返しクレイトン": "#805ad5", "共単調": "#2d3748"}
LAB = {"独立": "独立", "ガウス": "ガウス", "t": "t（自由度4）", "グンベル": "グンベル",
       "裏返しクレイトン": "裏返しクレイトン", "共単調": "完全に一緒"}
NOTE = "架空の会社・例示の値（シミュレーション）"


def save(fig, name):
    fig.text(0.99, 0.01, NOTE, ha="right", va="bottom", fontsize=8, color="#718096")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(F, name), dpi=150)
    plt.close(fig)


# 1. 4つのリスクの1年の損失（超える確率）
marg, _ = build_marginals()
fig, ax = plt.subplots(figsize=(8, 5))
cols = ["#c53030", "#2f855a", "#d97706", "#805ad5"]
p = 1 - (np.arange(marg.shape[0]) + 0.5) / marg.shape[0]
for k in range(4):
    x = marg[:, k] - marg[:, k].mean()
    sel = slice(int(marg.shape[0] * 0.5), None, 50)
    ax.plot(x[sel], p[sel], color=cols[k], label=MODULES[k], lw=2)
ax.set_yscale("log"); ax.axhline(0.005, color="#4a5568", ls="--", lw=1)
ax.axvline(100, color="#4a5568", ls=":", lw=1)
ax.text(102, 0.006, "200年に1度（99.5%点）＝平均＋100億円", fontsize=9, color="#4a5568")
ax.set_xlim(-50, 450); ax.set_ylim(1e-5, 0.6)
ax.set_xlabel("1年の損失（平均との差、億円）"); ax.set_ylabel("その額を超える確率（対数）")
ax.set_title("1. 4つのリスクは、200年に1度の額をそろえても裾の形が違う")
ax.legend(frameon=False)
save(fig, "f295_1_modules.png")

# 2. 分散効果（本計算）
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(KINDS)); w = 0.38
v = [A["res"][k]["db_var"] * 100 for k in KINDS]; ve = [A["res"][k]["db_var_se"] * 200 for k in KINDS]
t = [A["res"][k]["db_tvar"] * 100 for k in KINDS]; te = [A["res"][k]["db_tvar_se"] * 200 for k in KINDS]
ax.bar(x - w / 2, v, w, yerr=ve, color=[COL[k] for k in KINDS], label="VaR99.5で計る")
ax.bar(x + w / 2, t, w, yerr=te, color=[COL[k] for k in KINDS], alpha=0.45, hatch="//", label="TVaR99.5で計る")
for i in range(len(KINDS)):
    ax.text(x[i] - w / 2, v[i] + 1.2, f"{v[i]:.0f}", ha="center", fontsize=9)
    ax.text(x[i] + w / 2, t[i] + 1.2, f"{t[i]:.0f}", ha="center", fontsize=9)
ax.axhline(A["formula_db"] * 100, color="#1a202c", ls="--", lw=1.2)
ax.text(5.45, A["formula_db"] * 100 + 1.2, f"相関の表の式（ρ=0.25）{A['formula_db']*100:.0f}%", ha="right", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([LAB[k] for k in KINDS])
ax.set_ylabel("分散効果（%）"); ax.set_ylim(-2, 62)
ax.set_title("2. 同じ「つながりの強さ」でも、裾が一緒に動くと分散効果は小さくなる")
ax.legend(frameon=False, loc="upper right")
save(fig, "f295_2_db.png")

# 3. 自然災害と市場の順位（上の裾の重なり）
rng = np.random.default_rng(31)
fig, axs = plt.subplots(1, 4, figsize=(12, 3.6), sharex=True, sharey=True)
for ax, k in zip(axs, ["ガウス", "t", "グンベル", "裏返しクレイトン"]):
    U = sample_U(k, 20000, rng, rho=0.25)
    hit = (U[:, 0] > 0.95) & (U[:, 2] > 0.95)
    ax.scatter(U[:, 0], U[:, 2], s=3, color="#a0aec0", alpha=0.6)
    ax.scatter(U[hit, 0], U[hit, 2], s=4, color=COL[k])
    ax.add_patch(plt.Rectangle((0.95, 0.95), 0.05, 0.05, fill=False, ec=COL[k], lw=1.5))
    ax.set_xlim(0.8, 1); ax.set_ylim(0.8, 1)
    ax.set_title(f"{LAB[k]}\n両方が上位5%の年：{hit.sum()}（2万年中）", fontsize=10)
    ax.set_xlabel("自然災害の順位（上位20%を拡大）")
axs[0].set_ylabel("市場の順位")
fig.suptitle("3. ケンドールのτを同じ0.16にそろえても、両方が大きい年（右上の枠）の数が違う（独立なら約50）", fontsize=12)
save(fig, "f295_3_scatter.png")

# 4. 相関の大きさ・t の自由度
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
ax = axs[0]
rhos = [0.10, 0.25, 0.50]
for k in ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン"]:
    ys = []
    for r in rhos:
        if r == 0.25:
            ys.append(A["res"][k]["db_var"] * 100)
        else:
            ys.append(B[(B.check == "R2_rho") & (B.value.astype(str) == str(r)) & (B.kind == k)].db_var.iloc[0] * 100)
    ax.plot(rhos, ys, "o-", color=COL[k], label=LAB[k])
ax.plot(rhos, [formula_db(np.full(4, 100), equicorr(r)) * 100 for r in rhos], "k--", label="相関の表の式")
ax.set_xlabel("相関 ρ（すべての組み合わせ）"); ax.set_ylabel("分散効果（VaR99.5、%）")
ax.set_title("どの相関でもガウスが最大（ρ=0.10 では t・グンベル・クレイトンがほぼ並ぶ）", fontsize=10); ax.legend(frameon=False, fontsize=9)
ax = axs[1]
nus = [3, 4, 6, 10, 30]
ys = [B[(B.check == "R4_nu") & (B.value.astype(str) == str(n)) & (B.kind == "t")].db_var.iloc[0] * 100 if n != 4 else A["res"]["t"]["db_var"] * 100 for n in nus]
ax.plot(nus, ys, "o-", color=COL["t"], label="t コピュラ")
ax.axhline(A["res"]["ガウス"]["db_var"] * 100, color=COL["ガウス"], ls="-", lw=1, label="ガウス")
ax.axhline(A["formula_db"] * 100, color="k", ls="--", lw=1, label="相関の表の式")
ax.set_xscale("log"); ax.set_xticks(nus); ax.set_xticklabels(nus); ax.minorticks_off()
ax.set_xlabel("t コピュラの自由度（小さいほど裾が一緒に動く）"); ax.set_ylabel("分散効果（VaR99.5、%）")
ax.set_title("自由度が小さいほど分散効果は小さい"); ax.legend(frameon=False, fontsize=9)
fig.suptitle("4. 相関の大きさと、t コピュラの自由度を変えると", fontsize=12)
save(fig, "f295_4_rho_nu.png")

# 5. 自然災害の ξ
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
xis = [0.3, 0.5, 0.7]
for ax, col, ttl in [(axs[0], "db_var", "VaR99.5で計る"), (axs[1], "db_tvar", "TVaR99.5で計る")]:
    for k in ["独立", "ガウス", "t", "グンベル"]:
        ys = [B[(B.check == "R3_xi") & (B.value.astype(str) == str(x)) & (B.kind == k)][col].iloc[0] * 100 for x in xis]
        ax.plot(xis, ys, "o-", color=COL[k], label=LAB[k])
    ax.set_xticks(xis); ax.set_xlabel("自然災害の1件の損害の裾の指数 ξ"); ax.set_title(ttl)
axs[0].set_ylabel("分散効果（%）"); axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("5. 自然災害の裾が重いほど分散効果は小さい（TVaRで大きく出る）", fontsize=12)
save(fig, "f295_5_xi.png")

# 6. 問い直し：逆算した相関 vs データで測る相関
fig, ax = plt.subplots(figsize=(9, 4.8))
ks = ["独立", "ガウス", "t", "グンベル", "裏返しクレイトン"]
x = np.arange(len(ks)); w = 0.26
imp = [C["implied"]["0.25"][k]["implied_rho_var"] for k in ks]
spm = [C["data_corr"][k]["spearman"] for k in ks]
prs = [C["data_corr"][k]["pearson"] for k in ks]
ax.bar(x - w, imp, w, color=[COL[k] for k in ks], label="式に入れる必要のある相関（逆算）")
ax.bar(x, spm, w, color="#cbd5e0", label="損失で測る順位相関（スピアマン）")
ax.bar(x + w, prs, w, color="#e2e8f0", hatch="..", label="損失で測る相関（ピアソン）")
for i in range(len(ks)):
    ax.text(x[i] - w, imp[i] + (0.01 if imp[i] >= 0 else -0.04), f"{imp[i]:.2f}", ha="center", fontsize=9)
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([LAB[k] for k in ks])
ax.set_ylabel("相関"); ax.set_ylim(-0.12, 0.5)
ax.set_title("6. もう一度問う：式に入れるべき相関は、順位相関からは決まらない（ピアソンは向きは合うが足りない）", fontsize=11)
ax.legend(frameon=False, fontsize=9, loc="upper left")
save(fig, "f295_6_reask.png")
print("figures done")
