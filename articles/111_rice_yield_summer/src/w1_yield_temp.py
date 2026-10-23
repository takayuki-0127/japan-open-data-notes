"""W1：夏が暑い年・寒い年に、10a当たり収量は下がるのか（全国と地域、1958〜2025年）"""
from common import *
import statsmodels.api as sm
import statsmodels.formula.api as smf

lo = sm.nonparametric.lowess
p, t = panel(), summer_temp()
t = t[t.year <= 2025].copy()
# 夏（6〜8月）の気温：温暖化でじわじわ上がる分（LOWESS、frac=0.3）を除いた「その年だけの暑さ寒さ」
t["jja_trend"] = lo(t.jja, t.year, frac=0.3, return_sorted=False)
t["tdev"] = t.jja - t.jja_trend

# ---- 全国：作況指数（平年収量に対する比）と、自前のトレンド除去（LOWESS）の両方
nat = p[(p.level == "region") & (p.name == "全国")].merge(t, on="year")
nat["y_trend"] = lo(nat.yield_kg, nat.year, frac=0.3, return_sorted=False)
nat["ydev"] = (nat.yield_kg / nat.y_trend - 1) * 100
nat.to_csv(RES / "w1_national.csv", index=False, encoding="utf-8")


def fit(d, y="sakkyo_any"):
    """寒い側と暑い側で傾きを分けた折れ線回帰（HC1標準誤差）"""
    d = d.dropna(subset=[y, "tdev"]).copy()
    d["cold"] = d.tdev.clip(upper=0); d["hot"] = d.tdev.clip(lower=0)
    m = smf.ols(f"{y} ~ cold + hot", d).fit(cov_type="HC1")
    q = smf.ols(f"{y} ~ tdev + I(tdev**2)", d).fit(cov_type="HC1")
    return {"n": len(d), "r": d[y].corr(d.tdev), "b_cold": m.params["cold"], "se_cold": m.bse["cold"],
            "b_hot": m.params["hot"], "se_hot": m.bse["hot"], "b_lin": smf.ols(f"{y} ~ tdev", d).fit().params["tdev"],
            "q2": q.params["I(tdev ** 2)"], "q2_se": q.bse["I(tdev ** 2)"]}


rows = []
d58 = nat[nat.year >= 1958]
rows.append({"系列": "全国 作況指数 1958-2025", **fit(d58)})
rows.append({"系列": "全国 LOWESS偏差% 1958-2025", **fit(d58, "ydev")})
rows.append({"系列": "全国 LOWESS偏差% 1898-2025", **fit(nat, "ydev")})
rows.append({"系列": "全国 作況指数 1958-1999", **fit(d58[d58.year <= 1999])})
rows.append({"系列": "全国 作況指数 2000-2025", **fit(d58[d58.year >= 2000])})
fits = pd.DataFrame(rows).round(3)
fits.to_csv(RES / "w1_fit_national.csv", index=False, encoding="utf-8")
print(fits.to_string())

# 暑い年・寒い年の一覧（気温偏差の上位・下位10年）
show = ["year", "jja", "tdev", "yield_kg", "normal_yield_kg", "sakkyo_any", "ydev"]
ext = pd.concat([d58.nsmallest(10, "tdev").assign(区分="寒い夏"), d58.nlargest(10, "tdev").assign(区分="暑い夏")])[["区分"] + show]
ext.round(2).to_csv(RES / "w1_extreme_years.csv", index=False, encoding="utf-8")
print(ext.round(2).to_string())
hot = d58[d58.tdev >= 0.6]
print("暑い夏（tdev>=0.6）平均作況：", hot.groupby(hot.year >= 2000).sakkyo_any.mean().round(1).to_dict())
cold = d58[d58.tdev <= -0.5]
print("寒い夏（tdev<=-0.5）平均作況：", round(cold.sakkyo_any.mean(), 1), len(cold))

# ---- 地域別：地域の作況指数を全国の夏の気温偏差で説明（地域の気温ではない点に注意）
REG = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州"]
reg = p[(p.level == "region") & p.name.isin(REG) & (p.year >= 1958)].merge(t, on="year")
rr = pd.DataFrame([{"地域": r, **fit(reg[reg.name == r])} for r in REG]).round(3)
rr.to_csv(RES / "w1_fit_region.csv", index=False, encoding="utf-8")
print(rr.to_string())
YRS = [1993, 2003, 2010, 2023, 2025]
kt = reg[reg.year.isin(YRS)].pivot(index="name", columns="year", values="sakkyo_any").loc[REG]
kt.to_csv(RES / "w1_region_key_years.csv", encoding="utf-8")
print(kt.to_string())
# 都道府県で作況指数が最も低かった県（主な年）
pf = p[(p.level == "pref") & p.year.isin(YRS)]
print(pf.sort_values("sakkyo_any").groupby("year").head(3)[["year", "name", "sakkyo_any"]].to_string())

