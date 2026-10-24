"""A204 特定健診の検査値（HbA1c・BMI）の都道府県差は？"""
from common import *

d = load()
d["h65p"] = d.h65; d["h60p"] = d.h65 + d.h60; d["b25p"] = d.b30 + d.b25
t = pd.DataFrame({
    "n_hba1c": d.groupby("pref", sort=False).hn.sum(),
    "crude_h65": d.groupby("pref", sort=False).h65.sum() / d.groupby("pref", sort=False).hn.sum() * 100,
    "std_h65": std_rate(d, "h65p", "hn"),
    "std_h60": std_rate(d, "h60p", "hn"),
    "crude_b25": d.groupby("pref", sort=False).b25p.sum() / d.groupby("pref", sort=False).bn.sum() * 100,
    "std_b25": std_rate(d, "b25p", "bn"),
    "std_b30": std_rate(d, "b30", "bn"),
    "share_old": d[d.age.isin(["65-69", "70-74"])].groupby("pref", sort=False).hn.sum() / d.groupby("pref", sort=False).hn.sum() * 100,
})
t = t.sort_values("std_h65", ascending=False)
t.round(3).to_csv(RES / "pref_2022.csv")
nat = d[["h65", "hn", "b25p", "bn", "h60p"]].sum()
ag = d.groupby(["sex", "age"])[["h65", "hn", "b25p", "bn"]].sum()
ag["h65r"] = ag.h65 / ag.hn * 100; ag["b25r"] = ag.b25p / ag.bn * 100
ag.round(2).to_csv(RES / "national_by_sex_age.csv")
r = np.corrcoef(t.std_b25, t.std_h65)[0, 1]
b, a = np.polyfit(t.std_b25, t.std_h65, 1)
res = t.std_h65 - (a + b * t.std_b25)
with open(RES / "summary.txt", "w") as f:
    f.write(f"national n_hba1c={nat.hn:.0f} h65={nat.h65/nat.hn*100:.2f}% h60+={nat.h60p/nat.hn*100:.2f}% n_bmi={nat.bn:.0f} b25={nat.b25p/nat.bn*100:.2f}%\n")
    f.write(f"std_h65 top5 {[(k, round(v,2)) for k,v in t.std_h65.head(5).items()]}\n")
    f.write(f"std_h65 bottom5 {[(k, round(v,2)) for k,v in t.std_h65.tail(5).items()]}\n")
    f.write(f"std_h65 max/min {t.std_h65.max()/t.std_h65.min():.2f} median {t.std_h65.median():.2f}\n")
    f.write(f"crude_h65 top5 {[(k, round(v,2)) for k,v in t.crude_h65.sort_values(ascending=False).head(5).items()]}\n")
    f.write(f"crude_h65 bottom5 {[(k, round(v,2)) for k,v in t.crude_h65.sort_values().head(5).items()]}\n")
    f.write(f"rank corr crude vs std {t.crude_h65.rank().corr(t.std_h65.rank()):.2f}\n")
    f.write(f"std_b25 top5 {[(k, round(v,2)) for k,v in t.std_b25.sort_values(ascending=False).head(5).items()]}\n")
    f.write(f"std_b25 bottom5 {[(k, round(v,2)) for k,v in t.std_b25.sort_values().head(5).items()]}\n")
    f.write(f"corr std_b25 vs std_h65 r={r:.2f} slope={b:.3f}\n")
    f.write(f"resid top {[(k, round(v,2)) for k,v in res.sort_values(ascending=False).head(5).items()]}\n")
    f.write(f"resid bottom {[(k, round(v,2)) for k,v in res.sort_values().head(5).items()]}\n")
    f.write(ag[["h65r", "b25r"]].round(2).to_string() + "\n")
    f.write(t.round(2).to_string() + "\n")

# fig1 ranking (age-adjusted)
fig, ax = plt.subplots(figsize=(7.5, 10))
s = t.std_h65.sort_values()
cols = [ORANGE if k in s.tail(5).index else (GRAY if k in s.head(5).index else BLUE) for k in s.index]
ax.barh(s.index, s.values, color=cols)
nv = nat.h65 / nat.hn * 100
ax.axvline(nv, color=INK, lw=1, ls="--"); ax.text(nv + 0.05, 0.3, f"全国 {nv:.2f}%", fontsize=9)
for i, v in enumerate(s.values): ax.text(v + 0.05, i, f"{v:.2f}", va="center", fontsize=7.5)
ax.set_xlabel("HbA1c 6.5%以上の人の割合（%、性・年齢調整、2022年度の特定健診）"); ax.tick_params(axis="y", labelsize=8.5)
ax.set_title("HbA1c 6.5%以上の割合（都道府県別）", loc="left")
save(fig, "a204_ranking.png")

# fig2 by age and sex
fig, ax = plt.subplots(figsize=(8, 4.6))
ages = ["40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74"]
for sx, col, lab in (("M", BLUE, "男性"), ("F", ORANGE, "女性")):
    v = ag.loc[sx].reindex(ages).h65r
    ax.plot(ages, v, color=col, marker="o", label=lab)
    for x, y in zip(ages, v): ax.text(x, y + 0.5, f"{y:.1f}", ha="center", fontsize=8.5, color=col)
ax.set_ylabel("HbA1c 6.5%以上の割合（%）"); ax.set_xlabel("年齢（歳）"); ax.set_ylim(0, 20)
ax.legend(frameon=False); ax.set_title("年齢・性別で見たHbA1c 6.5%以上の割合（全国）", loc="left")
save(fig, "a204_age.png")

# fig3 scatter
fig, ax = plt.subplots(figsize=(7.5, 6))
ax.scatter(t.std_b25, t.std_h65, color=BLUE, s=28)
xs = np.linspace(t.std_b25.min(), t.std_b25.max(), 10); ax.plot(xs, a + b * xs, color=GRAY, lw=1)
lab = set(t.std_h65.head(5).index) | set(t.std_h65.tail(4).index) | set(t.std_b25.sort_values().head(3).index) | set(t.std_b25.sort_values().tail(3).index) | set(res.abs().sort_values().tail(4).index)
for k in lab: ax.annotate(k, (t.std_b25[k], t.std_h65[k]), fontsize=8.5, xytext={"宮城県": (4, -12), "茨城県": (-14, 6), "鳥取県": (5, -11)}.get(k, (4, 2)), textcoords="offset points")
ax.set_xlabel("BMI 25以上の人の割合（%、性・年齢調整）"); ax.set_ylabel("HbA1c 6.5%以上の割合（%、性・年齢調整）")
ax.set_title(f"肥満の多さとHbA1c高値の多さ（相関係数 {r:.2f}）", loc="left")
save(fig, "a204_scatter.png")
print(open(RES / "summary.txt").read()[:3000])
