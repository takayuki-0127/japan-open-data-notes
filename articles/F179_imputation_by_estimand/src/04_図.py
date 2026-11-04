"""04 図：results/ から5枚の図を作る。"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

from common import FIG, RES

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

MJ = {"full": "欠かす前", "avail": "値がある町だけ", "mean": "平均で埋める", "reg": "回帰で1回埋める",
      "sreg": "回帰＋ばらつきで1回", "knn": "近い5町で埋める", "forest": "木のモデルで埋める",
      "mi_norm": "多重代入（正規）", "mi_pmm": "多重代入（PMM）"}
EJ = {"mean_tax": "地方税の平均", "p90_tax": "地方税の90%点", "sd_unemp": "失業率の標準偏差",
      "share_unemp5": "失業率5%以上の割合", "corr_unemp_tert": "失業率と3次産業の相関",
      "coef_tert": "回帰係数（3次産業）"}
MECH = {"mcar": "でたらめに欠ける", "mar": "人口が小さい町ほど欠ける", "mnar": "値が大きいほど欠ける"}
EST = list(EJ)
S = pd.read_csv(RES / "sim_summary.csv")
main = S[S.tag.isin(["main", "forest"])]

# 1) 欠け方
P = pd.read_csv(RES / "missing_pattern.csv")
P = P[(P.pop_decile != "all") & (P["var"] == "logtax")].copy()
P["pop_decile"] = P.pop_decile.astype(int)
fig, ax = plt.subplots(figsize=(7, 4.2))
for mech, c in zip(MECH, ["#888888", "#1f6fb4", "#d1495b"]):
    d = P[P.mech == mech]
    ax.plot(d.pop_decile, 100 * d.miss_rate, marker="o", color=c, label=MECH[mech])
ax.set_xticks(range(1, 11))
ax.set_xlabel("人口の十分位（1＝いちばん小さい町）")
ax.set_ylabel("地方税が欠けた割合（%）")
ax.set_title("3つの欠け方（どれも全体では30%を欠かす）", loc="left")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG / "f179_1_missing_pattern.png", dpi=150)
plt.close(fig)

# 2) 偏り（欠かす前の推定の揺れ＝標準偏差の何倍か）
methods = ["avail", "mean", "reg", "sreg", "knn", "forest", "mi_norm", "mi_pmm"]
fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), sharey=True)
for ax, mech in zip(axes, MECH):
    d = main[main.mech == mech]
    full_sd = d[d.method == "full"].set_index("est")["sd"]
    M = np.full((len(methods), len(EST)), np.nan)
    for i, m in enumerate(methods):
        dd = d[d.method == m].set_index("est")
        for j, e in enumerate(EST):
            if e in dd.index:
                M[i, j] = dd.loc[e, "bias"] / full_sd[e]
    im = ax.imshow(np.clip(M, -6, 6), cmap="RdBu_r", vmin=-6, vmax=6, aspect="auto")
    for i in range(len(methods)):
        for j in range(len(EST)):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:+.1f}", ha="center", va="center", fontsize=8,
                        color="white" if abs(M[i, j]) > 3.5 else "black")
    ax.set_xticks(range(len(EST)))
    ax.set_xticklabels([EJ[e] for e in EST], rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels([MJ[m] for m in methods])
    ax.set_title(MECH[mech], fontsize=10)
fig.suptitle("偏り：欠かす前の推定のばらつき（標準偏差）の何倍ずれたか", x=0.01, ha="left")
fig.colorbar(im, ax=axes, shrink=0.8, label="偏り ÷ 標準偏差（±6で頭打ち）")
fig.savefig(FIG / "f179_2_bias.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 3) 95%区間が真の値を含んだ割合
SEE = ["mean_tax", "share_unemp5", "corr_unemp_tert", "coef_tert"]
cm = ["full", "avail", "mean", "reg", "sreg", "knn", "mi_norm", "mi_pmm"]
fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
for ax, mech in zip(axes, MECH):
    d = main[(main.mech == mech) & main.method.isin(cm)]
    w = 0.8 / len(SEE)
    for k, e in enumerate(SEE):
        v = [d[(d.method == m) & (d.est == e)]["cover"].mean() * 100 for m in cm]
        ax.bar(np.arange(len(cm)) + (k - 1.5) * w, v, width=w, label=EJ[e])
    ax.axhline(95, color="k", lw=0.8, ls="--")
    ax.set_xticks(range(len(cm)))
    ax.set_xticklabels([MJ[m] for m in cm], rotation=45, ha="right", fontsize=8)
    ax.set_title(MECH[mech], fontsize=10)
    ax.set_ylim(0, 100)
axes[0].set_ylabel("95%区間が真の値を含んだ割合（%）")
fig.legend(*axes[0].get_legend_handles_labels(), fontsize=8, frameon=False, loc="lower center", ncol=4)
fig.suptitle("区間の当たり：1回だけ埋めると、区間が狭すぎて外れやすい（点線＝95%）", x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.06, 1, 1))
fig.savefig(FIG / "f179_3_coverage.png", dpi=150)
plt.close(fig)

# 4) 町の大きさで分けて埋める（人口が小さい町ほど欠ける場合）
mar = S[S.mech == "mar"]
rows = [("値がある町だけ", "main", "avail"), ("多重代入（正規）", "main", "mi_norm"), ("多重代入（PMM）", "main", "mi_pmm"),
        ("分けて多重代入（正規）", "norm_strata5", "mi_norm"), ("分けて多重代入（PMM）", "pmm_strata5", "mi_pmm")]
full_sd = mar[(mar.tag == "main") & (mar.method == "full")].set_index("est")["sd"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
cols = ["#999999", "#9ecae1", "#3182bd", "#fdae6b", "#e6550d"]
w = 0.8 / len(rows)
for i, (lab, tag, m) in enumerate(rows):
    d = mar[(mar.tag == tag) & (mar.method == m)].set_index("est")
    axes[0].barh(np.arange(len(EST)) + (i - 2) * w, [d.loc[e, "bias"] / full_sd[e] for e in EST], height=w,
                 color=cols[i], label=lab)
    axes[1].barh(np.arange(len(SEE)) + (i - 2) * w, [100 * d.loc[e, "cover"] for e in SEE], height=w, color=cols[i])
axes[0].set_yticks(range(len(EST)))
axes[0].set_yticklabels([EJ[e] for e in EST])
axes[0].axvline(0, color="k", lw=0.8)
axes[0].invert_yaxis()
axes[0].set_xlabel("偏り ÷ 欠かす前の標準偏差")
axes[0].set_title("偏り", loc="left")
axes[1].set_yticks(range(len(SEE)))
axes[1].set_yticklabels([EJ[e] for e in SEE])
axes[1].axvline(95, color="k", lw=0.8, ls="--")
axes[1].invert_yaxis()
axes[1].set_xlim(0, 100)
axes[1].set_xlabel("95%区間が真の値を含んだ割合（%）")
axes[1].set_title("区間の当たり", loc="left")
fig.legend(*axes[0].get_legend_handles_labels(), fontsize=8, frameon=False, loc="lower center", ncol=5)
fig.suptitle("人口が小さい町ほど欠けるとき：人口で5つに分けてから埋めると、偏りが縮み区間が当たる", x=0.01, ha="left")
fig.tight_layout(rect=(0, 0.07, 1, 1))
fig.savefig(FIG / "f179_6_strata.png", dpi=150)
plt.close(fig)

# 4) 埋める回数 m
Mm = pd.read_csv(RES / "m_summary.csv")
fig, ax = plt.subplots(figsize=(7, 4.2))
for e in SEE:
    d = Mm[Mm.est == e]
    ax.plot(d.m, d.q_sd_over_se, marker="o", label=f"{EJ[e]}（fmi {d.ref_fmi.iloc[0]:.2f}）")
ax.set_xscale("log")
ax.minorticks_off()
ax.set_xticks(sorted(Mm.m.unique()))
ax.set_xticklabels(sorted(Mm.m.unique()))
ax.set_xlabel("埋める回数 m")
ax.set_ylabel("埋め直しによる答えの揺れ ÷ 標準誤差")
ax.set_title("同じデータを埋め直すと、答えはどれだけ動くか", loc="left")
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "f179_4_m.png", dpi=150)
plt.close(fig)

# 5) 埋めた値の分布（地方税）
T = pd.read_csv(RES / "imputed_tax_dist.csv")
T["tax"] = np.exp(T.logtax)
fig, axes = plt.subplots(1, 4, figsize=(13, 3.8), sharex=True, sharey=True)
bins = np.linspace(np.log(60), np.log(400), 40)
true = T[T.kind == "true_missing"].logtax
for ax, k in zip(axes, ["mean", "reg", "mi_norm", "mi_pmm"]):
    ax.hist(true, bins=bins, color="#cccccc", label="欠かした町の本当の値")
    ax.hist(T[T.kind == k].logtax, bins=bins, histtype="step", lw=1.8, color="#d1495b", label="埋めた値")
    ax.set_title(MJ[k], fontsize=10)
    ticks = [75, 100, 150, 200, 300]
    ax.set_xticks(np.log(ticks))
    ax.set_xticklabels(ticks)
axes[0].set_ylim(0, 130)
n_mean = int((T.kind == "mean").sum())
axes[0].annotate(f"{n_mean}町がすべて同じ値\n（棒は上で切れている）", xy=(np.log(143), 128), xytext=(np.log(170), 95), fontsize=8,
                 arrowprops=dict(arrowstyle="->", lw=0.8))
axes[0].set_ylabel("市区町村の数")
axes[0].legend(fontsize=7, frameon=False)
fig.supxlabel("1人あたり地方税（千円、対数目盛）", fontsize=9)
fig.suptitle("人口が小さい町ほど欠けるとき、埋めた地方税の分布", x=0.01, ha="left")
fig.tight_layout()
fig.savefig(FIG / "f179_5_tax_dist.png", dpi=150)
plt.close(fig)
print("図6枚")
