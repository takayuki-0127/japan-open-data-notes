"""04 図と集計表（figures/、results/）"""
import json
import numpy as np, pandas as pd, arviz as az
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from common import FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, SOURCE, TILE
from importlib import import_module
M = import_module("02_model")
S = json.load(open(RES / "fit_summary.json"))


def note(fig, y=-0.02):
    fig.text(0.01, y, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")


d, prefs, munis = M.prep()
idn = az.from_netcdf(RES / "idata_null.nc")
p = idn.posterior
mu = p["mu"].values.ravel(); A = p["a"].values.reshape(-1, len(prefs)); Bm = p["b"].values.reshape(-1, len(munis))
g = np.concatenate([[0.0], p["g_raw"].mean(("chain", "draw")).values])

# ---- 図1 分散の分解（国保・後期） ----
fig, ax = plt.subplots(figsize=(8, 3.4))
rows = [("市町村国保", S["null"]), ("後期高齢者医療", S["kouki"])]
med = d["pop2020"].median()
for k, (lab, r) in enumerate(rows):
    va, vb = r["sigma_pref"] ** 2, r["sigma_muni"] ** 2
    tot = va + vb
    ax.barh(k, va / tot * 100, color=BLUE); ax.barh(k, vb / tot * 100, left=va / tot * 100, color=ORANGE)
    ax.text(va / tot * 50, k, f"県の差\n{va/tot*100:.0f}%", ha="center", va="center", color="white", fontsize=10)
    ax.text(va / tot * 100 + vb / tot * 50, k, f"同じ県の中の\n市区町村の差 {vb/tot*100:.0f}%", ha="center", va="center", color="white", fontsize=10)
    ax.text(101, k, f"県のSD {r['sigma_pref']:.1f}%\n市区町村のSD {r['sigma_muni']:.1f}%", va="center", fontsize=9, color=INK)
ax.set_yticks([0, 1]); ax.set_yticklabels([r[0] for r in rows]); ax.set_xlim(0, 100); ax.invert_yaxis()
ax.set_xlabel("毎年続く医療費の差（年齢調整後）のばらつきに占める割合（%）")
ax.set_title("医療費の地域差は、県の差と県の中の差がほぼ6対4（市町村国保）")
note(fig, -0.06); fig.savefig(FIG / "f05_variance_share.png"); plt.close(fig)

# ---- 図2 部分プーリング ----
d["est"] = (mu[:, None] + A[:, d["pref_i"].values] + Bm[:, d["muni_i"].values]).mean(0) + g[d["year_i"].values]
mm = d.groupby("muni_i").agg(raw=("y", "mean"), est=("est", "mean"), pop=("pop2020", "first"), pref_i=("pref_i", "first")).reset_index()
pref_mean = (mu[:, None] + A).mean(0) + g.mean()
mm["pref_est"] = pref_mean[mm["pref_i"]]
mm["shrink"] = 1 - (mm["est"] - mm["pref_est"]) / (mm["raw"] - mm["pref_est"])
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
ax = axes[0]
sc = ax.scatter(mm["raw"], mm["est"], c=np.log10(mm["pop"]), cmap="viridis_r", s=9, alpha=.8)
lim = [mm["raw"].min() - 2, mm["raw"].max() + 2]
ax.plot(lim, lim, color=GRAY, lw=1, ls="--"); ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("そのままの値（3年平均、全国＝0、%）"); ax.set_ylabel("階層モデルの推定値（%）")
cb = fig.colorbar(sc, ax=ax); cb.set_label("人口（log10）")
ax.set_title("小さい町ほど、推定値は県の平均へ引き寄せられる", fontsize=11.5)
ax = axes[1]
bins = [0, 3000, 10000, 30000, 100000, 1e7]; labs = ["3千人未満", "3千〜1万", "1万〜3万", "3万〜10万", "10万人以上"]
mm["size"] = pd.cut(mm["pop"], bins, labels=labs)
ok = (mm["raw"] - mm["pref_est"]).abs() > 1
sh = mm[ok].groupby("size", observed=True)["shrink"].median() * 100
ax.bar(range(len(sh)), sh.values, color=[ORANGE if v > 20 else BLUE for v in sh.values])
for k, v in enumerate(sh.values): ax.text(k, v + 1, f"{v:.0f}%", ha="center")
ax.set_xticks(range(len(sh))); ax.set_xticklabels(sh.index, fontsize=9.5)
ax.set_ylabel("県の平均との差が縮んだ割合（中央値、%）"); ax.set_xlabel("市区町村の人口")
ax.set_title("縮み方は人口の大きさで決まる", fontsize=11.5)
note(fig, -0.03); fig.tight_layout(); fig.savefig(FIG / "f05_partial_pooling.png"); plt.close(fig)
sh.to_csv(RES / "shrink_by_size.csv")
mm.to_csv(RES / "muni_estimates_kokuho.csv", index=False)

# ---- 図3 共変量の効果（事後分布） ----
bt = S["beta"]
fig, ax = plt.subplots(figsize=(8, 3.6))
names = list(bt.keys())
for k, nm in enumerate(names):
    m_, lo, hi = bt[nm]
    c = BLUE if lo > 0 or hi < 0 else GRAY
    ax.plot([lo, hi], [k, k], color=c, lw=3); ax.plot(m_, k, "o", color=c, ms=8)
    ax.text(hi + 0.15, k, f"{m_:+.1f}（{lo:+.1f}〜{hi:+.1f}）", va="center", fontsize=9)
ax.axvline(0, color=INK, lw=.8); ax.set_yticks(range(len(names))); ax.set_yticklabels(names); ax.invert_yaxis()
ax.set_xlabel("1標準偏差あたりの医療費の高さの差（%ポイント、95%区間）")
ax.set_title("県の病床数が多いほど、年齢をそろえた医療費は高い")
xl = ax.get_xlim(); ax.set_xlim(xl[0], xl[1] + 2.5)
note(fig, -0.05); fig.savefig(FIG / "f05_covariates.png"); plt.close(fig)

# ---- 図4 県の差（タイル地図） ----
pe = pd.DataFrame({"pref": prefs, "a": A.mean(0), "lo": np.quantile(A, .025, 0), "hi": np.quantile(A, .975, 0)})
pe.to_csv(RES / "pref_effects_kokuho.csv", index=False)
fig, ax = plt.subplots(figsize=(7.5, 6.2))
vmax = np.abs(pe["a"]).max()
cmap = plt.get_cmap("RdBu_r")
for _, r in pe.iterrows():
    x, y = TILE[r["pref"]]
    col = cmap(0.5 + r["a"] / vmax / 2)
    ax.add_patch(Rectangle((x, -y), .95, .95, color=col))
    ax.text(x + .475, -y + .6, r["pref"].replace("県", "").replace("府", "").replace("東京都", "東京"), ha="center", va="center", fontsize=7.5)
    ax.text(x + .475, -y + .28, f"{r['a']:+.0f}", ha="center", va="center", fontsize=8, color=INK)
ax.set_xlim(-.2, 13.2); ax.set_ylim(-9.2, 1.1); ax.axis("off")
ax.set_title("県の差（市町村国保、全国の平均＝0、%）：西日本で高く、東日本で低い")
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(-vmax, vmax)); cb = fig.colorbar(sm, ax=ax, shrink=.6); cb.set_label("%")
note(fig, 0.02); fig.savefig(FIG / "f05_pref_map.png"); plt.close(fig)

