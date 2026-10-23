"""W2：子どもの身長の伸びは止まったか（年齢別の長期推移、出生年でそろえた成長曲線、ピークの年度）"""
from common import *

h = load_height()
h.to_csv(ROOT / "data" / "height_long.csv", index=False, encoding="utf-8-sig")
norm = h[~h.year.between(*COVID)]  # 2020〜23年度は比べないので外す

# 年齢ごとに最も高かった年度（2020〜23年度を除く）と、2025年度との差
pk = norm.loc[norm.groupby(["sex", "age"]).height.idxmax()][["sex", "age", "year", "height"]].rename(columns={"year": "peak_year", "height": "peak"})
for y in (1900, 1948, 1970, 1994, 2025):
    pk = pk.merge(h[h.year == y][["sex", "age", "height"]].rename(columns={"height": f"h{y}"}), on=["sex", "age"], how="left")
pk["d2025_peak"] = pk.h2025 - pk.peak
pk["gain_1948_1994"] = pk.h1994 - pk.h1948
pk["gain_1994_2025"] = pk.h2025 - pk.h1994
pk.to_csv(RES / "w2_peak_by_age.csv", index=False, encoding="utf-8-sig")
print(pk.round(1).to_string(index=False))

# 17歳：最高値の何cm以内に入った最初の年度
for sex in ("男", "女"):
    x = norm[(norm.sex == sex) & (norm.age == 17)].sort_values("year")
    mx = x.height.max()
    y05 = x[x.height >= mx - 0.5].year.min()
    print(sex, "17歳 最高", mx, "年度", x.loc[x.height.idxmax(), "year"], "最高-0.5cm以内に入った最初の年度", y05,
          "1948", x[x.year == 1948].height.iloc[0], "2025", x[x.year == 2025].height.iloc[0])
    # 10年ごとの伸び
    dec = x.set_index("year").height
    print("  10年の伸び:", {f"{a}-{a+10}": round(dec.get(a + 10, np.nan) - dec.get(a, np.nan), 1) for a in range(1950, 2020, 10)})

fig, ax = plt.subplots(figsize=(9, 4.4))
for sex, c in (("男", BLUE), ("女", ORANGE)):
    for age, ls in ((17, "-"), (11, "--")):
        x = h[(h.sex == sex) & (h.age == age)].sort_values("year")
        x = x.set_index("year").reindex(range(1900, 2026)).height  # 欠けた年は線を切る
        ax.plot(x.index, x.values, color=c, ls=ls, lw=1.8, label=f"{sex}子 {age}歳")
shade_covid(ax)
ax.axvspan(1939.5, 1947.5, color="#ddd", alpha=.5, lw=0); ax.text(1943.5, 145, "1940〜47年度\nデータなし", ha="center", fontsize=8, color="#555")
ax.set_ylabel("平均身長（cm）"); ax.set_xlim(1898, 2027); ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower right")
ax.set_title("平均身長の推移（1900〜2025年度）")
note(fig, "右端の灰色の帯（2020〜2023年度）は測定時期が違うため、ほかの年と直接比べられない")
fig.savefig(FIG / "w2_trend.png"); plt.close(fig)

# 出生年（年度−年齢、おおよその生まれ年）ごとの成長曲線
c = h.copy(); c["cohort"] = c.year - c.age
cohorts = [1950, 1960, 1970, 1980, 1990, 2000]
cv = c[c.cohort.isin(cohorts) & c.age.between(6, 17)]
cv.pivot_table(index=["sex", "cohort"], columns="age", values="height").to_csv(RES / "w2_cohort_curves.csv", encoding="utf-8-sig")
# 17歳（≒最終に近い身長）を出生年でそろえる
c17 = c[(c.age == 17) & ~c.year.between(*COVID)][["sex", "cohort", "height"]]
c17.to_csv(RES / "w2_height17_by_cohort.csv", index=False, encoding="utf-8-sig")
for sex in ("男", "女"):
    x = c17[c17.sex == sex]; print(sex, "17歳身長の最高の出生年", x.loc[x.height.idxmax()].to_dict())
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
cmap = plt.get_cmap("viridis")
for k, sex in enumerate(("男", "女")):
    for i, co in enumerate(cohorts):
        x = cv[(cv.sex == sex) & (cv.cohort == co)].sort_values("age")
        ax[k].plot(x.age, x.height, marker="o", ms=3, lw=1.6, color=cmap(i / (len(cohorts) - 1) * .9), label=f"{co}年ごろ生まれ")
    ax[k].set_title(f"{sex}子"); ax[k].set_xlabel("年齢"); ax[k].set_xticks(range(6, 18))
ax[0].set_ylabel("平均身長（cm）"); ax[1].legend(frameon=False, fontsize=8.5, loc="lower right")
fig.suptitle("生まれた年でそろえた成長曲線（年度−年齢でおおよその生まれ年を作った）", y=1.0)
note(fig, "ここに出した世代は2019年度までの測定で、2020〜2023年度の値は入っていない。各点は同じ子どもを追ったものではなく、毎年の標本の平均")
fig.savefig(FIG / "w2_cohort.png"); plt.close(fig)

# 年齢別：1948→1994年度と1994→2025年度の伸び
fig, ax = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
for k, sex in enumerate(("男", "女")):
    x = pk[(pk.sex == sex) & (pk.age >= 6)].sort_values("age")
    ax[k].bar(x.age - .2, x.gain_1948_1994, width=.4, color=LIGHT, label="1948→1994年度")
    ax[k].bar(x.age + .2, x.gain_1994_2025, width=.4, color=BLUE, label="1994→2025年度")
    ax[k].axhline(0, color=INK, lw=.8); ax[k].set_title(f"{sex}子"); ax[k].set_xticks(range(6, 18)); ax[k].set_xlabel("年齢")
ax[0].set_ylabel("平均身長の伸び（cm）"); ax[0].legend(frameon=False, fontsize=9)
fig.suptitle("戦後の約半世紀と、その後の約30年の伸び", y=1.0)
note(fig)
fig.savefig(FIG / "w2_gain.png"); plt.close(fig)
