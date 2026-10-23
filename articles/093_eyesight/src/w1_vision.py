"""W1：裸眼視力1.0未満の子どもは、40年あまりでどれだけ増えたか（学校種別・年齢別・都道府県別）"""
from common import *
import statsmodels.api as sm

d = load_disease()
t = d[d.sex == "計"].copy()
SCH = ["幼稚園", "小学校", "中学校", "高等学校"]
COL = {"幼稚園": GRAY, "小学校": BLUE, "中学校": ORANGE, "高等学校": PURPLE}
v = t[t["1.0未満"].notna()]
first = v.groupby("school").year.min()
print("1.0未満の最初の年度:", first.to_dict())
t[t.year >= 1979][["year", "school", "1.0未満", "0.7以上1.0未満", "0.3以上0.7未満", "0.3未満", "むし歯"]].sort_values(["school", "year"]).to_csv(RES / "w1_school_trend.csv", index=False, encoding="utf-8-sig")

# 年あたりの増え方（1979〜2019年度、測定時期が違う2020〜2023年度は入れない）
rows = []
for s in SCH:
    x = t[(t.school == s) & t.year.between(1979, 2019)].dropna(subset=["1.0未満"])
    m = sm.OLS(x["1.0未満"], sm.add_constant(x.year)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    g = lambda y, c="1.0未満": t[(t.school == s) & (t.year == y)][c].iloc[0]
    rows.append({"school": s, "1979": g(1979), "1989": g(1989), "2019": g(2019), "2024": g(2024), "2025": g(2025),
                 "slope_pp_per_10y": m.params["year"] * 10, "se": m.bse["year"] * 10,
                 "lt03_1979": g(1979, "0.3未満"), "lt03_2025": g(2025, "0.3未満"),
                 "caries_1979": g(1979, "むし歯"), "caries_2025": g(2025, "むし歯")})
sl = pd.DataFrame(rows); sl.to_csv(RES / "w1_slope.csv", index=False, encoding="utf-8-sig")
print(sl.round(2).to_string())

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
for s in SCH:
    x = t[(t.school == s) & (t.year >= 1979)]
    ax[0].plot(x.year, x["1.0未満"], color=COL[s], lw=2, label=s)
    ax[1].plot(x.year, x["むし歯"], color=COL[s], lw=2, label=s)
for a in ax:
    shade_covid(a); a.set_xlim(1978, 2026)
ax[0].set_title("裸眼視力1.0未満の割合（%）"); ax[1].set_title("むし歯のある人の割合（%）")
ax[0].legend(frameon=False, fontsize=9); ax[0].set_ylim(0, 80); ax[1].set_ylim(0, 100)
ax[0].text(2021.5, 3, "2020〜23年度\n測定時期が違う", ha="center", fontsize=7.5, color="#555")
note(fig, "灰色の帯（2020〜2023年度）は測定の時期がずれたため、ほかの年と直接比べられない")
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# 年齢別（2025年度、全国）
p25, p24 = load_pref(2025), load_pref(2024)
na = p25[(p25.pref == "全国") & (p25.sex == "計")].copy()
na["0.7以上1.0未満"] = na["1.0未満"] - na["0.3未満"]
na[["age", "1.0未満", "0.3未満", "むし歯"]].to_csv(RES / "w1_age_2025.csv", index=False, encoding="utf-8-sig")
sx = p25[(p25.pref == "全国") & (p25.sex != "計")].pivot(index="age", columns="sex", values="1.0未満")
sx.to_csv(RES / "w1_age_sex_2025.csv", encoding="utf-8-sig")
print(na[["age", "1.0未満", "0.3未満"]].to_string(index=False)); print(sx)
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.bar(na.age, na["1.0未満"] - na["0.3未満"], color=LIGHT, label="0.3以上1.0未満")
ax.bar(na.age, na["0.3未満"], bottom=na["1.0未満"] - na["0.3未満"], color=BLUE, label="0.3未満")
for a_, v_ in zip(na.age, na["1.0未満"]):
    ax.text(a_, v_ + 1, f"{v_:.0f}", ha="center", fontsize=9)
ax.set_xticks(na.age, [f"{a}歳" for a in na.age], fontsize=9)
ax.set_ylabel("%"); ax.set_ylim(0, 85); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("年齢別 裸眼視力1.0未満の割合（2025年度、全国）")
note(fig)
fig.savefig(FIG / "w1_age.png"); plt.close(fig)

# 都道府県別（11歳＝小6、14歳＝中3、2025年度と2024年度）
def pref_tab(p, age):
    x = p[(p.age == age) & (p.sex == "計") & (p.pref != "全国")].set_index("pref")["1.0未満"]
    return x
out = []
for age in (11, 14):
    a25, a24 = pref_tab(p25, age), pref_tab(p24, age)
    j = pd.concat([a25.rename("y2025"), a24.rename("y2024")], axis=1)
    j["age"] = age; out.append(j)
    jj = j.dropna()
    print(age, "歳 公表あり 2025:", a25.notna().sum(), "両年:", len(jj), "相関:", round(jj.corr().iloc[0, 1], 2),
          "範囲2025:", a25.idxmin(), a25.min(), a25.idxmax(), a25.max())
pr = pd.concat(out).reset_index(names="pref"); pr.to_csv(RES / "w1_pref.csv", index=False, encoding="utf-8-sig")

j = pr[pr.age == 11].dropna(subset=["y2025"]).sort_values("y2025")
nat = p25[(p25.pref == "全国") & (p25.age == 11) & (p25.sex == "計")]["1.0未満"].iloc[0]
fig, ax = plt.subplots(figsize=(8, max(5, len(j) * 0.17)))
ax.barh(j.pref, j.y2025, color=LIGHT, label="2025年度")
ax.scatter(j.y2024, j.pref, color=ORANGE, s=14, zorder=3, label="2024年度")
ax.axvline(nat, color=INK, lw=1, ls="--"); ax.text(nat, len(j) - .3, f" 全国 {nat:.1f}%", fontsize=8.5, va="bottom")
ax.tick_params(axis="y", labelsize=8); ax.set_xlabel("%"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("11歳（小学6年）の裸眼視力1.0未満の割合（都道府県別）")
note(fig, "標本が少なく数値が伏せられた（X）県は除いた。都道府県の値は標本誤差が大きい")
fig.savefig(FIG / "w1_pref.png"); plt.close(fig)
print(j.sort_values("y2025").to_string(index=False))
