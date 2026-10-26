"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import TwoSlopeNorm, Normalize, LogNorm
from scipy import stats
from common import FIG, RES, DATA, load_topo

fits = json.load(open(RES / "fits.json", encoding="utf-8"))
cmp = json.load(open(RES / "compare_published.json", encoding="utf-8"))
rings, _ = load_topo()
t = pd.read_csv(RES / "theta_main.csv", dtype={"code": str}).set_index("code")
SRC = "出典：厚生労働省「人口動態保健所・市区町村別統計（平成30年〜令和4年）」をもとに作成。灰色はデータなし"


def draw(ax, values, cmap, norm, title, cbar_label=""):
    polys, cols = [], []
    for code, rs in rings.items():
        for rr in rs:
            polys.append(rr)
            cols.append(values.get(code, np.nan))
    cols = np.array(cols, dtype=float)
    cm = plt.get_cmap(cmap)
    fc = ["#e6e6e6" if np.isnan(v) else cm(norm(v)) for v in cols]
    ax.add_collection(PolyCollection(polys, facecolors=fc, edgecolors="none", linewidths=0))
    ax.set_xlim(128.5, 146.2)
    ax.set_ylim(30.8, 45.7)
    ax.set_aspect(1.25)
    ax.axis("off")
    ax.set_title(title, fontsize=11)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    cb = plt.colorbar(sm, ax=ax, fraction=0.035, pad=0.01)
    cb.set_label(cbar_label, fontsize=8)