# ---- 図5 入院・入院外・歯科 ----
comp = [("計", S["null"]), ("入院", S["null_idx_in"]), ("入院外", S["null_idx_out"]), ("歯科", S["null_idx_dental"])]
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
ax = axes[0]
for k, (lab, r) in enumerate(comp):
    ax.errorbar(r["pref_share"] * 100, k, xerr=[[r["pref_share"] * 100 - r["pref_share_lo"] * 100], [r["pref_share_hi"] * 100 - r["pref_share"] * 100]], fmt="o", color=BLUE, ms=8, capsize=4)
    ax.text(r["pref_share_hi"] * 100 + 2, k, f"{r['pref_share']*100:.0f}%", va="center")
ax.set_yticks(range(4)); ax.set_yticklabels([c[0] for c in comp]); ax.invert_yaxis(); ax.set_xlim(0, 100)
ax.set_xlabel("ばらつきのうち「県の差」の割合（%、95%区間）"); ax.set_title("入院は県で、入院外は市区町村で差がつく", fontsize=11.5)
ax = axes[1]
w = .38
for k, (lab, r) in enumerate(comp):
    ax.bar(k - w / 2, r["sigma_pref"], w, color=BLUE, label="県の差（SD）" if k == 0 else None)
    ax.bar(k + w / 2, r["sigma_muni"], w, color=ORANGE, label="県の中の市区町村の差（SD）" if k == 0 else None)
