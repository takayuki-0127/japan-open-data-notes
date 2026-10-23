"""S2：子どもが減ると、学校はどれくらい遅れて減るのか。
小学校・中学校の学校数と在籍者数（1948〜2025年）の対数差分に分布ラグ回帰を当てはめ、累積の弾力性を見る"""
from common import *
import statsmodels.api as sm

L = 10  # 最大ラグ（年）
out, cum = {}, {}
for name, lab in [("k003.xlsx", "小学校"), ("k004.xlsx", "中学校")]:
    d = schools(name).set_index("year")
    d["per_school"] = d.pupils / d.schools; d["per_teacher"] = d.pupils / d.teachers
    d.round(2).to_csv(RES / f"s2_{'elem' if lab == '小学校' else 'jhs'}.csv", encoding="utf-8-sig")
    g = np.log(d[["schools", "pupils"]]).diff() * 100
    X = pd.concat({f"lag{k}": g.pupils.shift(k) for k in range(L + 1)}, axis=1)
    z = pd.concat([g.schools, X], axis=1).dropna(); z = z[z.index >= 1975]  # 沖縄の編入（1973年）以降
    ols = sm.OLS(z.schools, sm.add_constant(z.drop(columns="schools"))).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    b = ols.params.drop("const"); V = ols.cov_params().drop(index="const", columns="const")
    cs = np.cumsum(b.values); se = [np.sqrt(V.values[:k + 1, :k + 1].sum()) for k in range(L + 1)]
    cum[lab] = pd.DataFrame({"lag": range(L + 1), "coef": b.values, "cum": cs, "cum_lo": cs - 1.96 * np.array(se), "cum_hi": cs + 1.96 * np.array(se)})
    cum[lab].round(4).to_csv(RES / f"s2_lags_{'elem' if lab == '小学校' else 'jhs'}.csv", index=False, encoding="utf-8-sig")
    peak = d.pupils.idxmax(); low = d.loc[1975:].pupils.idxmin()
    out[lab] = {"pupils_peak_year": int(peak), "pupils_peak": d.pupils.max(), "pupils_2025": d.pupils.iloc[-1],
                "schools_at_peak": d.loc[peak, "schools"], "schools_2025": d.schools.iloc[-1], "schools_max_year": int(d.schools.idxmax()), "schools_max": d.schools.max(),
                "pupil_change_pct_since_peak": (d.pupils.iloc[-1] / d.pupils.max() - 1) * 100,
                "school_change_pct_since_peak": (d.schools.iloc[-1] / d.loc[peak, "schools"] - 1) * 100,
                "per_school_peak": d.loc[peak, "per_school"], "per_school_2025": d.per_school.iloc[-1],
                "per_teacher_1948": d.per_teacher.iloc[0], "per_teacher_2025": d.per_teacher.iloc[-1],
                "const": ols.params["const"], "cum0": cs[0], "cum5": cs[5], "cum10": cs[10], "cum10_lo": cum[lab].cum_lo.iloc[-1], "cum10_hi": cum[lab].cum_hi.iloc[-1],
                "pupils_pct_1985_2025": (d.pupils.iloc[-1] / d.loc[1985, "pupils"] - 1) * 100, "schools_pct_1985_2025": (d.schools.iloc[-1] / d.loc[1985, "schools"] - 1) * 100,
                "r2": ols.rsquared, "n": int(ols.nobs), "y0": int(z.index.min())}
    # 2010年以降に限った長期の弾力性（学校数の変化率 ÷ 在籍者数の変化率）
    for a, b2 in [(1985, 2000), (2000, 2010), (2010, 2025)]:
        out[lab][f"pupils_pct_{a}_{b2}"] = (d.loc[b2, "pupils"] / d.loc[a, "pupils"] - 1) * 100
        out[lab][f"schools_pct_{a}_{b2}"] = (d.loc[b2, "schools"] / d.loc[a, "schools"] - 1) * 100
        out[lab][f"elast_{a}_{b2}"] = np.log(d.loc[b2, "schools"] / d.loc[a, "schools"]) / np.log(d.loc[b2, "pupils"] / d.loc[a, "pupils"])
