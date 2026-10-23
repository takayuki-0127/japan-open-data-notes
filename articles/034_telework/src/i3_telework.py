"""I3：テレワークをしたことがある人は、2019年→2025年でどれくらい増えたか。年代・性別・年収・都道府県で、誰がしているか"""
from common import *
import statsmodels.formula.api as smf
R1 = RAW / "r1_kosein.xls"; T = "テレワークをしたことがある"
t25, t19 = read_table("構35表"), read_table("構33表", path=R1)
AG = ["２０～２９歳", "３０～３９歳", "４０～４９歳", "５０～５９歳", "６０～６４歳", "６５～６９歳", "７０～７９歳"]
AGL = ["20代", "30代", "40代", "50代", "60〜64歳", "65〜69歳", "70代"]
def age(tb, sex): a = tb[(tb.section == "本人の性別・年齢") & (tb.sex == sex)].drop_duplicates("label").set_index("label"); return a.loc[AG, T].astype(float).values
A = pd.DataFrame({"age": AGL, "all_2019": age(t19, "男女計"), "all_2025": age(t25, "男女計"), "men_2025": age(t25, "男性"), "women_2025": age(t25, "女性"),
                  "men_2019": age(t19, "男性"), "women_2019": age(t19, "女性")})
A.to_csv(RES / "i3_age.csv", index=False, encoding="utf-8-sig"); print(A)
inc = t25[t25.section == "所属世帯年収"][["label", T]]; city = pd.concat([t19[t19.section == "都市区分"][["label", T]].set_index("label")[T].rename("2019"), t25[t25.section == "都市区分"][["label", T]].set_index("label")[T].rename("2025")], axis=1)
print(inc, city)
# 都道府県：2019年と2025年、情報通信業で働く人の割合
p = pd.DataFrame({"y2019": t19[t19.section == "都道府県"].set_index("label")[T], "y2025": t25[t25.section == "都道府県"].set_index("label")[T]}).reset_index().rename(columns={"index": "label"})
p["pref"] = p.label.str[2:]
h = pd.read_csv(RAW / "SSDSE-E-2026.csv", encoding="cp932", header=None, nrows=1).iloc[0]
e = pd.read_csv(RAW / "SSDSE-E-2026.csv", encoding="cp932", header=None, skiprows=3); e.columns = list(h); e = e.rename(columns={"Prefecture": "pref"})
e["ict"] = e.C220839 / e.C2208 * 100; e["old"] = e.A1303 / e.A1101 * 100
p = p.merge(e[["pref", "ict", "old"]], on="pref"); assert len(p) == 47
m_all = smf.ols("y2025 ~ ict", p).fit(cov_type="HC3"); m_ex = smf.ols("y2025 ~ ict", p[p.pref != "東京都"]).fit(cov_type="HC3")
m_old = smf.ols("y2025 ~ ict + old", p[p.pref != "東京都"]).fit(cov_type="HC3")
print(m_all.params, m_all.rsquared, m_ex.params, m_ex.pvalues, m_ex.rsquared, m_old.params, m_old.pvalues)
p.round(2).sort_values("y2025").to_csv(RES / "i3_pref.csv", index=False, encoding="utf-8-sig")
reason = {}
for y, tb in [("2019", read_table("構35表", path=R1)), ("2025", read_table("構37表"))]:
    reason[y] = tb[tb.label == "男女計："].iloc[0].drop(["label", "section", "sex"]).astype(float)
