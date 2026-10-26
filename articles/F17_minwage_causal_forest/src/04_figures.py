"""図を作る"""
import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import DATA, RES, X_COLS, X_JA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

d = pd.read_csv(DATA / "f17_panel_with_tau.csv")
mj = json.load(open(RES / "main.json"))
pref = pd.read_csv(RES / "pref_effects.csv")

# 1 効果の分布（県×年）と県ごとの平均（95%区間）
fig, ax = plt.subplots(1, 2, figsize=(12, 6.2), gridspec_kw={"width_ratios": [1, 1.25]})
ax[0].hist(pref.tau, bins=14, color=LIGHT, edgecolor="white")
ax[0].axvline(mj["ate"], color=BLUE, lw=2); ax[0].axvline(0, color=GRAY, lw=1, ls="--")
ax[0].axvspan(mj["ate_lo"], mj["ate_hi"], color=BLUE, alpha=0.08)
ax[0].set_title("県ごとの効果の推定値（47県）")
ax[0].set_xlabel("最低賃金が平均時給の1%分上がったときの\n就業率の変化（%pt）"); ax[0].set_ylabel("県の数")
ax[0].text(mj["ate"], ax[0].get_ylim()[1] * 0.92, f" 平均 {mj['ate']:+.2f}\n（{mj['ate_lo']:+.2f}〜{mj['ate_hi']:+.2f}）", color=BLUE, fontsize=10)
p = pref.sort_values("tau").reset_index(drop=True)
cols = [ORANGE if e else GRAY for e in p.ci_excl0]
ax[1].hlines(p.index, p.tau_lo, p.tau_hi, color=cols, lw=1.4); ax[1].scatter(p.tau, p.index, color=cols, s=14, zorder=3)
ax[1].axvline(0, color=INK, lw=0.8)
ax[1].set_yticks(p.index); ax[1].set_yticklabels(p.pref, fontsize=7)
ax[1].set_title("県ごとの平均（95%区間）")
ax[1].set_xlabel("就業率の変化（%pt）")
ax[1].text(0.98, 0.02, f"区間が0をまたがない県：{int(p.ci_excl0.sum())}／47\n（偶然でも5%＝約2県は出る）", transform=ax[1].transAxes, ha="right", fontsize=9, color=ORANGE)
fig.suptitle("因果フォレストの推定：効果の平均はほぼ0、県ごとの差も区間の中", x=0.01, ha="left", fontsize=14)
fig.tight_layout(); save(fig, "f1_effects.png")

# 2 効果と bite（最低賃金÷平均時給）、高齢化の関係
fig, ax = plt.subplots(1, 2, figsize=(12, 4.8))
pf = pref.merge(pd.read_csv(DATA / "f17_pref_features.csv"), on="code", suffixes=("", "_f"))
for a, col, lab in [(ax[0], "bite", "最低賃金÷平均時給（2015年）"), (ax[1], "age65", "65歳以上の割合（2015年、%）")]:
    a.errorbar(pf[col], pf.tau, yerr=[pf.tau - pf.tau_lo, pf.tau_hi - pf.tau], fmt="o", color=BLUE, ecolor=LIGHT, ms=4)
    a.axhline(0, color=GRAY, lw=0.8)
    r = np.corrcoef(pf[col], pf.tau)[0, 1]
    a.set_xlabel(lab); a.set_ylabel("県の平均効果（%pt）"); a.set_title(f"相関 {r:+.2f}")
    for _, rw in pf.iterrows():
        if rw.pref in ["東京", "沖縄", "青森", "秋田", "山形", "徳島", "神奈川", "島根"]:
            a.annotate(rw.pref, (rw[col], rw.tau), fontsize=8, xytext=(3, 3), textcoords="offset points")
if "bite_f" in pf: pass
fig.suptitle("「最低賃金が平均時給に近い県」ほど効果が大きい、という形は出なかった", x=0.01, ha="left", fontsize=14)
fig.tight_layout(); save(fig, "f2_bite_age.png")

# 3 特徴量の重要度
imp = pd.read_csv(RES / "feature_importance.csv", index_col=0)["importance"].sort_values()
fig, ax = plt.subplots(figsize=(9, 5.2))
ax.barh([X_JA[i] for i in imp.index], imp.values, color=[BLUE if i == imp.index[-1] else LIGHT for i in imp.index])
ax.set_xlabel("分割に使われた重要度（合計1）")
ax.set_title("森が「分けるのに使った」特徴。ただしプラセボでも同じ1位になった", loc="left")
fig.tight_layout(); save(fig, "f3_importance.png")

# 4 地図（タイル）
TILE = {"北海道": (11, 0), "青森": (10, 2), "秋田": (9, 3), "岩手": (10, 3), "山形": (9, 4), "宮城": (10, 4), "福島": (10, 5),
        "新潟": (8, 5), "群馬": (8, 6), "栃木": (9, 6), "茨城": (10, 6), "長野": (7, 6), "埼玉": (8, 7), "千葉": (10, 7), "東京": (9, 7),
        "神奈川": (9, 8), "山梨": (8, 8), "静岡": (7, 8), "富山": (7, 5), "石川": (6, 5), "福井": (6, 6), "岐阜": (6, 7), "愛知": (6, 8),
        "三重": (5, 8), "滋賀": (5, 7), "京都": (4, 7), "大阪": (4, 8), "兵庫": (3, 7), "奈良": (5, 9), "和歌山": (4, 9),
        "鳥取": (2, 6), "島根": (1, 6), "岡山": (2, 7), "広島": (1, 7), "山口": (0, 7), "香川": (2, 9), "徳島": (3, 9), "愛媛": (1, 9),
        "高知": (2, 10), "福岡": (0, 9), "佐賀": (-1, 9), "長崎": (-2, 9), "大分": (0, 10), "熊本": (-1, 10), "宮崎": (0, 11),
        "鹿児島": (-1, 11), "沖縄": (-2, 12)}
