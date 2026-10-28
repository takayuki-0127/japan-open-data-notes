"""04 図"""
import json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from patsy import dmatrix
import statsmodels.api as sm
from common import ROOT, T, Y, X, LO, HI

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e5e5e5", "grid.linewidth": 0.6})
C = {"naive": "#9a9a9a", "ols": "#2a78b5", "gps": "#d1603d", "ipw": "#3a9a5b"}
LAB = {"naive": "そのまま（条件なし）", "ols": "回帰で調整", "gps": "一般化傾向スコア（GPS）", "ipw": "IPW（安定化重み）"}
FIG = ROOT / "figures"
r = json.load(open(ROOT / "results/results.json"))
D = pd.read_csv(ROOT / "data/analysis_2018_22.csv", dtype={"code": str, "pref": str})
g = np.array(r["grid"])
NAMES = {"young_f": "15〜39歳女性の割合", "income": "所得（対数）", "tertiary": "第3次産業の割合",
         "density": "人口密度（対数）", "aged": "65歳以上の割合", "nursery": "保育所数", "unmarried": "未婚者の割合"}

# 1 散布図
fig, ax = plt.subplots(figsize=(7.5, 5))
ax.scatter(D[T], D[Y], s=7, alpha=0.35, color="#6b6b6b", lw=0)
c = r["curves"]["naive"]
ax.plot(g, c["curve"], color="#d1603d", lw=2.5, label="スプラインで当てはめた平均")
ax.set_xlabel("市区町村外へ通勤・通学する人の割合（%、2020年）"); ax.set_ylabel("合計特殊出生率（2018〜22年）")
ax.set_title(f"外へ通勤する人が多い町ほど、出生率は低く見える（{r['n']:,}市区町村）", loc="left", fontsize=12)
ax.legend(frameon=False, loc="upper right"); fig.tight_layout(); fig.savefig(FIG / "f81_scatter.png", dpi=160); plt.close()

# 2 バランス
bal = pd.DataFrame(r["balance_max_abs_smd"]).T
ic = pd.DataFrame(r["ipw_corr"]).T
order = bal["smd_raw"].sort_values().index
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.8), sharey=True)
yy = np.arange(len(order))
ax = axs[0]
ax.hlines(yy, bal.loc[order, "smd_adj"], bal.loc[order, "smd_raw"], color="#cccccc", lw=2)
ax.scatter(bal.loc[order, "smd_raw"], yy, color=C["naive"], zorder=3, label="調整前")
ax.scatter(bal.loc[order, "smd_adj"], yy, color=C["gps"], zorder=3, label="GPS で5ブロックに分けた後")
ax.axvline(0.1, color="#333", ls="--", lw=1); ax.set_xlim(0, 1.25); ax.text(0.115, len(order) - 0.75, "目安0.1", fontsize=9, color="#333")
ax.set_yticks(yy, [NAMES[v] for v in order]); ax.set_xlabel("標準化平均差の絶対値（3区分のうち最大）")
ax.set_title("GPS：差は縮むが、目安までは届かない", loc="left", fontsize=11); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax = axs[1]
ax.hlines(yy, ic.loc[order, "weighted"].abs(), ic.loc[order, "raw"].abs(), color="#cccccc", lw=2)
ax.scatter(ic.loc[order, "raw"].abs(), yy, color=C["naive"], zorder=3, label="重みなし")
ax.scatter(ic.loc[order, "weighted"].abs(), yy, color=C["ipw"], zorder=3, label="IPW の重み付き")
ax.axvline(0.1, color="#333", ls="--", lw=1); ax.set_xlim(0, 0.65)
ax.set_xlabel("処置との相関の絶対値"); ax.set_title("IPW：相関は半分以下に、それでも残る", loc="left", fontsize=11)
ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.suptitle("条件をそろえられたか（未婚者の割合はモデルに入れていない参考の変数）", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f81_balance.png", dpi=160); plt.close()

# 3 用量反応曲線
fig, ax = plt.subplots(figsize=(8, 5.2))
for k in ["naive", "ols", "ipw", "gps"]:
    c = r["curves"][k]
    ax.fill_between(g, c["lo"], c["hi"], color=C[k], alpha=0.12, lw=0)
    ax.plot(g, c["curve"], color=C[k], lw=2.3, label=f"{LAB[k]}　{LO}%→{HI}%：{c['diff']:+.3f}")
ax.axvspan(LO, HI, color="#f3f3f3", zorder=0)
ax.set_xlabel("市区町村外へ通勤・通学する人の割合（%）"); ax.set_ylabel("その割合のときの平均の出生率")
ax.set_title("条件をそろえると下がり方は半分前後に。形は手法で変わる", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9.5, loc="lower left"); fig.tight_layout(); fig.savefig(FIG / "f81_curves.png", dpi=160); plt.close()

# 4 3区分の傾向スコア
tg = r["three_group"]; cuts = tg["cuts"]
labs = [f"少ない\n（〜{cuts[0]}%）", f"中くらい\n（{cuts[0]}〜{cuts[1]}%）", f"多い\n（{cuts[1]}%〜）"]
x = np.arange(3); wdt = 0.36
fig, ax = plt.subplots(figsize=(7.5, 4.8))
b1 = ax.bar(x - wdt/2, tg["raw_means"], wdt, color=C["naive"], label="そのままの平均")
b2 = ax.bar(x + wdt/2, tg["ipw_means"], wdt, color=C["ipw"], label="3区分の傾向スコアで重み付け")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.004, f"{b.get_height():.3f}", ha="center", fontsize=9)
ax.set_ylim(1.30, 1.50); ax.set_xticks(x, labs); ax.set_ylabel("合計特殊出生率")
ax.set_title(f"3区分で比べても、差は {tg['raw_top_minus_bottom']:+.3f} → {tg['ipw_top_minus_bottom']:+.3f} に縮む", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9); fig.tight_layout(); fig.savefig(FIG / "f81_three.png", dpi=160); plt.close()

