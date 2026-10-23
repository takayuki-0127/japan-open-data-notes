"""S1：大学（学部）進学率は、男女それぞれどこまで上がりそうか。女性の短大進学の減少は、どれだけ大学進学に置き換わったか。
ロジスティック曲線（S字カーブ）の当てはめと残差ブートストラップ、年ごとの変化の回帰"""
from common import *
from scipy.optimize import curve_fit
import statsmodels.api as sm

r = rates().dropna(subset=["univ"]).reset_index(drop=True)
r.to_csv(RES / "s1_rates.csv", index=False, encoding="utf-8-sig")


def logi(t, K, b, t0, c):
    """下限 c から上限 K へ向かう S 字カーブ（t0 が真ん中の年、b が速さ）"""
    return c + (K - c) / (1 + np.exp(-b * (t - t0)))


def fit(y, t, p0, nboot=500, seed=0):
    bounds = ([0, 0.01, 1950, 0], [100, 1.0, 2100, max(y.min(), 0.1)])
    p, _ = curve_fit(logi, t, y, p0=p0, bounds=bounds, maxfev=20000)
    res = y - logi(t, *p); rng = np.random.default_rng(seed); Ks = []
    # 残差は前後の年で似るので、5年ずつのブロックで並べ替える（ブロック・ブートストラップ）
    blocks = [np.arange(i, min(i + 5, len(res))) for i in range(0, len(res), 5)]
    for _ in range(nboot):
        idx = []
        while len(idx) < len(res): idx.extend(blocks[rng.integers(0, len(blocks))])
        idx = np.array(idx[:len(res)])
        yb = logi(t, *p) + res[idx]
        try:
            pb, _ = curve_fit(logi, t, yb, p0=p, bounds=bounds, maxfev=20000); Ks.append(pb[0])
        except RuntimeError:
            pass
    return p, np.percentile(Ks, [2.5, 97.5]), np.sqrt(np.mean(res ** 2))


t = r.year.values.astype(float)
out = {}
for k, lab in [("univ_f", "女性"), ("univ_m", "男性")]:
    y = r[k].values
    p, ci, rmse = fit(y, t, [70, 0.1, 2000, 2])
    out[k] = dict(label=lab, K=p[0], K_lo=ci[0], K_hi=ci[1], b=p[1], t0=p[2], c=p[3], rmse=rmse, last=y[-1])
fits = pd.DataFrame(out).T; fits.to_csv(RES / "s1_logistic.csv", encoding="utf-8-sig"); print(fits)

# 男性：1976〜1990年の横ばい（定員抑制の時期）を外して当てはめた場合
mask = ~r.year.between(1976, 1990).values
pm, cim, rm = fit(r.univ_m.values[mask], t[mask], [70, 0.1, 2000, 10])
print("men excl 1976-1990", pm, cim)

# 置き換え：1994年以降、女性の短大進学率の年変化と大学進学率の年変化
q = r[r.year >= 1994].copy(); q["d_univ_f"] = q.univ_f.diff(); q["d_jc_f"] = q.jc_f.diff(); q = q.dropna()
ols = sm.OLS(q.d_univ_f, sm.add_constant(q.d_jc_f)).fit(cov_type="HAC", cov_kwds={"maxlags": 2})
print(ols.summary().tables[1])
gap = (r.univ_m - r.univ_f)
s = {"univ_f_1954": r.univ_f.iloc[0], "univ_f_2025": r.univ_f.iloc[-1], "univ_m_2025": r.univ_m.iloc[-1],
     "jc_f_peak_year": int(r.year[r.jc_f.idxmax()]), "jc_f_peak": r.jc_f.max(), "jc_f_2025": r.jc_f.iloc[-1],
     "univ_f_1994": r.set_index("year").loc[1994, "univ_f"], "univjc_f_1994": r.set_index("year").loc[1994, "univjc_f"],
     "gap_max_year": int(r.year[gap.idxmax()]), "gap_max": gap.max(), "gap_2025": gap.iloc[-1],
     "K_f": out["univ_f"]["K"], "K_f_lo": out["univ_f"]["K_lo"], "K_f_hi": out["univ_f"]["K_hi"], "t0_f": out["univ_f"]["t0"],
     "K_m": out["univ_m"]["K"], "K_m_lo": out["univ_m"]["K_lo"], "K_m_hi": out["univ_m"]["K_hi"],
     "K_m_excl": pm[0], "K_m_excl_lo": cim[0], "K_m_excl_hi": cim[1],
     "subst_slope": ols.params["d_jc_f"], "subst_lo": ols.conf_int().loc["d_jc_f", 0], "subst_hi": ols.conf_int().loc["d_jc_f", 1],
     "subst_const": ols.params["const"], "subst_r2": ols.rsquared, "n_subst": len(q)}