s = pd.DataFrame(out); s.to_csv(RES / "s2_summary.csv", encoding="utf-8-sig"); print(s.round(3).to_string())

note = "\n（学校数は国公私立の計。在籍者数は児童・生徒数。1972年以前は沖縄県を含まない）"
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
for ax, (name, lab) in zip(axes, [("k003.xlsx", "小学校"), ("k004.xlsx", "中学校")]):
    d = schools(name).set_index("year")
    ax.plot(d.index, d.pupils / d.pupils.loc[1985] * 100, color=BLUE, lw=2, label="在籍者数")
    ax.plot(d.index, d.schools / d.schools.loc[1985] * 100, color=ORANGE, lw=2, label="学校数")
    ax.plot(d.index, d.teachers / d.teachers.loc[1985] * 100, color=GRAY, lw=1.4, label="本務教員数")
    ax.axhline(100, color=GRAY, lw=0.6, ls=":"); ax.set_title(lab); ax.set_ylabel("1985年＝100"); ax.legend(frameon=False, fontsize=9)
fig.suptitle(f"1985年から、小学校の子どもは{-out['小学校']['pupils_pct_1985_2025']:.0f}%減、学校は{-out['小学校']['schools_pct_1985_2025']:.0f}%減", y=1.02)
fig.text(0.01, -0.06, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "s2_index.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.4))
for lab, c in [("小学校", BLUE), ("中学校", ORANGE)]:
    q = cum[lab]; ax.plot(q.lag, q.cum, color=c, lw=2, marker="o", ms=4, label=lab)
    ax.fill_between(q.lag, q.cum_lo, q.cum_hi, color=c, alpha=0.15, lw=0)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xlabel("在籍者数が変わってからの年数"); ax.set_ylabel("学校数の累積の反応（弾力性）")
ax.set_title("子どもが1%減ったときの学校数の反応：数年かけて少しずつ")
ax.legend(frameon=False)
fig.text(0.01, -0.07, SOURCE + "\n（1975〜2025年。学校数の対数差分を、在籍者数の対数差分の0〜10年前に回帰。帯は95%区間（HAC標準誤差））", fontsize=7, color="#8a8984")
fig.savefig(FIG / "s2_lags.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.2))
for name, lab, c in [("k003.xlsx", "小学校", BLUE), ("k004.xlsx", "中学校", ORANGE)]:
    d = schools(name).set_index("year")
    ax.plot(d.index, d.pupils / d.schools, color=c, lw=2, label=f"{lab}：1校あたりの在籍者数")
    ax.plot(d.index, d.pupils / d.teachers, color=c, lw=1.2, ls="--", label=f"{lab}：教員1人あたり")
ax.set_ylabel("人"); ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title("1校あたりの子どもは減り、教員1人あたりはさらに減った")
fig.text(0.01, -0.06, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "s2_ratios.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.2))
per = ["1985〜2000年", "2000〜2010年", "2010〜2025年"]; keys = ["1985_2000", "2000_2010", "2010_2025"]; x = np.arange(3); w = 0.36
for i, (lab, c) in enumerate([("小学校", BLUE), ("中学校", ORANGE)]):
    v = [out[lab][f"elast_{k}"] for k in keys]
    ax.bar(x + (i - 0.5) * w, v, width=w, color=c, label=lab)
    for xi, vi, k in zip(x, v, keys):
        ax.text(xi + (i - 0.5) * w, vi + 0.04, f"{vi:.2f}\n(子{out[lab]['pupils_pct_' + k]:+.0f}%/校{out[lab]['schools_pct_' + k]:+.0f}%)", ha="center", fontsize=7.5)
ax.axhline(1, color=GRAY, ls=":", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(per); ax.set_ylim(-0.2, 2.2)
ax.set_ylabel("学校数の変化率 ÷ 子どもの変化率"); ax.legend(frameon=False)
ax.set_title("子どもが3割減った1985〜2000年に学校はほぼ減らず、2000年以降に減り始めた")
fig.text(0.01, -0.06, SOURCE + "\n（対数変化の比。1＝子どもと同じ割合で学校が減る。括弧内は期間中の在籍者数と学校数の変化率）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "s2_periods.png"); plt.close(fig)