m = fits["main"]
# 1 素の SMR と BYM2 の地図を並べる
fig, axs = plt.subplots(1, 2, figsize=(13, 6.4))
norm = TwoSlopeNorm(vcenter=100, vmin=75, vmax=125)
draw(axs[0], t["smr_raw"].to_dict(), "RdBu_r", norm, f"素の標準化死亡比（全死因・男女計）\n範囲 {m['range_raw'][0]:.0f}〜{m['range_raw'][1]:.0f}", "全国＝100")
draw(axs[1], t["smr_bym2"].to_dict(), "RdBu_r", norm, f"BYM2 で推定した標準化死亡比\n範囲 {m['range_bym2'][0]:.0f}〜{m['range_bym2'][1]:.0f}", "全国＝100")
fig.text(0.02, 0.01, SRC + "。色は75〜125で頭打ち", fontsize=7.5)
fig.savefig(FIG / "f27_1_maps_raw_vs_bym2.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 2 ファネル：期待死亡数と素の SMR
fig, ax = plt.subplots(figsize=(8.5, 5.6))
E = np.logspace(np.log10(t["E"].min() * 0.9), np.log10(t["E"].max() * 1.1), 200)
for p, ls in [(0.975, "--"), (0.999, "-")]:
    z = stats.norm.ppf(p)
    ax.plot(E, 100 * (1 + z / np.sqrt(E)), "k" + ls, lw=0.8)
    ax.plot(E, 100 * (1 - z / np.sqrt(E)), "k" + ls, lw=0.8, label=f"偶然だけで出る範囲（{'95' if p == 0.975 else '99.8'}%）")
ax.scatter(t["E"], t["smr_raw"], s=6, c="#3b6ea5", alpha=0.5, lw=0, label="素の SMR")
ax.scatter(t["E"], t["smr_bym2"], s=6, c="#d1495b", alpha=0.5, lw=0, label="BYM2")
ax.set_xscale("log")
ax.set_ylim(40, 180)
ax.axhline(100, color="gray", lw=0.6)
ax.set_xlabel("期待死亡数（5年間、男女計、対数目盛り）")
ax.set_ylabel("標準化死亡比（全国＝100）")
fs = json.load(open(RES / "funnel_summary.json", encoding="utf-8"))
ax.set_title(f"小さな町ほど素の SMR は大きくぶれる。99.8%範囲の外：{fs['funnel_out_share']*100:.0f}%（偶然だけでは説明できない差もある）", fontsize=10)
ax.legend(fontsize=8, loc="upper right")
fig.text(0.02, 0.005, SRC, fontsize=7.5)
fig.savefig(FIG / "f27_2_funnel.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 3 事後分布の幅（95%区間の幅）の地図と、期待死亡数との関係
fig, axs = plt.subplots(1, 2, figsize=(13, 6.0), gridspec_kw={"width_ratios": [1.15, 1]})
w = (t["hi"] - t["lo"])
draw(axs[0], w.to_dict(), "viridis_r", Normalize(0, 30), "BYM2 の 95% 区間の幅（SMR のポイント）", "幅")
axs[1].scatter(t["E"], w, s=6, alpha=0.5, lw=0)
axs[1].set_xscale("log")
axs[1].set_xlabel("期待死亡数（対数目盛り）")
axs[1].set_ylabel("95% 区間の幅")
axs[1].set_title(f"区間が100をまたがない区域：{m['share_ci_excl_100']*100:.0f}%", fontsize=10)
fig.text(0.02, 0.01, SRC, fontsize=7.5)
fig.savefig(FIG / "f27_3_uncertainty.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 4 空間効果と区域ごとの効果
fig, axs = plt.subplots(1, 2, figsize=(13, 6.4))
nm = TwoSlopeNorm(vcenter=0, vmin=-0.25, vmax=0.25)
draw(axs[0], t["spatial"].to_dict(), "PuOr_r", nm, "空間効果（隣と共通の部分）", "log SMR")
draw(axs[1], t["iid"].to_dict(), "PuOr_r", nm, "区域ごとの効果（隣と関係ない部分）", "log SMR")
fig.text(0.02, 0.01, f"ばらつきのうち空間効果の割合 ρ = {m['rho'][0]:.2f}（95%区間 {m['rho'][1]:.2f}〜{m['rho'][2]:.2f}）。" + SRC, fontsize=7.5)
fig.savefig(FIG / "f27_4_spatial_iid.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 5 公表のベイズ推定値との比較（男性・女性）
df = pd.read_csv(DATA / "smr_2018_22.csv", dtype={"code": str}).set_index("code")
fig, axs = plt.subplots(1, 2, figsize=(11, 5.2))
for ax, (tag, sex, lab) in zip(axs, [("male", "m", "男性"), ("female", "f", "女性")]):
    tt = pd.read_csv(RES / f"theta_{tag}.csv", dtype={"code": str}).set_index("code")
    b = df.loc[tt.index, f"bayes_all_{sex}"]
    ax.scatter(b, tt["smr_raw"], s=5, c="#3b6ea5", alpha=0.35, lw=0, label=f"素の SMR（相関 {cmp[tag]['corr_raw']:.2f}）")
    ax.scatter(b, tt["smr_bym2"], s=5, c="#d1495b", alpha=0.5, lw=0, label=f"BYM2（相関 {cmp[tag]['corr']:.2f}）")
    ax.plot([60, 160], [60, 160], "k--", lw=0.7)
    ax.set_xlim(60, 160)
    ax.set_ylim(40, 180)
    ax.set_xlabel("公表のベイズ推定値（第5表）")
    ax.set_ylabel("この記事の値")
    ax.set_title(f"{lab}：全死因", fontsize=11)
    ax.legend(fontsize=8)
fig.text(0.02, 0.005, "公表値は都道府県の値を事前の情報に使うベイズ推定。この記事は隣接する区域の情報を借りる BYM2。" + SRC, fontsize=7)
fig.savefig(FIG / "f27_5_vs_published.png", dpi=150, bbox_inches="tight")
plt.close(fig)

# 6 頑健性：ρ と σ、本体との相関
tags = [("main", "本体（PC事前分布・接する区域）"), ("prior_wide", "広い事前分布"), ("knn6", "隣＝近い6区域"),
        ("covariates", "共変量あり"), ("male", "男性"), ("female", "女性"),
        ("cancer", "悪性新生物"), ("heart", "心疾患"), ("stroke", "脳血管疾患")]
fig, axs = plt.subplots(1, 2, figsize=(11.5, 5))
ys = np.arange(len(tags))[::-1]
for k, (key, lab) in enumerate([("rho", "空間効果の割合 ρ"), ("sigma", "全体のばらつき σ（log SMR）")]):
    ax = axs[k]
    for y, (tag, name) in zip(ys, tags):
        if tag not in fits:
            continue
        v = fits[tag][key]
        ax.errorbar(v[0], y, xerr=[[v[0] - v[1]], [v[2] - v[0]]], fmt="o", color="#d1495b" if tag == "main" else "#3b6ea5", ms=4, capsize=2)
    ax.set_yticks(ys)
    ax.set_yticklabels([n for _, n in tags] if k == 0 else [])
    ax.set_title(lab, fontsize=11)
    ax.grid(axis="x", alpha=0.3)
axs[0].set_xlim(0, 1)
fig.text(0.02, 0.005, "点は事後平均、線は95%区間。" + SRC, fontsize=7.5)
fig.savefig(FIG / "f27_6_robustness.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("ok")