# ---- 図1：収量と平年収量の推移、作況指数
fig, ax = plt.subplots(2, 1, figsize=(9, 7), sharex=True, gridspec_kw={"height_ratios": [1.2, 1]})
a = ax[0]
a.plot(nat.year, nat.yield_kg, color=BLUE, lw=1.4, label="10a当たり収量（実際）")
a.plot(d58.year, d58.normal_yield_kg, color=GRAY, lw=1.6, ls="--", label="10a当たり平年収量")
for y in [1993, 2003, 1980, 1945, 1934]:
    v = nat.loc[nat.year == y, "yield_kg"]
    if len(v):
        a.annotate(f"{y}年\n{v.iloc[0]:.0f}kg", (y, v.iloc[0]), xytext=(0, -20), textcoords="offset points", ha="center", fontsize=8, color=ORANGE)
a.set_ylim(140, 570); a.set_ylabel("kg / 10a"); a.legend(frameon=False, loc="upper left"); a.set_title("水稲の10a当たり収量（全国、1898〜2025年）")
b = ax[1]
b.bar(d58.year, d58.sakkyo_any - 100, bottom=100, color=np.where(d58.tdev < 0, BLUE, ORANGE), width=0.8)
b.axhline(100, color=INK, lw=0.6)
for y in [1993, 2003, 2010, 2023]:
    v = d58.loc[d58.year == y, "sakkyo_any"].iloc[0]
    b.annotate(f"{y}\n{v:.0f}", (y, v), xytext=(0, -24 if v < 100 else 4), textcoords="offset points", ha="center", fontsize=8)
b.set_ylabel("作況指数（平年＝100）"); b.set_ylim(65, 116)
b.set_title("作況指数（青＝平年より涼しい夏、橙＝暑い夏）", fontsize=11)
note(b, y=-0.2)
fig.savefig(FIG / "w1_series.png"); plt.close(fig)

# ---- 図2：夏の気温偏差と作況指数の散布図
fig, a = plt.subplots(figsize=(8, 5.6))
c = np.where(d58.year >= 2000, ORANGE, BLUE)
a.scatter(d58.tdev, d58.sakkyo_any, c=c, s=26, alpha=0.85)
f0 = fit(d58); xs = np.linspace(d58.tdev.min(), d58.tdev.max(), 50)
m = smf.ols("sakkyo_any ~ cold + hot", d58.assign(cold=d58.tdev.clip(upper=0), hot=d58.tdev.clip(lower=0))).fit()
a.plot(xs, m.params.Intercept + m.params.cold * np.minimum(xs, 0) + m.params.hot * np.maximum(xs, 0), color=INK, lw=1.2)
for _, r in d58.iterrows():
    if r.year in (1993, 2003, 1980, 1976, 1978, 1994, 1984, 2010, 2023, 2025, 2009):
        a.annotate(int(r.year), (r.tdev, r.sakkyo_any), xytext=(4, 3), textcoords="offset points", fontsize=8)
a.axhline(100, color=GRAY, lw=0.6); a.axvline(0, color=GRAY, lw=0.6)
a.set_xlabel("夏（6〜8月）の気温の偏差（℃、長期の上昇を除いた分）"); a.set_ylabel("作況指数（平年＝100）")
a.set_title(f"涼しい夏は大きく減り、暑い夏は減らない（全国、1958〜2025年）\n傾き：涼しい側 {f0['b_cold']:.1f}／℃、暑い側 {f0['b_hot']:.1f}／℃", fontsize=12)
a.scatter([], [], c=BLUE, s=26, label="1958〜1999年"); a.scatter([], [], c=ORANGE, s=26, label="2000〜2025年"); a.legend(frameon=False, loc="lower right")
note(a, y=-0.14)
fig.savefig(FIG / "w1_scatter.png"); plt.close(fig)

# ---- 図3：地域別の作況指数（主な年）
fig, a = plt.subplots(figsize=(9, 5))
w = 0.16; x = np.arange(len(REG)); cols = [BLUE, LIGHT, ORANGE, "#f2a07b", GREEN]
for i, y in enumerate(YRS):
    a.bar(x + (i - 2) * w, kt[y].values - 100, bottom=100, width=w, color=cols[i], label=f"{y}年")
a.axhline(100, color=INK, lw=0.6); a.set_xticks(x); a.set_xticklabels(REG)
a.set_ylim(30, 115); a.set_ylabel("作況指数（平年＝100）")
a.set_title("地域別の作況指数：1993年は北海道・東北が大きく落ちた")
a.legend(frameon=False, ncol=5, loc="lower center")
note(a, y=-0.12)
fig.savefig(FIG / "w1_region.png"); plt.close(fig)
