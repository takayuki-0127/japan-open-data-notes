"""H2：同じ暑さでも、夏の初め（体が暑さに慣れていない時期）のほうが搬送が多いのか。そして、同じ暑さでの搬送は年々増えているのか。
WBGT25を超えた分の傾き（折れ線の効果）を月ごと・「その年すでに暑い日が何日あったか」ごとに推定し、年の効果も比べる"""
from common import *
import statsmodels.api as sm
import statsmodels.formula.api as smf

m = panel()
m["h"] = np.maximum(m.wbgt_max - 25, 0); m["c"] = np.minimum(m.wbgt_max - 25, 0)
m["hl1"] = np.maximum(m.wbgt_l1 - 25, 0)
m["mon"] = m.month.map({5: "5月", 6: "6月", 7: "7月", 8: "8月", 9: "9月"})
m["exp"] = pd.cut(m.hot_days_sofar, [-1, 0, 5, 15, 30, 200], labels=["0日", "1〜5日", "6〜15日", "16〜30日", "31日以上"])
base = "C(city) + C(year) + C(dow) + c + hl1"
rows = []
for var, lab in [("mon", "月"), ("exp", "その年それまでのWBGT28以上の日数")]:
    f = f"n ~ h:C({var}) + C({var}) + {base}"
    r = smf.glm(f, data=m, family=sm.families.Poisson(), offset=np.log(m["pop"])).fit(scale="X2")
    for k in [p for p in r.params.index if p.startswith("h:")]:
        lv = k.split("[")[1].rstrip("]"); lv = lv.split(".", 1)[-1] if "." in lv else lv
        rows.append(dict(by=lab, level=lv, rr_per_1c=np.exp(r.params[k]), lo=np.exp(r.conf_int().loc[k, 0]), hi=np.exp(r.conf_int().loc[k, 1]),
                         n_days=int((m[var].astype(str) == lv).sum())))
t = pd.DataFrame(rows); t.round(4).to_csv(RES / "h2_slopes.csv", index=False, encoding="utf-8-sig"); print(t.round(3))

# 年の効果：同じ WBGT（スプラインで調整）でも搬送はどう変わったか（2016年＝1）
KN = "bs(wbgt_max, knots=(22, 26, 29, 31), degree=2, lower_bound=5, upper_bound=37)"
r = smf.glm(f"n ~ {KN} + wbgt_l1 + wbgt_l2 + C(city) + C(year) + C(dow) + C(month)", data=m, family=sm.families.Poisson(), offset=np.log(m["pop"])).fit(scale="X2")
yr = pd.DataFrame([(2016, 1.0, 1.0, 1.0)] + [(int(k.split("T.")[1].rstrip("]")), np.exp(r.params[k]), np.exp(r.conf_int().loc[k, 0]), np.exp(r.conf_int().loc[k, 1]))
                   for k in r.params.index if k.startswith("C(year)")], columns=["year", "rr", "lo", "hi"])
raw = m.groupby("year").agg(n=("n", "sum"), wbgt=("wbgt_max", "mean"), hot31=("wbgt_max", lambda s: (s >= 31).sum()))
yr = yr.merge(raw, left_on="year", right_index=True); yr.round(3).to_csv(RES / "h2_year_effects.csv", index=False, encoding="utf-8-sig"); print(yr.round(2))
# 高齢者の割合と WBGT
m["el_sh"] = m.elderly / m.n
s = {"may_rr": t[(t.by == "月") & (t.level == "5月")].rr_per_1c.iloc[0], "aug_rr": t[(t.by == "月") & (t.level == "8月")].rr_per_1c.iloc[0],
     "jun_rr": t[(t.by == "月") & (t.level == "6月")].rr_per_1c.iloc[0], "jul_rr": t[(t.by == "月") & (t.level == "7月")].rr_per_1c.iloc[0], "sep_rr": t[(t.by == "月") & (t.level == "9月")].rr_per_1c.iloc[0],
     "exp0_rr": t[t.level == "0日"].rr_per_1c.iloc[0], "exp31_rr": t[t.level == "31日以上"].rr_per_1c.iloc[0],
     "yr2025": yr.set_index("year").loc[2025, "rr"], "yr2025_lo": yr.set_index("year").loc[2025, "lo"], "yr2025_hi": yr.set_index("year").loc[2025, "hi"],
     "yr2020": yr.set_index("year").loc[2020, "rr"], "yr2018": yr.set_index("year").loc[2018, "rr"]}
pd.Series(s).to_csv(RES / "h2_summary.csv", header=["value"]); print(pd.Series(s).round(3))

note = "\n（6都市・2016〜2025年5〜9月。準ポアソン回帰：WBGT25を超えた分の傾きをグループ別に推定。都市・年・曜日、WBGT25未満の部分、前日のWBGTを調整）"
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
for ax, (lab, g) in zip(axes, t.groupby("by", sort=False)):
    x = np.arange(len(g))
    ax.errorbar(x, g.rr_per_1c, yerr=[g.rr_per_1c - g.lo, g.hi - g.rr_per_1c], fmt="o", color=ORANGE, capsize=4)
    ax.set_xticks(x); ax.set_xticklabels(g.level, fontsize=9); ax.set_title(lab, fontsize=11)
    for xi, v in zip(x, g.rr_per_1c): ax.text(xi + 0.08, v, f"×{v:.2f}", fontsize=8.5, va="center")
axes[0].set_ylabel("WBGTが1℃上がるごとの倍率（WBGT25超の部分）")
fig.suptitle("WBGT1℃あたりの増え方は6月がやや大きいが、「夏の初めほど増えやすい」とまでは言えない", y=1.03)
fig.text(0.01, -0.08, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "h2_season.png"); plt.close(fig)

fig, ax1 = plt.subplots(figsize=(9, 4.4))
ax1.errorbar(yr.year, yr.rr, yerr=[yr.rr - yr.lo, yr.hi - yr.rr], fmt="o-", color=BLUE, capsize=3, label="同じ暑さでの搬送（2016年＝1）")
ax1.axhline(1, color=GRAY, lw=0.6); ax1.set_ylabel("倍率（WBGTなどを調整）"); ax1.set_xticks(yr.year)
ax2 = ax1.twinx(); ax2.bar(yr.year, yr.hot31, color=ORANGE, alpha=0.25, width=0.6, label="WBGT31以上の日数（6都市合計）"); ax2.set_ylabel("日数")
ax1.set_zorder(ax2.get_zorder() + 1); ax1.patch.set_visible(False)
h1_, l1_ = ax1.get_legend_handles_labels(); h2_, l2_ = ax2.get_legend_handles_labels(); ax1.legend(h1_ + h2_, l1_ + l2_, frameon=False, fontsize=8.5, loc="upper left")
ax1.set_title("暑さを調整した年の効果：2018〜2020年が高く、2021年以降は2016年並み〜1.1倍")
fig.text(0.01, -0.07, SOURCE + "\n（年の効果は、WBGT（スプライン・前日・前々日）、都市・曜日・月を調整した準ポアソン回帰の年ダミー。2020年は5月の調査なし）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "h2_years.png"); plt.close(fig)
