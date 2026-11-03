"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import ROOT, P

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
RES, FIG = ROOT / "results", ROOT / "figures"
S = json.load(open(RES / "summary.json", encoding="utf-8"))
C_LOC, C_SCALE, C_SHAPE = "#2a6f97", "#e9a23b", "#b5525c"

# 図1 分位関数と、全国に対する比
Q = pd.read_csv(RES / "quantiles_2023.csv", index_col=0, dtype={0: str})
from common import load, bins_of, quantiles
d = load(2023)
QF = {}
for code, g in d[(d.tenure == "総数") & (d["size"] == "total")].groupby("code"):
    QF[code] = quantiles(*bins_of(g))[0]
QF = pd.DataFrame(QF).T
nat = QF.loc["00000"].to_numpy(); Qp = QF.drop(index="00000")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
for c in Qp.index:
    ax[0].plot(P * 100, Qp.loc[c], color="#9aa5b1", lw=0.7, alpha=0.8)
    ax[1].plot(P * 100, Qp.loc[c] / nat, color="#9aa5b1", lw=0.7, alpha=0.8)
ax[0].plot(P * 100, nat, color="#1d3557", lw=2.2, label="全国")
ax[1].axhline(1, color="#1d3557", lw=2.2)
ax[0].set_ylim(0, 2000); ax[0].set_xlabel("下から何%の世帯か"); ax[0].set_ylabel("世帯の年間収入（万円）")
ax[0].set_title("47都道府県の分位関数（灰色）と全国", fontsize=12); ax[0].legend(frameon=False)
ax[1].set_ylim(0.6, 1.5); ax[1].set_xlabel("下から何%の世帯か"); ax[1].set_ylabel("全国の同じ分位点に対する比")
ax[1].set_title("全国に対する比：線はほぼ水平（全体が何倍かのずれ）", fontsize=12)
fig.text(0.01, 0.01, "出典：総務省「令和5年住宅・土地統計調査」第40-1表（主世帯、収入不詳を除く）を加工。分位関数は階級別の度数から単調スプラインとパレートの裾で推定", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig1_quantile_functions.png", dpi=160); plt.close()

# 図2 ばらつきの分解（位置・広がり・形）
R = S["robustness"]
rows = [("万円の目（基本）", S["frechet_2023"]), ("対数の目", S["log_frechet_2023"]),
        ("等価（√世帯人員で割る）", R["等価（世帯人員の平方根で割る）"]), ("階級内一様", R["階級内一様"]),
        ("2018年（万円）", S["robustness_2018"])]
fig, ax = plt.subplots(figsize=(10, 4.6))
for i, (lab, r) in enumerate(rows):
    l, s, h = r["loc"], r["scale"], r["shape"]
    ax.barh(i, l, color=C_LOC); ax.barh(i, s, left=l, color=C_SCALE); ax.barh(i, h, left=l + s, color=C_SHAPE)
    ax.text(l / 2, i, f"{l*100:.0f}%", ha="center", va="center", color="white", fontsize=10)
    if s > 0.04: ax.text(l + s / 2, i, f"{s*100:.0f}%", ha="center", va="center", color="black", fontsize=10)
    ax.text(1.01, i, f"形 {h*100:.0f}%", va="center", fontsize=9, color=C_SHAPE)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis(); ax.set_xlim(0, 1.12)
ax.set_xlabel("都道府県の分布のばらつき（2-Wasserstein 距離の2乗）に占める割合")
ax.bar(0, 0, color=C_LOC, label="位置（平均）"); ax.bar(0, 0, color=C_SCALE, label="広がり（標準偏差）"); ax.bar(0, 0, color=C_SHAPE, label="形（それ以外）")
ax.legend(ncol=3, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
fig.text(0.01, 0.01, "フレシェ平均（47都道府県の分位関数の平均）からの W² を、(平均の差)²＋(標準偏差の差)²＋2σσ'(1−相関) に分けた。出典：住宅・土地統計調査（2018・2023年）を加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig2_decomposition.png", dpi=160); plt.close()

# 図3 分位点ごとの都道府県の差
sp = pd.read_csv(RES / "spread_by_p_2023.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))
ax[0].plot(sp.p * 100, sp.sd_across_pref, color="#1d3557", lw=2)
ax[0].set_xlabel("下から何%の世帯か"); ax[0].set_ylabel("都道府県の間の標準偏差（万円）"); ax[0].set_title("差の大きさ（万円）は上の方ほど大きい", fontsize=12)
ax[1].plot(sp.p * 100, sp.cv * 100, color="#2a6f97", lw=2)
ax[1].set_ylim(0, 30); ax[1].set_xlabel("下から何%の世帯か"); ax[1].set_ylabel("標準偏差÷平均（%）"); ax[1].set_title("比で見ると、下の方がやや大きい（下5%は推定が不安定）", fontsize=12)
fig.text(0.01, 0.01, "出典：総務省「令和5年住宅・土地統計調査」第40-1表を加工。上下0.5%は使っていない", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig3_spread_by_quantile.png", dpi=160); plt.close()

# 図4 世帯の構成をそろえると
sh = pd.read_csv(RES / "dfl_mean_shift_2023.csv", index_col=0)
D = S["dfl_2023"]
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
ax[0].scatter(sh.one_person * 100, sh.shift_mean, color="#2a6f97", s=28)
ax[0].axhline(0, color="#888", lw=0.8)
ax[0].set_xlabel("単身世帯の割合（%）"); ax[0].set_ylabel("構成をそろえたときの平均の動き（万円）")
ax[0].set_title("単身が多い県は上がり、少ない県は下がる", fontsize=12)
labs = ["実際", "世帯人員を\nそろえる", "持ち家・借家を\nそろえる", "両方を\nそろえる"]
vals = [S["frechet_2023"]["frechet_sd"], np.sqrt(D["size"]["frechet_var"]), np.sqrt(D["tenure"]["frechet_var"]), np.sqrt(D["cell"]["frechet_var"])]
ax[1].bar(labs, vals, color=["#1d3557", "#9aa5b1", "#9aa5b1", "#9aa5b1"])
for i, v in enumerate(vals): ax[1].text(i, v + 1, f"{v:.1f}", ha="center")
ax[1].set_ylabel("都道府県の分布のばらつき（フレシェ標準偏差、万円）"); ax[1].set_ylim(0, 75)
ax[1].set_title("そろえても、差はほとんど縮まらない", fontsize=12)
fig.text(0.01, 0.01, "各県の「世帯人員×持ち家・借家」ごとの分布を、全国の構成の重みで混ぜ直した（DFL 型の反実仮想）。出典：住宅・土地統計調査（2023年）を加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig4_composition.png", dpi=160); plt.close()

# 図5 クラスタの頑健性
labs = ["平均だけで分ける", "平均と標準偏差で分ける", "世帯の構成をそろえる", "階級内一様", "対数の目", "等価", "不詳を一番下へ", "不詳を700〜1,000万円へ", "2018年"]
vals = [S["ari_full_vs_mean_only"], S["ari_full_vs_mean_sd"], S["ari_cluster_vs_composition_adjusted"], R["階級内一様"]["ari_vs_base"],
        R["対数（log(収入＋10万円)）"]["ari_vs_base"], R["等価（世帯人員の平方根で割る）"]["ari_vs_base"],
        R["不詳を一番下の階級（100万円未満）へ"]["ari_vs_base"], R["不詳を700〜1,000万円の階級へ"]["ari_vs_base"], S["change_2018_2023"]["ari_cluster_2018_2023"]]
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.barh(labs, vals, color="#2a6f97"); ax.invert_yaxis(); ax.set_xlim(0, 1)
for i, v in enumerate(vals): ax.text(v + 0.01, i, f"{v:.2f}", va="center")
ax.axvline(1, color="#888", lw=0.8)
ax.set_xlabel("基本の3分類との一致度（調整ランド指数、1＝完全に一致、0＝偶然と同じ）")
ax.set_title("分布でクラスタに分けても、条件を少し変えると顔ぶれが入れ替わる", fontsize=12)
fig.text(0.01, 0.01, "基本：2023年の分位関数（万円）に Ward 法で3つに分けた。2018年は2018年のデータで同じ手順。出典：住宅・土地統計調査を加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig5_cluster_stability.png", dpi=160); plt.close()

# 図6 2018→2023 の変化
ch = pd.read_csv(RES / "change_2018_2023.csv", index_col=0)
N = S["change_2018_2023"]["national"]
fig, ax = plt.subplots(figsize=(10, 4.6))
rng = np.random.default_rng(153)
for i, (col, lab) in enumerate([("dp10", "下から10%"), ("dp50", "中央値"), ("dp90", "下から90%")]):
    ax.scatter(i + rng.uniform(-0.15, 0.15, len(ch)), ch[col], color="#9aa5b1", s=20)
    ax.scatter(i, N[col], color="#1d3557", s=90, marker="D", zorder=3, label="全国" if i == 0 else None)
ax.axhline(0, color="#888", lw=0.8)
ax.set_xticks(range(3)); ax.set_xticklabels(["下から10%", "中央値", "下から90%"])
ax.set_ylabel("2018→2023年の変化（万円、名目）"); ax.legend(frameon=False)
ax.set_title(f"上の方ほど伸びた：47都道府県のうち{S['change_2018_2023']['n_dp90_gt_dp10']}で、90%点の伸び＞10%点の伸び", fontsize=12)
fig.text(0.01, 0.01, "2023年の階級を2018年と同じ10階級にそろえて推定。物価の変化は調整していない。出典：住宅・土地統計調査（2018・2023年）を加工", fontsize=8, color="#555")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig6_change_2018_2023.png", dpi=160); plt.close()
print("ok")
