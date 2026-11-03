"""04 図：5枚"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import RES, FIG

for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    try:
        fm.fontManager.addfont(p)
    except Exception:
        pass
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C = ["#1f5f8b", "#e07b39", "#3a9d5d", "#8e5ea2", "#c0392b"]

S = json.load(open(RES / "summary.json"))
med = pd.read_csv(RES / "screening_eps_median.csv").set_index("eps")
eps = med.index.to_numpy()

# 1. 規模別の誤差
fig, ax = plt.subplots(figsize=(7.5, 4.8))
for i, lab in enumerate(["500人未満", "500〜2,000人", "2,000〜1万人", "1万人以上"]):
    v = med[f"mae_{lab}"].replace(0, np.nan)
    ax.plot(eps, v, "o-", color=C[i], label=f"対象者 {lab}")
ax.set_xscale("log"); ax.set_yscale("log")
ax.axhline(1, color="gray", lw=0.8, ls="--"); ax.text(eps[-1], 1.1, "1ポイント", ha="right", color="gray", fontsize=9)
ax.set_xlabel("ε（左ほどプライバシーが強い＝ノイズが大きい）")
ax.set_ylabel("受診率の誤差（ポイント、中央値）")
ax.set_title("ノイズによる受診率のずれは、小さい町ほど大きい\n（大腸がん検診・2023年度・1,654市区町村、200回の中央値）", fontsize=11)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f146_1_error_by_size.png", dpi=150); plt.close()

# 2. 分析の種類ごとの「答えの変わり方」
smr = pd.read_csv(RES / "smr_eps_median.csv")
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.plot(eps, med["spearman"], "o-", color=C[0], label="検診：順位の相関")
ax.plot(eps, med["top50_overlap"], "s-", color=C[1], label="検診：上位50の一致")
ax.plot(eps, med["funnel_kappa"], "^-", color=C[2], label="検診：ファンネルの外れの一致（κ）")
st = smr[smr.cause == "stroke"].set_index("eps")
al = smr[smr.cause == "all"].set_index("eps")
ax.plot(st.index, st["top50_overlap"], "s--", color=C[3], label="死亡（脳血管）：上位50の一致")
ax.plot(al.index, al["top50_overlap"], "s:", color=C[4], label="死亡（全死因）：上位50の一致")
ax.set_xscale("log"); ax.set_ylim(0, 1.03)
ax.set_xlabel("ε（左ほどノイズが大きい）"); ax.set_ylabel("ノイズなしの答えとの一致")
ax.set_title("順位の相関より、「上位50」のほうが早く崩れる", fontsize=11)
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f146_2_agreement.png", dpi=150); plt.close()

# 3. 上位50に入る小さい町の割合：ノイズ vs 秘匿
sup = pd.DataFrame(S["suppression"])
true_share = S["screening_base"]["top50_small_share_true"]
fig, axs = plt.subplots(1, 2, figsize=(9, 4.6), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
ax = axs[0]
ax.plot(eps, med["top50_small_share"] * 100, "o-", color=C[0])
ax.axhline(true_share * 100, color="gray", ls="--"); ax.text(eps[0], true_share * 100 + 1.5, f"ノイズなし {true_share*100:.0f}%", fontsize=9, color="gray")
ax.set_xscale("log"); ax.set_xlabel("ε（左ほどノイズが大きい）")
ax.set_ylabel("上位50のうち、対象者500人未満の町の割合（%）")
ax.set_title("ノイズ：小さい町が上位に増える", fontsize=11)
ax = axs[1]
x = np.arange(len(sup))
ax.bar(x, sup["top50_small_share"] * 100, color=C[1])
for i, r in sup.iterrows():
    ax.text(i, r.top50_small_share * 100 + 1.5, f"{r.top50_small_share*100:.0f}%", ha="center", fontsize=10)
    ax.text(i, 4, f"伏せた\n小さい町\n{r.hidden_small_share*100:.0f}%", ha="center", fontsize=8, color="white")
ax.axhline(true_share * 100, color="gray", ls="--")
ax.set_xticks(x); ax.set_xticklabels([f"{k}人未満" for k in sup.k])
ax.set_xlabel("受診者が何人未満の町を伏せるか")
ax.set_title("秘匿：小さい町が上位から消える", fontsize=11)
ax.set_ylim(0, 95)
fig.suptitle("同じ「上位50」の顔ぶれが、ノイズと秘匿で逆の向きにずれる（大腸がん検診・2023年度）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f146_3_noise_vs_suppression.png", dpi=150); plt.close()

# 4. 集計の細かさ：県の率
pdir = pd.read_csv(RES / "pref_direct.csv").set_index("eps")
fig, ax = plt.subplots(figsize=(7.5, 4.6))
ax.plot(eps, med["pref_sum_err_pt"], "o-", color=C[0], label="市区町村にノイズ → 県に足し上げ")
ax.plot(pdir.index, pdir["pref_direct_err_pt"].replace(0, np.nan), "s-", color=C[1], label="県の合計に直接ノイズ")
ax.plot(eps, med["mae_all"].replace(0, np.nan), "^:", color="gray", label="（参考）市区町村の率そのもの")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("ε（左ほどノイズが大きい）"); ax.set_ylabel("率の誤差（ポイント、中央値）")
ax.set_title("同じ ε でも、細かく出すほど足し上げたときの誤差は大きい", fontsize=11)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f146_4_granularity.png", dpi=150); plt.close()

# 5. 回帰の係数
rm = pd.read_csv(RES / "reg_eps_median.csv").set_index("eps")
rl = pd.read_csv(RES / "reg_eps_lo.csv").set_index("eps")
rh = pd.read_csv(RES / "reg_eps_hi.csv").set_index("eps")
tr = S["reg_true"]
fig, axs = plt.subplots(1, 2, figsize=(9, 4.4))
for ax, k, lab in [(axs[0], "young_f", "15〜39歳女性の割合"), (axs[1], "density", "人口密度（対数）")]:
    b, se = tr["coef"][k], tr["se"][k]
    ax.axhspan(b - 1.96 * se, b + 1.96 * se, color="gray", alpha=0.2, label="ノイズなしの95%区間")
    ax.axhline(b, color="gray", lw=1)
    ax.fill_between(rm.index, rl[f"b_{k}"], rh[f"b_{k}"], color=C[0], alpha=0.25, label="ノイズを入れた200回の95%")
    ax.plot(rm.index, rm[f"b_{k}"], "o-", color=C[0], label="中央値")
    ax.set_xscale("log"); ax.set_xlabel("ε（左ほどノイズが大きい）")
    ax.set_title(f"{lab}の係数", fontsize=11)
axs[0].set_ylabel("出生率の差（1標準偏差あたり）")
axs[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("出生率の回帰（F20）：ε が小さいと、ノイズを入れた変数の係数が0に寄る", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f146_5_regression.png", dpi=150); plt.close()
print("ok")
