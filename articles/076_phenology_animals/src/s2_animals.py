"""動物（初鳴・初見）：観測できた地点数の推移、観測期間中の「記録なし」の割合、日付の変化（1953〜2020年）"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from common import *

d = load()
SP = {"018": "うぐいすの初鳴", "017": "ひばりの初鳴", "019": "つばめの初見", "020": "もんしろちょうの初見", "022": "とのさまがえるの初見",
      "023": "しおからとんぼの初見", "024": "ほたるの初見", "025": "あぶらぜみの初鳴", "026": "ひぐらしの初鳴", "113": "にいにいぜみの初鳴",
      "111": "つくつくほうしの初鳴", "027": "もずの初鳴"}
x = d[d.code.isin(SP) & d.year.between(1953, 2020)].copy()

# 地点ごとの「観測期間」＝初めて記録がある年〜最後に記録がある年。その中で記録がない年＝「記録なし」
rows = []
for (c, s), g in x.groupby(["code", "st"]):
    ob = g[g.obs == 1]
    if len(ob) < 5: continue
    y0, y1 = ob.year.min(), ob.year.max()
    w = g[g.year.between(y0, y1)]
    for _, r in w.iterrows():
        rows.append((c, s, r.year, r.obs, y0, y1))
W = pd.DataFrame(rows, columns=["code", "st", "year", "obs", "y0", "y1"])
W["dec"] = (W.year // 10) * 10
W = W[W.year.between(1960, 2019)]
gap = W.groupby(["code", "dec"]).obs.apply(lambda s: (1 - s.mean()) * 100).unstack("dec")
gap.index = [SP[c] for c in gap.index]; gap.to_csv(RES / "s2_noobs_share_by_decade.csv", encoding="utf-8-sig")
allgap = W.groupby("dec").obs.apply(lambda s: (1 - s.mean()) * 100); print(gap.round(1)); print(allgap.round(1))

# 年ごとの「記録があった地点数」
n = x[x.obs == 1].groupby(["code", "year"]).st.nunique().unstack(0).reindex(range(1953, 2021)).fillna(0)
n.columns = [SP[c] for c in n.columns]; n.to_csv(RES / "s2_nstations_by_year.csv", encoding="utf-8-sig")
peak = n.loc[1971:1990].mean(); late = n.loc[2011:2020].mean()
# 比べるための基準：同じ期間の「さくらの開花」の記録地点数（地点の廃止・無人化の影響の目安）
sk = d[(d.code == "004") & (d.obs == 1)].groupby("year").st.nunique()
base = sk.loc[2011:2020].mean() / sk.loc[1971:1990].mean() - 1
cmp_ = pd.DataFrame({"1971-1990平均": peak, "2011-2020平均": late, "変化率%": (late / peak - 1) * 100}).sort_values("変化率%")
cmp_.loc["（参考）さくらの開花"] = [sk.loc[1971:1990].mean(), sk.loc[2011:2020].mean(), base * 100]
cmp_.to_csv(RES / "s2_nstations_change.csv", encoding="utf-8-sig"); print(cmp_.round(1))

# 日付のトレンド（地点固定効果、30年以上記録がある地点、1953〜2020年）
tr = []
for c, nm in SP.items():
    g = x[(x.code == c) & (x.obs == 1)]
    keep = g.groupby("st").size(); g = g[g.st.isin(keep[keep >= 30].index)]
    if g.st.nunique() < 5: continue
    m = smf.ols("doy ~ year + C(st)", g).fit(cov_type="cluster", cov_kwds={"groups": g.year})
    ci = m.conf_int().loc["year"]
    tr.append({"code": c, "name": nm, "n_stations": g.st.nunique(), "n_obs": len(g), "trend_dec": m.params["year"] * 10, "lo": ci[0] * 10, "hi": ci[1] * 10})
TR = pd.DataFrame(tr).sort_values("trend_dec"); TR.to_csv(RES / "s2_date_trends.csv", index=False, encoding="utf-8-sig"); print(TR.round(2).to_string())

# 図1：記録があった地点数
fig, ax = plt.subplots(figsize=(8.6, 4.3))
show = ["とのさまがえるの初見", "ほたるの初見", "ひばりの初鳴", "しおからとんぼの初見", "うぐいすの初鳴", "つばめの初見", "あぶらぜみの初鳴"]
cols = [GREEN, "#d4a72c", PURPLE, BLUE, ORANGE, INK, GRAY]
for s_, c_ in zip(show, cols):
    ax.plot(n.index, n[s_].rolling(3, center=True, min_periods=1).mean(), color=c_, lw=1.8, label=f"{s_}（{cmp_.loc[s_, '変化率%']:+.0f}%）")
skr = sk.reindex(range(1953, 2021)).rolling(3, center=True, min_periods=1).mean()
ax.plot(skr.index, skr.values, color=ORANGE, lw=1.2, ls="--", label=f"（参考）さくらの開花（{base * 100:+.0f}%）")
ax.set_ylabel("記録があった地点数（3年移動平均）"); ax.set_xlim(1953, 2020); ax.set_ylim(0, None)
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower left")
ax.set_title("初鳴・初見の記録があった地点の数（かっこ内は1971〜90年平均→2011〜20年平均）", loc="left", fontsize=11)
note(ax, SOURCE, -0.13)
fig.savefig(FIG / "s2_nstations.png"); plt.close(fig)

# 図2：観測期間中の「記録なし」の割合（年代別）
fig, ax = plt.subplots(figsize=(8.6, 4.2))
order = gap[2010].sort_values().index
decs = [1960, 1980, 2000, 2010]; dc = [LIGHT, "#7fb0e6", BLUE, ORANGE]  # 1960〜2019年を10年ごとに
for j, (dd_, cc) in enumerate(zip(decs, dc)):
    ax.barh(np.arange(len(order)) + (j - 1.5) * .2, gap.loc[order, dd_], .2, color=cc, label=f"{dd_}年代")
ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=9); ax.set_xlabel("観測期間中に記録がなかった年の割合（%）")
ax.legend(frameon=False, fontsize=9, loc="lower right"); ax.set_title("その地点で観測していた期間のうち、記録がなかった年の割合", loc="left", fontsize=11.5)
note(ax, SOURCE + "\n観測期間＝その地点で最初に記録がある年〜最後に記録がある年（1960〜2019年の範囲で集計）", -0.17)
fig.savefig(FIG / "s2_noobs.png"); plt.close(fig)

# 図3：日付の変化
fig, ax = plt.subplots(figsize=(8.2, 4.4))
yy = np.arange(len(TR))
ax.errorbar(TR.trend_dec, yy, xerr=[TR.trend_dec - TR.lo, TR.hi - TR.trend_dec], fmt="o", color=BLUE, capsize=3)
for i, r in enumerate(TR.itertuples()): ax.text(r.hi + .3, i, f"{r.trend_dec:+.1f}日（{r.n_stations}地点）", va="center", fontsize=8.5)
ax.axvline(0, color=INK, lw=.7); ax.set_yticks(yy); ax.set_yticklabels(TR.name, fontsize=9)
ax.set_xlabel("10年あたりの変化（日、マイナス＝早まった）"); ax.set_xlim(TR.lo.min() - 1, TR.hi.max() + 5)
ax.set_title("初鳴・初見の日の変化（1953〜2020年、地点の違いを除いた回帰）", loc="left", fontsize=11.5)
note(ax, SOURCE + "\n30年以上記録がある地点。ひげは95%信頼区間（年でクラスター）", -0.17)
fig.savefig(FIG / "s2_date_trends.png"); plt.close(fig)