# 5 頑健性
rb = pd.DataFrame(r["robustness"])
fig, ax = plt.subplots(figsize=(8.5, 5.4))
yy = np.arange(len(rb))[::-1]
ax.errorbar(rb["gps_diff"], yy + 0.15, xerr=[rb["gps_diff"] - rb["gps_lo"], rb["gps_hi"] - rb["gps_diff"]],
            fmt="o", color=C["gps"], capsize=3, label="GPS")
m = rb["ipw_diff"].notna()
ax.errorbar(rb.loc[m, "ipw_diff"], yy[m.values] - 0.15, xerr=[(rb["ipw_diff"] - rb["ipw_lo"])[m], (rb["ipw_hi"] - rb["ipw_diff"])[m]],
            fmt="s", color=C["ipw"], capsize=3, label="IPW")
ax.axvline(0, color="#333", lw=1)
ax.set_yticks(yy, [f"{s}（{n:,}）" for s, n in zip(rb["setting"], rb["n"])])
ax.set_xlabel(f"通勤・通学で外に出る割合 {LO}%→{HI}% での出生率の差（95%区間）")
ax.set_title("ほとんどの設定でマイナス。GPS の結果モデルを3次にすると0をまたぐ", loc="left", fontsize=11.5)
ax.legend(frameon=False, loc="lower right"); fig.tight_layout(); fig.savefig(FIG / "f81_robust.png", dpi=160); plt.close()

# 6 GPS の重なり（共通サポート）
from scipy import stats
t = D[T].values; grp = pd.qcut(t, 3, labels=False)
Z = D[X].astype(float); Z = (Z - Z.mean()) / Z.std()
Z = sm.add_constant(pd.concat([Z, pd.get_dummies(D["pref"], prefix="p", drop_first=True).astype(float)], axis=1)).values
mo = sm.OLS(t, Z).fit(); mu = Z @ mo.params; s = np.sqrt(mo.scale)
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8), sharey=False)
names = ["少ない", "中くらい", "多い"]
for gi in range(3):
    rg = stats.norm.pdf(np.median(t[grp == gi]), mu, s)
    ax = axs[gi]; bins = np.linspace(0, rg.max(), 30)
    ax.hist(rg[grp == gi], bins=bins, alpha=0.6, color=C["gps"], label="その区分の町")
    ax.hist(rg[grp != gi], bins=bins, alpha=0.5, color=C["naive"], label="ほかの区分の町")
    ax.set_title(f"「{names[gi]}」の中央値での GPS", fontsize=10.5, loc="left"); ax.set_xlabel("GPS")
    if gi == 0: ax.legend(frameon=False, fontsize=8.5)
fig.suptitle(f"通勤の多い町と少ない町は、条件の分布があまり重ならない（共通部分は {r['n_common_support']:,}/{r['n']:,}）", x=0.01, ha="left", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f81_support.png", dpi=160); plt.close()
print("ok")
