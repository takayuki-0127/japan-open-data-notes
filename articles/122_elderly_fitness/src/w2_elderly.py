"""W2：70代の体力は20年前の60代並みか（65〜79歳、1998〜2025年度、年齢×年度と生まれ年）"""
from common import *
import statsmodels.formula.api as smf

d = load()
e = d[d.group == "高齢者"].copy()
AGES = ["65-69", "70-74", "75-79"]
LOW = {"10m障害物歩行"}               # 小さいほど良い
ITEMS = ["握力", "上体起こし", "長座体前屈", "開眼片足立ち", "10m障害物歩行", "6分間歩行", "合計点"]
tot = e[e["item"] == "合計点"].pivot_table(index="year", columns=["age", "sex"], values="value")
tot.to_csv(RES / "w2_total_by_age_year.csv", encoding="utf-8-sig")

# 1) 同じ年齢の変化（1998→2025年度）と、何年前の65〜69歳と同じか
rows = []
for s in ("男", "女"):
    for k, a in enumerate(AGES):
        v = tot[(a, s)]
        r = {"age": a, "sex": s, "1998": v[1998], "2005": v[2005], "2019": v[2019], "2025": v[2025],
             "chg_1998_2025": v[2025] - v[1998], "slope_per10y_1998_2019": np.polyfit(v.loc[:2019].index, v.loc[:2019].values, 1)[0] * 10}
        if k > 0:
            # 2025年度のこの年齢の点数に、5歳若い区分が初めて届いた年度（線形補間）
            y65 = tot[(AGES[k - 1], s)]
            target = v[2025]
            hit = None
            for y0, y1 in zip(y65.index[:-1], y65.index[1:]):
                if y65[y0] < target <= y65[y1]:
                    hit = y0 + (target - y65[y0]) / (y65[y1] - y65[y0]) * (y1 - y0); break
            if hit is None and y65.iloc[0] >= target:
                hit = np.nan
            r["year_younger_group_reached"] = hit
        rows.append(r)
same = pd.DataFrame(rows)
same.to_csv(RES / "w2_same_age.csv", index=False, encoding="utf-8-sig")
print(same.round(2).to_string())

# 2) 種目ごと：2025年度の70〜74歳 vs 2005年度の65〜69歳・70〜74歳
p = e.pivot_table(index=["item", "sex"], columns=["age", "year"], values="value")
cmp = []
for it in ITEMS:
    for s in ("男", "女"):
        now70, old65, old70 = p.loc[(it, s), ("70-74", 2025)], p.loc[(it, s), ("65-69", 2005)], p.loc[(it, s), ("70-74", 2005)]
        sign = -1 if it in LOW else 1
        cmp.append({"item": it, "sex": s, "70-74_2025": now70, "65-69_2005": old65, "70-74_2005": old70,
                    "vs_65-69_2005_pct": sign * (now70 / old65 - 1) * 100, "vs_70-74_2005_pct": sign * (now70 / old70 - 1) * 100})
cmp = pd.DataFrame(cmp)
cmp.to_csv(RES / "w2_items_2025_vs_2005.csv", index=False, encoding="utf-8-sig")
print(cmp.round(2).to_string())

# 3) 生まれ年でそろえる：t年度の65〜69歳 → t+5年度の70〜74歳 → t+10年度の75〜79歳
lo = tot.stack(level=[0, 1]).rename("score").reset_index()
lo["a0"] = lo["age"].str[:2].astype(int)
lo["cohort"] = lo["year"] - lo["a0"]          # 年齢区分の始めの歳で生まれ年を表す（例：2025年度の65〜69歳→1956〜60年生まれ）
lo.to_csv(RES / "w2_cohort_long.csv", index=False, encoding="utf-8-sig")
dec = []
for s in ("男", "女"):
    for t in range(1998, 2016):
        g = lo[(lo.sex == s)]
        a1 = g[(g.year == t) & (g.age == "65-69")].score
        a3 = g[(g.year == t + 10) & (g.age == "75-79")].score
        c1 = g[(g.year == t) & (g.age == "75-79")].score
        if len(a1) and len(a3):
            dec.append({"sex": s, "start_year": t, "cohort_65_69_in": t, "within_cohort_10y": a3.iloc[0] - a1.iloc[0],
                        "cross_section_gap_same_year": c1.iloc[0] - a1.iloc[0]})
dec = pd.DataFrame(dec)
dec["difference"] = dec.within_cohort_10y - dec.cross_section_gap_same_year
dec.to_csv(RES / "w2_cohort_vs_cross.csv", index=False, encoding="utf-8-sig")
print(dec.groupby("sex")[["within_cohort_10y", "cross_section_gap_same_year", "difference"]].mean().round(2))

