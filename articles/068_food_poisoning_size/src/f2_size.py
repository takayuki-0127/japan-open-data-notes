"""食中毒1件あたりの患者数：裾の重い分布、上位の事件の占める割合、病因物質・原因施設別の大きさ（負の二項回帰）"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load()
x = x[x.patients >= 1].copy()
P = x.patients.values
s = np.sort(P)[::-1]; cum = s.cumsum() / s.sum()
top = {f"上位{q}%": cum[int(np.ceil(len(s) * q / 100)) - 1] * 100 for q in (1, 5, 10)}
summ = {"事件数": len(s), "患者総数": int(s.sum()), "中央値": np.median(P), "平均": P.mean(), "患者1人の事件の割合%": (P == 1).mean() * 100,
        "100人以上の事件数": int((P >= 100).sum()), "500人以上の事件数": int((P >= 500).sum()), "最大": int(P.max()), **top}
pd.Series(summ).to_csv(RES / "f2_summary.csv", encoding="utf-8-sig"); print(pd.Series(summ).round(2))

# 期間別の上位1%の占める割合
pe = []
for a, b in [(2000, 2008), (2009, 2016), (2017, 2025)]:
    q = np.sort(x[(x.year >= a) & (x.year <= b)].patients.values)[::-1]; c = q.cumsum() / q.sum()
    pe.append({"期間": f"{a}-{b}", "事件数": len(q), "上位1%の割合": c[int(np.ceil(len(q) * .01)) - 1] * 100, "上位5%の割合": c[int(np.ceil(len(q) * .05)) - 1] * 100})
pd.DataFrame(pe).to_csv(RES / "f2_top_share_by_period.csv", index=False, encoding="utf-8-sig"); print(pd.DataFrame(pe).round(1))

# 裾の形：患者数≥xmin の部分に、べき分布と（xminで切った）対数正規分布を最尤推定で当てて比べる（連続近似、Vuong検定）
from scipy import stats, optimize
tail = []
for xmin in (20, 50, 100):
    t = P[P >= xmin].astype(float); lt = np.log(t); n_ = len(t)
    a = 1 + n_ / np.log(t / xmin).sum(); se = (a - 1) / np.sqrt(n_)
    l_pl = np.log((a - 1) / xmin) - a * np.log(t / xmin)
    def nll(th):
        mu, ls = th; sg = np.exp(ls)
        return -((stats.norm.logpdf(lt, mu, sg) - lt) - stats.norm.logsf((np.log(xmin) - mu) / sg)).sum()
    r = optimize.minimize(nll, [lt.mean(), np.log(lt.std())], method="Nelder-Mead", options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-6})
    mu, sg = r.x[0], np.exp(r.x[1])
    l_ln = (stats.norm.logpdf(lt, mu, sg) - lt) - stats.norm.logsf((np.log(xmin) - mu) / sg)
    dlt = l_pl - l_ln; R_ = dlt.sum(); z = R_ / (np.sqrt(n_) * dlt.std()); pv = 2 * stats.norm.sf(abs(z))
    tail.append({"xmin": xmin, "n": n_, "alpha": a, "se": se, "loglik_べき": l_pl.sum(), "loglik_対数正規": l_ln.sum(), "LR(べき−対数正規)": R_, "Vuong_z": z, "p": pv})
TL = pd.DataFrame(tail); TL.to_csv(RES / "f2_tail_fit.csv", index=False, encoding="utf-8-sig"); print(TL.round(2))

# 群別・施設別の中央値など
def agg(g):
    return pd.Series({"事件数": len(g), "中央値": g.patients.median(), "平均": g.patients.mean(), "90%点": g.patients.quantile(.9), "最大": g.patients.max(), "患者数計": g.patients.sum()})
G = x.groupby("group").apply(agg).reindex(GROUPS); G.to_csv(RES / "f2_by_group.csv", encoding="utf-8-sig"); print(G.round(1))
F = x.groupby("fac").apply(agg).sort_values("中央値", ascending=False); F.to_csv(RES / "f2_by_facility.csv", encoding="utf-8-sig"); print(F.round(1))

# 負の二項回帰：患者数 ~ 病因物質 + 原因施設 + 年代
d = x.copy(); d["period"] = pd.cut(d.year, [1999, 2008, 2016, 2025], labels=["2000-08", "2009-16", "2017-25"]).astype(str)
X = pd.concat([pd.get_dummies(d.group, prefix="病因", dtype=float).drop(columns="病因_カンピロバクター"),
               pd.get_dummies(d.fac, prefix="施設", dtype=float).drop(columns="施設_飲食店"),
               pd.get_dummies(d.period, prefix="期間", dtype=float).drop(columns="期間_2000-08")], axis=1)
m = sm.NegativeBinomial(d.patients.values, sm.add_constant(X)).fit(disp=0, maxiter=200)
ci = m.conf_int()
R = pd.DataFrame({"var": m.params.index, "ratio": np.exp(m.params), "lo": np.exp(ci[0]), "hi": np.exp(ci[1]), "p": m.pvalues}).reset_index(drop=True)
R.to_csv(RES / "f2_nb_ratio.csv", index=False, encoding="utf-8-sig"); print(R.round(3).to_string()); print("N", len(d))

# 図1：CCDF（両対数）
fig, ax = plt.subplots(figsize=(7.6, 4.6))
for g, col in [("全体", INK), ("ノロウイルス", GCOL["ノロウイルス"]), ("ウェルシュ菌", GCOL["ウェルシュ菌"]), ("カンピロバクター", GCOL["カンピロバクター"]), ("アニサキス", GCOL["アニサキス"])]:
    v = np.sort(P if g == "全体" else x[x.group == g].patients.values)
    u = np.unique(v); ccdf = 1 - np.searchsorted(v, u, side="left") / len(v)
    ax.step(u, ccdf, where="post", color=col, lw=2.2 if g == "全体" else 1.5, label=f"{g}（{len(v):,}件）")
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("1件あたりの患者数（人、対数目盛）"); ax.set_ylabel("その人数以上の事件の割合（対数目盛）")
ax.legend(frameon=False, fontsize=9); ax.set_title("患者数がその値以上になる事件の割合（2000〜2025年）", loc="left", fontsize=12)
note(ax, SOURCE, -0.15); fig.savefig(FIG / "f2_ccdf.png"); plt.close(fig)

# 図2：上位の事件が占める割合（ローレンツ風）
fig, ax = plt.subplots(figsize=(7.2, 4.2))
xs = np.arange(1, len(s) + 1) / len(s) * 100
ax.plot(xs, cum * 100, color=BLUE, lw=2.2)
for q in (1, 5, 10):
    v = top[f"上位{q}%"]; ax.plot([q, q], [0, v], ":", color=GRAY); ax.plot([0, q], [v, v], ":", color=GRAY)
    ax.text(q + 1, v - 5, f"上位{q}%の事件で\n患者の{v:.0f}%", fontsize=9, color=INK)
ax.set_xlim(0, 50); ax.set_ylim(0, 100); ax.set_xlabel("患者数の多い順に並べた事件の割合（%）"); ax.set_ylabel("患者数の累積割合（%）")
ax.set_title("ひと握りの大きな事件が患者の多くを占める", loc="left")
note(ax, SOURCE, -0.16); fig.savefig(FIG / "f2_topshare.png"); plt.close(fig)

# 図3：施設別・病因物質別の比（NB回帰）
sel = R[R["var"].str.startswith(("病因", "施設"))].copy()
sel["label"] = sel["var"].str.replace("病因_", "病因：").str.replace("施設_", "施設：")
sel = sel.sort_values("ratio")
fig, ax = plt.subplots(figsize=(7.8, 6.4))
yy = np.arange(len(sel))
cols = [BLUE if v.startswith("病因") else ORANGE for v in sel["var"]]
ax.errorbar(sel.ratio, yy, xerr=[sel.ratio - sel.lo, sel.hi - sel.ratio], fmt="none", ecolor=GRAY, capsize=2)
ax.scatter(sel.ratio, yy, c=cols, zorder=3)
ax.axvline(1, color=INK, lw=.7); ax.set_xscale("log"); ax.set_xticks([0.1, 0.3, 1, 3, 10]); ax.set_xticklabels(["0.1", "0.3", "1", "3", "10"]); ax.minorticks_off()
ax.set_yticks(yy); ax.set_yticklabels(sel.label, fontsize=9)
ax.set_xlabel("1件あたり患者数の比（対数目盛、基準：カンピロバクター・飲食店）")
ax.set_title("何が原因で、どこで起きると大きくなるか（負の二項回帰）", loc="left", fontsize=12)
note(ax, SOURCE + "\n青＝病因物質、橙＝原因施設。期間（2000-08/09-16/17-25年）もそろえた。ひげは95%信頼区間", -0.1)
fig.savefig(FIG / "f2_nb.png"); plt.close(fig)