reason = pd.DataFrame(reason); reason.to_csv(RES / "i3_reason.csv", encoding="utf-8-sig"); print(reason)
want = {y: float(tb[tb.label == "男女計："]["希望する"].iloc[0]) for y, tb in [("2019", read_table("構34表", path=R1)), ("2025", read_table("構36表"))]}
s = {"all_2019": float(t19[t19.label == "男女計："][T].iloc[0]), "all_2025": float(t25[t25.label == "男女計："][T].iloc[0]),
     "home_2025": float(t25[t25.label == "男女計："]["在宅"].iloc[0]), "men_2025": float(t25[t25.label == "男性："][T].iloc[0]), "women_2025": float(t25[t25.label == "女性："][T].iloc[0]),
     "pref_max": p.loc[p.y2025.idxmax(), "pref"], "pref_max_v": p.y2025.max(), "pref_min": p.loc[p.y2025.idxmin(), "pref"], "pref_min_v": p.y2025.min(),
     "pref_2019_max": p.y2019.max(), "pref_median_2025": p.y2025.median(), "corr_19_25": p[["y2019", "y2025"]].corr().iloc[0, 1],
     "b_ict_all": m_all.params.ict, "r2_all": m_all.rsquared, "b_ict_exTokyo": m_ex.params.ict, "p_ict_exTokyo": m_ex.pvalues.ict, "r2_exTokyo": m_ex.rsquared,
     "b_ict_old_exT": m_old.params.ict, "b_old_exT": m_old.params.old, "p_old_exT": m_old.pvalues.old, "want_2019": want["2019"], "want_2025": want["2025"]}
pd.Series(s).to_csv(RES / "i3_summary.csv", header=["value"]); print(pd.Series(s))

S2 = SOURCE.replace("令和7年", "令和元年・令和7年")
fig, ax = plt.subplots(figsize=(9, 4.2)); x = np.arange(len(AGL)); w = 0.27
ax.bar(x - w, A.all_2019, w, color=GRAY, label="2019年（男女計）"); ax.bar(x, A.men_2025, w, color=BLUE, label="2025年 男性"); ax.bar(x + w, A.women_2025, w, color=ORANGE, label="2025年 女性")
ax.set_xticks(x, AGL); ax.set_ylabel("テレワークをしたことがある人（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"テレワーク経験は2019年の{s['all_2019']:.1f}%から2025年は{s['all_2025']:.1f}%に", loc="left")
fig.text(0.01, -0.05, S2 + "\n（企業等に勤務し、ネットを使っている人のうち）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "i3_age.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 3.8))
labs = inc.label.str.replace("^200万円未満", "〜200", regex=True).str.replace("～", "〜").str.replace("万円未満", "").str.replace("万円以上", "+")
ax.bar(labs, inc[T], color=BLUE)
for i, v in enumerate(inc[T]): ax.text(i, v + 1, f"{v:.0f}", ha="center", fontsize=9)
ax.set_ylim(0, 70); ax.set_xlabel("世帯年収（万円）"); ax.set_ylabel("テレワーク経験（%）"); ax.tick_params(axis="x", labelsize=8.5)
ax.set_title("世帯年収が高いほど、テレワークをしたことがある人が多い（2025年）", loc="left")
fig.text(0.01, -0.06, SOURCE, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "i3_income.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.5, 4.6))
ax.scatter(p.ict, p.y2025, s=24, color=LIGHT, edgecolor=BLUE, lw=0.6)
xx = np.linspace(p[p.pref != "東京都"].ict.min(), p[p.pref != "東京都"].ict.max(), 20); ax.plot(xx, m_ex.params.Intercept + m_ex.params.ict * xx, color=ORANGE, label="東京都を除いた回帰")
for _, r in p[p.pref.isin(["東京都", "神奈川県", "千葉県", "埼玉県", "大阪府", "福岡県", "愛知県", "青森県", "宮崎県"]) | (p.y2025 == p.y2025.min())].iterrows():
    ax.annotate(r.pref, (r.ict, r.y2025), xytext=(4, 2), textcoords="offset points", fontsize=8.5)
ax.set_xlabel("情報通信業で働く人の割合（%、民営事業所の従業者、2021年）"); ax.set_ylabel("テレワーク経験（%、2025年）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("情報通信業が多い県ほど多い。ただし高齢化をそろえると、はっきりしなくなる", loc="left")
fig.text(0.01, -0.04, SOURCE + "、独立行政法人統計センター「SSDSE-E-2026」をもとに作成者が加工して作成", fontsize=6.8, color="#8a8984"); fig.savefig(FIG / "i3_pref.png"); plt.close(fig)
