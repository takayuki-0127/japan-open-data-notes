"""V1：2020〜2025年の月別死亡数は、それまでの傾向から予想される数よりどれだけ多かったか（超過死亡）。
基準期間（2012〜2019年）の月別死亡数に、トレンドと月の効果をもつ準ポアソン回帰を当てはめ、2020年以降を予測して比べる"""
from common import *
import statsmodels.api as sm

m = monthly_deaths(); m = m[m.year >= 2005].copy()
m["t"] = (m.year - 2012) * 12 + m.month - 1
m["mon"] = m.month.astype(str)


def design(d, trend):
    """切片・月（1月が基準）・トレンド（必要なら2乗）の説明変数"""
    X = pd.DataFrame({"const": 1.0}, index=d.index)
    for k in range(2, 13): X[f"m{k}"] = (d.month == k).astype(float)
    X["t"] = d.t / 12
    if trend == "quadratic": X["t2"] = (d.t / 12) ** 2
    return X


def fit_predict(base_years, trend="linear", nsim=4000, seed=0):
    b = m[m.year.between(*base_years)]
    res = sm.GLM(b.deaths, design(b, trend), family=sm.families.Poisson(), offset=np.log(b.days)).fit(scale="X2")
    fut = m[m.year >= 2020].copy()
    Xf = design(fut, trend).values
    mu = np.exp(Xf @ res.params.values + np.log(fut.days.values))
    # パラメータの不確かさ（多変量正規）＋過分散（準ポアソン：分散 = φμ をガンマ近似）を乱数で評価
    rng = np.random.default_rng(seed)
    beta = rng.multivariate_normal(res.params.values, res.cov_params().values, nsim)
    mus = np.exp(beta @ Xf.T + np.log(fut.days.values))
    phi = res.scale
    sims = rng.gamma(shape=mus / phi, scale=phi)
    fut["expected"] = mu; fut["lo"] = np.percentile(sims, 2.5, axis=0); fut["hi"] = np.percentile(sims, 97.5, axis=0)
    fut["excess"] = fut.deaths - fut.expected
    ann_sims = pd.DataFrame(sims.T, index=fut.index).groupby(fut.year).sum()
    ann = fut.groupby("year").agg(observed=("deaths", "sum"), expected=("expected", "sum"))
    ann["excess"] = ann.observed - ann.expected; ann["excess_pct"] = ann.excess / ann.expected * 100
    ann["exp_lo"] = ann_sims.quantile(0.025, axis=1); ann["exp_hi"] = ann_sims.quantile(0.975, axis=1)
    ann["exc_lo"] = ann.observed - ann.exp_hi; ann["exc_hi"] = ann.observed - ann.exp_lo
    return res, fut, ann


res, fut, ann = fit_predict((2012, 2019))
fut[["year", "month", "deaths", "expected", "lo", "hi", "excess"]].round(0).to_csv(RES / "v1_monthly.csv", index=False, encoding="utf-8-sig")
ann.round(1).to_csv(RES / "v1_annual.csv", encoding="utf-8-sig"); print(ann.round(0))

# 頑健性：基準期間とトレンドの形を変える
rob = []
for by in [(2012, 2019), (2015, 2019), (2010, 2019)]:
    for tr in ["linear", "quadratic"]:
        _, _, a = fit_predict(by, tr)
        rob.append(dict(base=f"{by[0]}-{by[1]}", trend=tr, **{f"excess_{y}": a.loc[y, "excess"] for y in a.index}, total=a.excess.sum()))
rob = pd.DataFrame(rob); rob.round(0).to_csv(RES / "v1_robustness.csv", index=False, encoding="utf-8-sig"); print(rob.round(0).to_string())

