"""台風の発生数と、日本への接近数（1951〜2025年）。ポアソン回帰・負の二項回帰の年トレンド（HAC標準誤差）と、月の分布の変化"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

d = load(); s = storms(d)
H = hourly(d)
H = H[H.ts]
lat = np.array([v[0] for v in OBS.values()]); lon = np.array([v[1] for v in OBS.values()])
# 近くの点だけ計算（粗い箱でしぼる）
near = H[(H.lat.between(19, 49)) & (H.lon.between(119, 150))].copy()
D = hav(near.lat.values[:, None], near.lon.values[:, None], lat[None, :], lon[None, :])
near["dmin"] = D.min(axis=1)
near["obs"] = np.array(list(OBS.keys()))[D.argmin(axis=1)]
app = near[near.dmin <= 300]
first = app.sort_values("time").groupby("sid").first()
s["approach"] = s.index.isin(first.index).astype(int)
s["t_app"] = first.time.reindex(s.index)
s["app_month"] = s.t_app.dt.month
# 最も近づいたときの距離と気圧（全期間のTS以上の点で）
cl = near.sort_values("dmin").groupby("sid").first()
s["dmin_km"] = cl.dmin.reindex(s.index); s["pres_at_closest"] = cl.pres.reindex(s.index)
s.to_csv(RES / "y1_storms.csv", encoding="utf-8-sig")

yr = pd.DataFrame({"formed": s.groupby("year").size(), "approach": s.groupby("year").approach.sum()}).reindex(range(Y0, Y1 + 1), fill_value=0)
yr.index.name = "year"; yr.to_csv(RES / "y1_yearly.csv", encoding="utf-8-sig")


def trend(y, years, label):
    X = sm.add_constant((years - 2000) / 10)
    out = []
    for fam, nm in [(sm.families.Poisson(), "ポアソン"), (sm.families.NegativeBinomial(alpha=0.05), "負の二項")]:
        m = sm.GLM(y, X, family=fam).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        b, se = np.asarray(m.params)[1], np.asarray(m.bse)[1]
        out.append({"series": label, "model": nm, "period": f"{years.min()}-{years.max()}", "pct_per_decade": (np.exp(b) - 1) * 100,
                    "lo": (np.exp(b - 1.96 * se) - 1) * 100, "hi": (np.exp(b + 1.96 * se) - 1) * 100, "p": np.asarray(m.pvalues)[1],
                    "dispersion": m.pearson_chi2 / m.df_resid})
    return out


T = []
for y0 in (1951, 1977):
    sub = yr.loc[y0:]
    T += trend(sub.formed.values, sub.index.values, "発生数") + trend(sub.approach.values, sub.index.values, "接近数")
T = pd.DataFrame(T); T.to_csv(RES / "y1_trend.csv", index=False, encoding="utf-8-sig"); print(T.round(3).to_string())
per = pd.DataFrame({"1951-1980": yr.loc[1951:1980].mean(), "1996-2025": yr.loc[1996:2025].mean()}); print(per.round(2))
per.to_csv(RES / "y1_period_mean.csv", encoding="utf-8-sig")
share = (yr.approach / yr.formed); print("接近の割合", share.loc[1951:1980].mean().round(3), share.loc[1996:2025].mean().round(3))
print(yr.formed.describe().round(1), yr.approach.describe().round(1))
print("最多・最少", yr.formed.idxmax(), yr.formed.max(), yr.formed.idxmin(), yr.formed.min(), "接近", yr.approach.idxmax(), yr.approach.max(), yr.approach.idxmin(), yr.approach.min())

# 月の分布
def mdist(col, a, b):
    x = s[(s.year >= a) & (s.year <= b)][col].dropna().astype(int)
    return x.value_counts().reindex(range(1, 13), fill_value=0) / (b - a + 1)
M = pd.DataFrame({"発生_1951-1980": mdist("month", 1951, 1980), "発生_1996-2025": mdist("month", 1996, 2025),
                  "接近_1951-1980": mdist("app_month", 1951, 1980), "接近_1996-2025": mdist("app_month", 1996, 2025)})
M.index.name = "month"; M.to_csv(RES / "y1_month.csv", encoding="utf-8-sig"); print(M.round(2))
# 接近の月の平均と、10月以降の接近
for a, b in [(1951, 1980), (1996, 2025)]:
    x = s[(s.year >= a) & (s.year <= b) & s.approach.eq(1)]
    print(a, b, "接近月平均", round(x.app_month.mean(), 2), "10月以降", round((x.app_month >= 10).sum() / (b - a + 1), 2), "7月以前", round((x.app_month <= 7).sum() / (b - a + 1), 2))
# 月の分布の差の検定（カイ二乗）
from scipy.stats import chi2_contingency
for col in ("month", "app_month"):
    a = s[(s.year <= 1980)][col].dropna().astype(int).value_counts().reindex(range(1, 13), fill_value=0)
    b = s[(s.year >= 1996)][col].dropna().astype(int).value_counts().reindex(range(1, 13), fill_value=0)
    tab = np.vstack([a.values, b.values]); tab = tab[:, tab.sum(0) > 0]
    # 少ない月をまとめる：1-5月、6,7,8,9,10、11-12月
    grp = lambda v: np.array([v[0:5].sum(), v[5], v[6], v[7], v[8], v[9], v[10:12].sum()])
    tab2 = np.vstack([grp(a.values), grp(b.values)])
    c = chi2_contingency(tab2); print(col, "chi2", round(c[0], 2), "p", round(c[1], 4))
    pd.DataFrame(tab2, index=["1951-1980", "1996-2025"], columns=["1-5月", "6月", "7月", "8月", "9月", "10月", "11-12月"]).assign(chi2=c[0], p=c[1]).to_csv(RES / f"y1_month_test_{col}.csv", encoding="utf-8-sig")

# 図1：年ごとの数
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(yr.index, yr.formed, color=LIGHT, label="発生数（台風になった数）")
ax.bar(yr.index, yr.approach, color=BLUE, label="日本への接近数")
for col, c in [("formed", GRAY), ("approach", INK)]:
    r = yr[col].rolling(11, center=True).mean(); ax.plot(r.index, r, color=c, lw=2)
ax.set_xlim(1950, 2026); ax.set_ylabel("個数"); ax.legend(frameon=False, ncol=2, loc="upper right")
ax.set_title("台風の発生数と日本への接近数（1951〜2025年、線は11年移動平均）", loc="left", fontsize=12)
note(ax, SOURCE + "\n接近＝中心が全国50か所の気象台（都道府県庁所在地など）のどれかから300km以内に入った台風", -0.13)
fig.savefig(FIG / "y1_counts.png"); plt.close(fig)

# 図2：月の分布
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=False)
for ax, (k, t) in zip(axes, [("発生", "発生した月"), ("接近", "接近した月")]):
    a, b = M[f"{k}_1951-1980"], M[f"{k}_1996-2025"]
    ax.bar(M.index - .2, a, .4, color=GRAY, label="1951〜1980年")
    ax.bar(M.index + .2, b, .4, color=BLUE, label="1996〜2025年")
    ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}" for m in range(1, 13)]); ax.set_xlabel("月")
    ax.set_title(t, loc="left")
axes[0].set_ylabel("1年あたりの個数"); axes[0].legend(frameon=False)
fig.suptitle("台風が発生・接近する月（30年ずつの平均）", x=.02, y=1.04, ha="left", fontsize=12)
note(axes[0], SOURCE, -0.2); fig.savefig(FIG / "y1_month.png"); plt.close(fig)

# 気象台ごとの接近数（30年比較）：その気象台から300km以内に入った台風の数
ok = (D <= 300)
cnt = []
for a, b in [(1951, 1980), (1996, 2025)]:
    ids = set(s[(s.year >= a) & (s.year <= b)].index)
    m_ = near.sid.isin(ids).values
    x = {o: near.sid.values[m_ & ok[:, j]] for j, o in enumerate(OBS.keys())}
    cnt.append(pd.Series({o: len(set(v)) / (b - a + 1) for o, v in x.items()}, name=f"{a}-{b}"))
C = pd.concat(cnt, axis=1); C.index.name = "気象台"
C["diff"] = C["1996-2025"] - C["1951-1980"]; C.to_csv(RES / "y1_by_obs.csv", encoding="utf-8-sig"); print(C.sort_values("diff").round(2).to_string())

# 図3：気象台ごとの接近数の変化（北から南へ）
C2 = C.copy(); C2["lat"] = [OBS[o][0] for o in C2.index]; C2 = C2.sort_values("lat")
fig, ax = plt.subplots(figsize=(7.6, 9.6))
yy = np.arange(len(C2))
ax.barh(yy, C2["diff"], color=[BLUE if v > 0 else ORANGE for v in C2["diff"]])
ax.set_yticks(yy); ax.set_yticklabels(C2.index, fontsize=8.5); ax.axvline(0, color=INK, lw=.7)
for i, (v, a, b) in enumerate(zip(C2["diff"], C2["1951-1980"], C2["1996-2025"])):
    ax.text(v + (0.02 if v >= 0 else -0.02), i, f"{a:.1f}→{b:.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=7.5, color=GRAY)
ax.set_xlim(-0.9, 0.7)
ax.set_xlabel("300km以内に入った台風の数の差（1年あたり、1996〜2025年 − 1951〜1980年）")
ax.set_title("気象台ごとの接近数の変化（上ほど北）", loc="left", fontsize=12)
note(ax, SOURCE, -0.085); fig.savefig(FIG / "y1_by_obs.png"); plt.close(fig)