pd.Series(s).to_csv(RES / "s1_summary.csv", header=["value"]); print(pd.Series(s).round(3))

note = "\n（大学（学部）・短大（本科）への進学率は、過年度高卒者等を含む入学者数 ÷ 3年前の中学校等卒業者数）"
fig, ax = plt.subplots(figsize=(10, 4.8))
tt = np.arange(1954, 2061)
for k, c in [("univ_m", BLUE), ("univ_f", ORANGE)]:
    f = out[k]; ax.plot(r.year, r[k], color=c, lw=2, label=f"{f['label']}（実際）")
    ax.plot(tt, logi(tt, f["K"], f["b"], f["t0"], f["c"]), color=c, lw=1, ls="--", label=f"{f['label']}（S字カーブ、上限{f['K']:.0f}%）")
ax.plot(r.year, r.jc_f, color=ORANGE, lw=1, alpha=0.5, label="女性の短大進学率")
ax.set_ylabel("進学率（%）"); ax.set_xlim(1950, 2060); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("大学進学率のS字カーブ：女性は上限に向けてまだ上昇中")
fig.text(0.01, -0.06, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "s1_curves.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 3.2))
lab = ["女性（大学）", "男性（大学）", "男性（1976〜90年を除く）"]
K = [s["K_f"], s["K_m"], s["K_m_excl"]]; lo = [s["K_f_lo"], s["K_m_lo"], s["K_m_excl_lo"]]; hi = [s["K_f_hi"], s["K_m_hi"], s["K_m_excl_hi"]]
y = np.arange(3)
ax.errorbar(K, y, xerr=[np.array(K) - lo, np.array(hi) - K], fmt="o", color=INK, capsize=4)
for i in range(3): ax.text(hi[i] + 0.8, i, f"{K[i]:.1f}%（{lo[i]:.0f}〜{hi[i]:.0f}）", va="center", fontsize=9)
ax.axvline(r.univ_f.iloc[-1], color=ORANGE, ls=":", lw=1); ax.axvline(r.univ_m.iloc[-1], color=BLUE, ls=":", lw=1)
ax.set_yticks(y); ax.set_yticklabels(lab); ax.invert_yaxis(); ax.set_xlabel("S字カーブの上限（%、横線は95%区間）")
ax.set_xlim(min(lo) - 5, max(hi) + 18); ax.set_title("推定した上限：区間は広く、決め打ちはできない")
fig.text(0.01, -0.06, SOURCE + "\n（点線は2025年の実際の値：橙＝女性、青＝男性。区間は5年ブロックの残差ブートストラップ500回）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "s1_ceiling.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4.6))
ax.scatter(q.d_jc_f, q.d_univ_f, color=ORANGE, s=22)
xx = np.linspace(q.d_jc_f.min(), q.d_jc_f.max(), 10); ax.plot(xx, ols.params["const"] + ols.params["d_jc_f"] * xx, color=INK, lw=1)
for _, w in q[q.d_jc_f < -1.3].iterrows(): ax.annotate(int(w.year), (w.d_jc_f, w.d_univ_f), xytext=(3, 2), textcoords="offset points", fontsize=8)
ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("女性の短大進学率の前年差（ポイント）"); ax.set_ylabel("女性の大学進学率の前年差（ポイント）")
ax.set_title(f"短大が1ポイント減った年、大学は{-s['subst_slope']:.2f}ポイント多く増えた")
fig.text(0.01, -0.06, SOURCE + f"\n（{int(q.year.min())}〜2025年。回帰の傾き {s['subst_slope']:.2f}、95%区間 {s['subst_lo']:.2f}〜{s['subst_hi']:.2f}）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "s1_substitution.png"); plt.close(fig)
