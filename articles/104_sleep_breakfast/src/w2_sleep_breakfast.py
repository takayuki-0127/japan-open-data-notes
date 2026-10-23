"""W2：睡眠時間6時間未満の人の割合（2009〜2024年）と朝食欠食率（2003〜2017年）の世代差"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

sl = load_sleep()
sl = sl[sl.age.isin(AGES)]
n = sl[sl.cat == "n_total"][["year", "sex", "age", "n"]].rename(columns={"n": "n_resp"})
short = (sl[sl.cat.isin(["lt5", "5-6"])].groupby(["year", "sex", "age"]).pct.sum().rename("lt6_pct").reset_index()
         .merge(sl[sl.cat == "lt5"][["year", "sex", "age", "pct"]].rename(columns={"pct": "lt5_pct"}), on=["year", "sex", "age"])
         .merge(sl[sl.cat.isin(["7-8", "8-9", "9+"])].groupby(["year", "sex", "age"]).pct.sum().rename("ge7_pct").reset_index(), on=["year", "sex", "age"])
         .merge(n, on=["year", "sex", "age"]))
short.to_csv(RES / "w2_sleep_by_sex_age.csv", index=False, encoding="utf-8-sig")

# 年齢構成をそろえた割合（全年の回答者数を合わせた年齢構成で直接法）
wts = short.groupby(["sex", "age"]).n_resp.sum()
def std(d, sex, col):
    w = wts.loc[sex].reindex(d.age)
    return np.average(d[col], weights=w.values)
stdz = pd.DataFrame([{"year": y, "sex": sex, "lt6_std": std(d, sex, "lt6_pct"), "lt5_std": std(d, sex, "lt5_pct"),
                      "ge7_std": std(d, sex, "ge7_pct"), "n": d.n_resp.sum()}
                     for (y, sex), d in short.groupby(["year", "sex"])])
stdz.to_csv(RES / "w2_sleep_standardized.csv", index=False, encoding="utf-8-sig")
print(stdz.round(1).to_string())
tr = []
for sex in ["male", "female"]:
    z = stdz[stdz.sex == sex]
    m = sm.OLS(z.lt6_std.values, sm.add_constant(z.year.values - 2009)).fit(cov_type="HAC", cov_kwds={"maxlags": 1})
    tr.append((sex, m.params[1] * 10, m.bse[1] * 10))
    # 年齢階級ごと：2009〜11年平均 → 2022〜24年平均
print(pd.DataFrame(tr, columns=["sex", "slope_pt_per10y", "se"]).round(2))
pd.DataFrame(tr, columns=["sex", "slope_pt_per10y", "se"]).to_csv(RES / "w2_sleep_trend.csv", index=False, encoding="utf-8-sig")
pa = short.assign(per=np.where(short.year <= 2011, "2009-11", np.where(short.year >= 2022, "2022-24", None))).dropna(subset=["per"])
pa = pa.groupby(["sex", "age", "per"]).lt6_pct.mean().unstack()
pa["chg"] = pa["2022-24"] - pa["2009-11"]
pa.to_csv(RES / "w2_sleep_age_periods.csv", encoding="utf-8-sig")
print(pa.round(1).to_string())

# --- 図1：6時間未満の割合の推移（年齢構成をそろえた値）＋年齢階級
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), sharey=True)
for ax, sex, lab, c in [(axes[0], "male", "男性", BLUE), (axes[1], "female", "女性", ORANGE)]:
    d = short[short.sex == sex]
    labs = []
    for a, cc in zip(AGES, AGE_COLORS):
        z = d[d.age == a].set_index("year").lt6_pct
        ax.plot(z.index, z.values, "-o", color=cc, ms=3, lw=1.6)
        labs.append([z.loc[2024], a, cc])
    labs.sort()
    for k in range(1, len(labs)):
        if labs[k][0] - labs[k - 1][0] < 2.4:
            labs[k][0] = labs[k - 1][0] + 2.4
    for v, a, cc in labs:
        ax.text(2024.5, v, a.replace("70+", "70歳以上").replace("-", "〜") + ("" if a == "70+" else "歳"), color=cc, fontsize=8.5, va="center")
    zz = stdz[stdz.sex == sex].set_index("year").lt6_std
    ax.plot(zz.index, zz.values, color=INK, lw=2.6, label="20歳以上（年齢構成をそろえた値）")
    ax.set_title(lab, loc="left"); ax.set_xlim(2008, 2028); ax.set_ylim(10, 62)
    ax.axvspan(2019.5, 2021.5, color="#eeeeee")
axes[0].set_ylabel("睡眠が6時間未満の人の割合（%）")
axes[0].legend(frameon=False, fontsize=8.5, loc="lower left")
fig.suptitle("1日の平均睡眠時間が6時間未満の人の割合（2009〜2024年、11回分）", x=0.02, ha="left", fontsize=13)
note(fig, SOURCE + "　※2012・2013・2016年は睡眠時間の表がなく、2020・21年は調査なし")
fig.savefig(FIG / "w2_sleep_trend.png"); plt.close(fig)

# --- 図2：2022〜24年の年齢・男女別の分布
cats = ["lt5", "5-6", "6-7", "7-8", "8-9", "9+"]
cl = {"lt5": "5時間未満", "5-6": "5〜6時間", "6-7": "6〜7時間", "7-8": "7〜8時間", "8-9": "8〜9時間", "9+": "9時間以上"}
cc = ["#b8401a", "#eb6834", "#d9d6cf", "#a9c9ef", "#2a78d6", "#1b4f99"]
rec = sl[(sl.year >= 2022) & sl.cat.isin(cats)].groupby(["sex", "age", "cat"]).pct.mean().unstack()[cats]
rec.to_csv(RES / "w2_sleep_dist_2022_24.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(9.6, 5))
labels, ypos = [], []
y = 0
for sex, lab in [("male", "男性"), ("female", "女性")]:
    for a in AGES:
        left = 0
        for c, col in zip(cats, cc):
            v = rec.loc[(sex, a), c]
            ax.barh(y, v, left=left, color=col, height=0.75)
            if c in ("lt5", "5-6") and v > 4:
                ax.text(left + v / 2, y, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white")
            left += v
        labels.append(f"{lab} " + a.replace("70+", "70歳以上").replace("-", "〜") + ("" if a == "70+" else "歳")); ypos.append(y)
        y += 1
    y += 0.6
ax.set_yticks(ypos, labels); ax.invert_yaxis(); ax.set_xlim(0, 100)
ax.set_xlabel("割合（%、2022〜24年の平均）")
for c, col in zip(cats, cc):
    ax.bar(0, 0, color=col, label=cl[c])
ax.legend(ncol=6, frameon=False, fontsize=8.5, loc="upper left", bbox_to_anchor=(0, 1.08))
ax.set_title("1日の平均睡眠時間の分布（年齢・男女別）", loc="left", pad=24)
note(fig)
fig.savefig(FIG / "w2_sleep_age.png"); plt.close(fig)

# --- 朝食欠食率（2003〜2017年）：年齢階級別と、同じ世代を10年後に追う
b = load_breakfast()
b.to_csv(RES / "w2_breakfast_by_sex_age.csv", index=False, encoding="utf-8-sig")
bb = b[b.age.isin(AGES)]
coh = []
for sex in ["male", "female"]:
    for y0 in range(2003, 2008):
        for i, a in enumerate(AGES[:-1]):
            v0 = bb[(bb.sex == sex) & (bb.year == y0) & (bb.age == a)].skip_pct.iloc[0]
            v1 = bb[(bb.sex == sex) & (bb.year == y0 + 10) & (bb.age == AGES[i + 1])].skip_pct.iloc[0]
            same_age_later = bb[(bb.sex == sex) & (bb.year == y0 + 10) & (bb.age == a)].skip_pct.iloc[0]
            coh.append((sex, y0, a, AGES[i + 1], v0, v1, same_age_later))
coh = pd.DataFrame(coh, columns=["sex", "year0", "age0", "age10", "skip_year0", "skip_10y_later_same_cohort", "skip_same_age_10y_later"])
cs = coh.groupby(["sex", "age0"])[["skip_year0", "skip_10y_later_same_cohort", "skip_same_age_10y_later"]].mean()
cs.to_csv(RES / "w2_breakfast_cohort.csv", encoding="utf-8-sig")
print(cs.round(1).to_string())
bp = bb.assign(per=np.where(bb.year <= 2005, "2003-05", np.where(bb.year >= 2015, "2015-17", None))).dropna(subset=["per"])
bp = bp.groupby(["sex", "age", "per"]).skip_pct.mean().unstack()
bp["chg"] = bp["2015-17"] - bp["2003-05"]
bp.to_csv(RES / "w2_breakfast_periods.csv", encoding="utf-8-sig")
print(bp.round(1).to_string())

fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4), sharey=True)
x = np.arange(len(AGES) - 1)
for ax, sex, lab in [(axes[0], "male", "男性"), (axes[1], "female", "女性")]:
    d = cs.loc[sex].reindex(AGES[:-1])
    ax.bar(x - 0.27, d.skip_year0, 0.27, color=LIGHT, label="2003〜07年のその年代")
    ax.bar(x, d.skip_10y_later_same_cohort, 0.27, color=BLUE if sex == "male" else ORANGE, label="同じ世代の10年後（1つ上の年代）")
    ax.bar(x + 0.27, d.skip_same_age_10y_later, 0.27, color=GRAY, label="10年後（2013〜17年）の同じ年代")
    ax.set_xticks(x, [f"{a[:2]}代→{int(a[:2]) + 10}代" for a in AGES[:-1]], fontsize=9)
    ax.set_title(lab, loc="left")
axes[0].set_ylabel("朝食欠食率（%、5年分の平均）")
axes[1].legend(frameon=False, fontsize=8.5, loc="upper right")
fig.suptitle("朝食を抜く人は、年をとっても抜き続けるか（2003〜2017年）", x=0.02, ha="left", fontsize=13)
note(fig, SOURCE + "\n※朝食欠食率の年次推移表を使用。2003→2013年、…、2007→2017年の5組の平均", y=-0.01)
fig.savefig(FIG / "w2_breakfast.png"); plt.close(fig)