# 月ごとの超過の割合が大きかった月
top = fut.assign(pct=fut.excess / fut.expected * 100).sort_values("pct", ascending=False).head(8)[["year", "month", "deaths", "expected", "pct"]]
top.round(1).to_csv(RES / "v1_top_months.csv", index=False, encoding="utf-8-sig"); print(top.round(1))
s = {"phi": res.scale, "trend_pct_per_year": (np.exp(res.params["t"]) - 1) * 100,
     "total_excess_2020_2025": ann.excess.sum(), "excess_2020": ann.loc[2020, "excess"], "excess_2022": ann.loc[2022, "excess"],
     "excess_2025": ann.loc[2025, "excess"], "excess_pct_2022": ann.loc[2022, "excess_pct"], "excess_pct_2025": ann.loc[2025, "excess_pct"],
     "n_months_above_pi": int((fut.deaths > fut.hi).sum()), "n_months_below_pi": int((fut.deaths < fut.lo).sum()), "n_months": len(fut),
     "rob_total_min": rob.total.min(), "rob_total_max": rob.total.max()}
pd.Series(s).to_csv(RES / "v1_summary.csv", header=["value"]); print(pd.Series(s).round(2))

note = "\n（基準：2012〜2019年の月別死亡数に、直線のトレンド＋月の効果＋月の日数を入れた準ポアソン回帰。帯は予測の95%区間）"
fig, ax = plt.subplots(figsize=(11, 4.6))
h = m[m.year >= 2012]
ax.plot(h.date, h.deaths / 1e4, color=INK, lw=1.2, label="実際の死亡数")
ax.plot(fut.date, fut.expected / 1e4, color=BLUE, lw=1.6, label="2019年までの傾向からの予想")
ax.fill_between(fut.date, fut.lo / 1e4, fut.hi / 1e4, color=LIGHT, alpha=0.6, lw=0, label="予想の95%区間")
ax.axvline(pd.Timestamp("2020-01-01"), color=GRAY, lw=0.8, ls="--")
ax.set_ylabel("死亡数（万人／月）"); ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("2022年以降、死亡数は予想の帯を上回る月が続いた")
fig.text(0.01, -0.06, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "v1_monthly.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.4))
yrs = ann.index.values
ax.bar(yrs, ann.excess / 1e4, color=[GREEN if v < 0 else ORANGE for v in ann.excess], width=0.6)
ax.errorbar(yrs, ann.excess / 1e4, yerr=[(ann.excess - ann.exc_lo) / 1e4, (ann.exc_hi - ann.excess) / 1e4], fmt="none", color=INK, lw=1, capsize=3)
for y, v, p in zip(yrs, ann.excess, ann.excess_pct): ax.text(y + 0.33, v / 1e4 / 2, f"{v/1e4:+.1f}万\n({p:+.1f}%)", ha="left", va="center", fontsize=8.5)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_ylabel("超過死亡数（万人）"); ax.set_xticks(yrs)
ax.set_title("年ごとの超過死亡：2020年は予想より少なく、2022〜2024年は約12〜13万人多い")
fig.text(0.01, -0.06, SOURCE + note + "。誤差棒は予想の95%区間から計算", fontsize=7, color="#8a8984"); fig.savefig(FIG / "v1_annual.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.2))
lab = [f"{r.base}・{'直線' if r.trend == 'linear' else '2次曲線'}" for r in rob.itertuples()]
ax.barh(range(len(rob)), rob.total / 1e4, color=[BLUE if t == "linear" else PURPLE for t in rob.trend])
for i, v in enumerate(rob.total): ax.text(v / 1e4 + 0.5, i, f"{v/1e4:.1f}万", va="center", fontsize=9)
ax.set_yticks(range(len(rob))); ax.set_yticklabels(lab, fontsize=9); ax.invert_yaxis()
ax.set_xlabel("2020〜2025年の超過死亡の合計（万人）"); ax.set_title("2020〜2025年の合計は、基準の取り方で8万〜47万人まで変わる")
fig.text(0.01, -0.06, SOURCE + "\n（左：基準期間・トレンドの形）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "v1_robustness.png"); plt.close(fig)