# 4) 簡単な年齢・時代・世代の比較：年齢×男女の固定効果に、年度（時代）か生まれ年（世代）の直線を足す
fits = []
for s in ("男", "女"):
    g = lo[lo.sex == s].copy()
    g["post2019"] = (g.year >= 2020).astype(int)
    # 注：年齢の固定効果があると「年度の直線」と「生まれ年の直線」は同じ当てはまりになり区別できない（APCの識別問題）
    for name, f in [("年齢＋年度の直線（＝年齢＋生まれ年の直線）", "score ~ C(age) + year"), ("年齢＋年度の固定効果", "score ~ C(age) + C(year)")]:
        m = smf.ols(f, g).fit()
        coef = m.params.get("year", m.params.get("cohort", np.nan))
        se = m.bse.get("year", m.bse.get("cohort", np.nan))
        fits.append({"sex": s, "model": name, "slope_per10y": coef * 10, "se_per10y": se * 10, "r2": m.rsquared, "aic": m.aic})
    # 年度の固定効果のもとで、年齢区分ごとの年度の傾きが違うか（違いが世代の効きを示す）
    m = smf.ols("score ~ C(age) * year", g[g.year <= 2019]).fit()
    for a in AGES:
        sl = m.params["year"] + (m.params.get(f"C(age)[T.{a}]:year", 0))
        fits.append({"sex": s, "model": f"年齢別の傾き {a}（〜2019）", "slope_per10y": sl * 10, "se_per10y": np.nan, "r2": m.rsquared, "aic": m.aic})
fits = pd.DataFrame(fits)
fits.to_csv(RES / "w2_apc_simple.csv", index=False, encoding="utf-8-sig")
print(fits.round(3).to_string())

# ---- 図1：年齢区分ごとの合計点の推移
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True)
for ax, s in zip(axes, ("男", "女")):
    for a, c in zip(AGES, [BLUE, ORANGE, GREEN]):
        v = tot[(a, s)]
        ax.plot(v.index, v.values, "-", color=c, lw=1.8, label=f"{a.replace('-', '〜')}歳")
    ax.axhline(tot[("65-69", s)][2005], color=BLUE, ls=":", lw=0.9)
    ax.text(1998.5, tot[("65-69", s)][2005] + 0.3, "2005年度の65〜69歳", fontsize=8, color=BLUE)
    ax.set_title(f"{s}性"); ax.set_xlim(1997, 2026)
axes[0].set_ylabel("新体力テストの合計点（高齢者）")
axes[1].legend(frameon=False, fontsize=9, loc="lower right")
fig.suptitle("65〜79歳の合計点（1998〜2025年度）", y=1.02)
note(fig)
fig.savefig(FIG / "w2_total.png"); plt.close(fig)

# ---- 図2：種目別に2025年度の70〜74歳を2005年度の65〜69歳と比べる
fig, ax = plt.subplots(figsize=(8.4, 4.4))
lab = [i for i in ITEMS]
yy = np.arange(len(lab))
for k, (s, c) in enumerate([("男", BLUE), ("女", ORANGE)]):
    v = cmp[cmp.sex == s].set_index("item").loc[lab, "vs_65-69_2005_pct"]
    ax.barh(yy + (k - 0.5) * 0.38, v.values, height=0.36, color=c, label=f"{s}性")
    for yi, x in zip(yy, v.values):
        ax.text(x + (0.4 if x >= 0 else -0.4), yi + (k - 0.5) * 0.38, f"{x:+.1f}%", va="center", ha="left" if x >= 0 else "right", fontsize=8)
ax.axvline(0, color=INK, lw=0.8)
ax.set_yticks(yy); ax.set_yticklabels(lab); ax.invert_yaxis()
ax.set_xlabel("2025年度の70〜74歳 ÷ 2005年度の65〜69歳 −1（%、右ほど良い）")
ax.set_title("2025年度の70〜74歳は、20年前の65〜69歳と比べてどうか")
ax.legend(frameon=False, fontsize=9, loc="lower right")
xm = np.abs(cmp["vs_65-69_2005_pct"]).max() + 3
ax.set_xlim(-xm, xm)
note(fig, "10m障害物歩行は時間が短いほど良いので符号を逆にした")
fig.savefig(FIG / "w2_items.png"); plt.close(fig)

# ---- 図3：生まれ年でそろえる
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2), sharey=True)
for ax, s in zip(axes, ("男", "女")):
    g = lo[lo.sex == s]
    for t, c in zip([1998, 2003, 2008, 2013], [LIGHT, BLUE, "#1c4f8f", INK]):
        pts = [(a, g[(g.year == t + 5 * i) & (g.age == a)].score) for i, a in enumerate(AGES)]
        xs = [i for i, (a, v) in enumerate(pts) if len(v)]
        ys = [v.iloc[0] for a, v in pts if len(v)]
        ax.plot(xs, ys, "-o", color=c, lw=1.8, ms=4, label=f"{t - 69}〜{t - 65}年生まれ")
    cs = g[g.year == 2025].set_index("age").loc[AGES, "score"]
    ax.plot(range(3), cs.values, "--s", color=ORANGE, ms=4, lw=1.4, label="2025年度の年齢差（横断）")
    ax.set_xticks(range(3)); ax.set_xticklabels(["65〜69歳", "70〜74歳", "75〜79歳"])
    ax.set_title(f"{s}性")
axes[0].set_ylabel("合計点")
axes[1].legend(frameon=False, fontsize=8, loc="lower left")
fig.suptitle("同じ生まれ年の人を5年ごとに追う", y=1.02)
note(fig, "毎年ちがう人を調べた結果を、生まれ年でつないだもの")
fig.savefig(FIG / "w2_cohort.png"); plt.close(fig)