fig, ax = plt.subplots(figsize=(8.5, 8))
norm = TwoSlopeNorm(vmin=-0.31, vcenter=0, vmax=0.31); cmap = plt.get_cmap("RdBu")
for _, rw in pref.iterrows():
    x, y = TILE[rw.pref]
    ax.add_patch(plt.Rectangle((x, -y), 0.95, 0.95, color=cmap(norm(rw.tau)), ec="white" if not rw.ci_excl0 else INK, lw=1.5))
    ax.text(x + 0.47, -y + 0.6, rw.pref, ha="center", fontsize=7.5)
    ax.text(x + 0.47, -y + 0.25, f"{rw.tau:+.2f}", ha="center", fontsize=7)
ax.set_xlim(-2.5, 12.2); ax.set_ylim(-12.2, 1.2); ax.set_aspect("equal"); ax.axis("off")
sm_ = plt.cm.ScalarMappable(norm=norm, cmap=cmap); cb = fig.colorbar(sm_, ax=ax, shrink=0.5); cb.set_label("県の平均効果（%pt）")
ax.set_title("県ごとの平均効果（赤＝就業率が下がる向き、黒枠＝区間が0をまたがない）", loc="left", fontsize=11)
save(fig, "f4_map.png")

# 5 キャリブレーション（GATES）と、上位・下位の比較
g = pd.read_csv(RES / "gates.csv")
comp = pd.read_csv(RES / "high_low_compare.csv", index_col=0)
fig, ax = plt.subplots(1, 2, figsize=(12.5, 5), gridspec_kw={"width_ratios": [1, 1.2]})
ax[0].errorbar(g.q, g.actual, yerr=[g.actual - g.lo, g.hi - g.actual], fmt="o", color=ORANGE, capsize=4, label="実際の差（残差から）")
ax[0].plot(g.q, g.pred_mean, "s--", color=BLUE, label="森が予測した効果")
ax[0].axhline(0, color=GRAY, lw=0.8)
ax[0].set_xticks([1, 2, 3, 4]); ax[0].set_xticklabels(["下がりやすい\n25%", "", "", "下がりにくい\n25%"])
ax[0].set_xlabel("予測した効果の大きさで4つに分けた群（県を外して予測）"); ax[0].set_ylabel("就業率の変化（%pt）")
ax[0].set_title(f"予測の順に並ばない（BLP p={mj['blp_het_p']:.2f}）", loc="left"); ax[0].legend(fontsize=9)
cols = ["bite", "age65", "logpop15", "sh_manu", "sh_food", "unemp15"]
hi_c, lo_c = comp.columns[0], comp.columns[1]
z = (comp.loc[cols, hi_c] - comp.loc[cols, lo_c]) / pd.read_csv(DATA / "f17_pref_features.csv")[cols].std().values
ax[1].barh([X_JA[c] for c in cols][::-1], z.values[::-1], color=[BLUE if v > 0 else ORANGE for v in z.values[::-1]])
ax[1].axvline(0, color=INK, lw=0.8)
ax[1].set_xlabel("「下がりにくい側」−「下がりやすい側」（県の標準偏差で割った差）")
ax[1].set_title("森の予測で就業率が下がりにくい側と下がりやすい側の違い", loc="left", fontsize=12)
fig.tight_layout(); save(fig, "f5_calibration.png")
print("ok")

# 6 頑健性：平均効果と、異質性の検定（同じデータ vs 県を外す）
r = pd.read_csv(RES / "robustness.csv")
fig, ax = plt.subplots(1, 2, figsize=(13, 6), gridspec_kw={"width_ratios": [1.4, 1]})
y = np.arange(len(r))[::-1]
c = [ORANGE if "プラセボ" in s else BLUE for s in r["設定"]]
ax[0].hlines(y, r["下限"], r["上限"], color=c, lw=1.6); ax[0].scatter(r["平均効果"], y, color=c, zorder=3, s=18)
ax[0].axvline(0, color=INK, lw=0.8); ax[0].set_yticks(y); ax[0].set_yticklabels(r["設定"], fontsize=8.5)
ax[0].set_xlabel("平均効果（%pt、95%区間）"); ax[0].set_title("平均効果：どの設定でも区間は0をまたぐ", loc="left", fontsize=12)
hv = r.dropna(subset=["BLP p値（県を外して予測）"])
yy = np.arange(len(hv))[::-1]
ax[1].barh(yy + 0.2, -np.log10(hv["BLP p値（同じデータで予測）"].clip(lower=1e-12)), height=0.38, color=GRAY, label="同じデータで予測した効果")
ax[1].barh(yy - 0.2, -np.log10(hv["BLP p値（県を外して予測）"]), height=0.38, color=BLUE, label="県を外して予測した効果")
ax[1].axvline(-np.log10(0.05), color=ORANGE, ls="--", lw=1); ax[1].text(-np.log10(0.05) + 0.1, yy.max() + 0.5, "p=0.05", color=ORANGE, fontsize=9)
ax[1].set_yticks(yy); ax[1].set_yticklabels([s.replace("（2010〜25年、2020〜22年を除く）", "") for s in hv["設定"]], fontsize=8.5)
ax[1].set_xlabel("異質性の検定（BLP）の −log10(p)。右ほど「差がある」")
ax[1].set_title("同じデータで確かめると、プラセボでも「差あり」", loc="left", fontsize=12); ax[1].legend(fontsize=8.5, loc="lower right")
fig.tight_layout(); save(fig, "f6_robustness.png")
print("ok6")