ax.set_xticks(range(4)); ax.set_xticklabels([c[0] for c in comp]); ax.set_ylabel("標準偏差（全国＝0 の %）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("差の大きさそのもの", fontsize=11.5)
note(fig, -0.04); fig.tight_layout(); fig.savefig(FIG / "f05_by_type.png"); plt.close(fig)

# ---- 図6 事後予測チェック ----
yrep = np.load(RES / "ppc_null_sub.npy")
d["size"] = pd.cut(d["pop2020"], bins, labels=labs)
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
ax = axes[0]
ax.hist(d["y"], bins=60, density=True, color=LIGHT, label="実際の値")
for s in range(0, len(yrep), max(1, len(yrep) // 20)):
    h, e = np.histogram(yrep[s], bins=60, range=(d["y"].min(), d["y"].max()), density=True)
    ax.plot((e[1:] + e[:-1]) / 2, h, color=BLUE, alpha=.25, lw=1)
ax.plot([], [], color=BLUE, label="モデルから作ったデータ（20組）"); ax.legend(frameon=False, fontsize=9)
ax.set_xlabel("医療費の高さ（全国＝0、%）"); ax.set_title("分布の形は再現できている", fontsize=11.5)
ax = axes[1]
obs_sd, rep_lo, rep_hi = [], [], []
for lab in labs:
    msk = (d["size"] == lab).values
    dm = d[msk]
    o = dm.groupby("muni_i")["y"].std().mean()
    reps = []
    for s in range(len(yrep)):
        tmp = pd.Series(yrep[s][msk]).groupby(dm["muni_i"].values).std().mean(); reps.append(tmp)
    obs_sd.append(o); rep_lo.append(np.quantile(reps, .05)); rep_hi.append(np.quantile(reps, .95))
x = np.arange(len(labs))
ax.fill_between(x, rep_lo, rep_hi, color=LIGHT, label="モデル（90%の範囲）"); ax.plot(x, obs_sd, "o-", color=ORANGE, label="実際")
ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9); ax.set_ylabel("同じ市区町村の3年のぶれ（SD、%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("ぶれの傾向は合うが、3千人未満ではモデルのぶれが大きすぎる", fontsize=11)
note(fig, -0.04); fig.tight_layout(); fig.savefig(FIG / "f05_ppc.png"); plt.close(fig)
pd.DataFrame({"size": labs, "obs_sd": obs_sd, "rep_lo": rep_lo, "rep_hi": rep_hi}).to_csv(RES / "ppc_sd_by_size.csv", index=False)

# ---- 頑健性の表 ----
rob = []
for k, lab in [("null", "基本（国保・3年・HalfNormal・人口でぶれを調整）"), ("prior_halfcauchy", "事前分布 HalfCauchy"), ("prior_exponential", "事前分布 Exponential"),
               ("year2023_only", "2023年度だけ"), ("year2021_only", "2021年度だけ"), ("homoscedastic", "ぶれを人口で調整しない"), ("kouki", "後期高齢者医療"),
               ("full", "共変量つき（県の差の残り）")]:
    r = S[k]; rob.append({"モデル": lab, "県の割合": round(r["pref_share"] * 100, 1), "下限": round(r["pref_share_lo"] * 100, 1), "上限": round(r["pref_share_hi"] * 100, 1),
                          "県のSD": round(r["sigma_pref"], 2), "市区町村のSD": round(r["sigma_muni"], 2), "ぶれのSD": round(r["sigma_noise"], 2), "R-hat最大": round(r["rhat_max"], 3)})
rob.append({"モデル": "頻度論の混合モデル（REML）", "県の割合": round(S["mixedlm"]["pref_share"] * 100, 1), "県のSD": round(S["mixedlm"]["var_pref"] ** .5, 2), "市区町村のSD": round(S["mixedlm"]["var_muni"] ** .5, 2)})
pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False)
print(pd.DataFrame(rob).to_string(index=False))
print(sh); print(pe.sort_values("a").head(3)); print(pe.sort_values("a").tail(3))
