"""W1：就業者の増減を「男女×年齢」に分け、さらに人口の変化と就業率の変化に分ける"""
from common import *

AG = [a for a in AGE5 if a not in ("65-69", "70-74", "75+")] + ["65+"]   # 1968年から通して使える区分
df = load_emp_pop()
d = df[df.sex.isin(["男", "女"]) & df.age.isin(AG)].copy()
d["old"] = d.age.eq("65+")
d["grp"] = d.sex + np.where(d.old, "65歳以上", "15〜64歳")
GRP = ["女15〜64歳", "女65歳以上", "男15〜64歳", "男65歳以上"]
COL = {"女15〜64歳": ORANGE, "女65歳以上": "#f2a27f", "男15〜64歳": BLUE, "男65歳以上": LIGHT}
tot = df[(df.sex == "男女計") & df.age.isin(AG)].groupby("year")[["pop", "emp"]].sum()
tot["rate"] = tot.emp / tot["pop"] * 100
tot.round(1).to_csv(RES / "w1_total.csv")

# 1) グループ別の就業者数の推移
g = d.groupby(["year", "grp"]).emp.sum().unstack()[GRP]
g.to_csv(RES / "w1_by_group.csv")

# 2) 期間ごとの増減と、人口要因・就業率要因（男女×5歳階級で計算して合計）
def decomp(y0, y1):
    a = d[d.year == y0].set_index(["sex", "age"]); b = d[d.year == y1].set_index(["sex", "age"])
    r0, r1 = a.emp / a["pop"], b.emp / b["pop"]
    popeff = (b["pop"] - a["pop"]) * (r0 + r1) / 2
    rateff = (r1 - r0) * (a["pop"] + b["pop"]) / 2
    x = pd.DataFrame({"grp": a.grp, "change": b.emp - a.emp, "pop_effect": popeff, "rate_effect": rateff})
    out = x.groupby("grp")[["change", "pop_effect", "rate_effect"]].sum().reindex(GRP)
    out.loc["計"] = out.sum()
    out.insert(0, "period", f"{y0}-{y1}")
    return out

PER = [(1990, 2000), (2000, 2012), (2012, 2019), (2019, 2025), (2012, 2025)]
dec = pd.concat([decomp(*p) for p in PER])
dec.round(1).to_csv(RES / "w1_decomposition.csv")
print(dec.round(0))
print(tot.loc[[1990, 1997, 2000, 2012, 2019, 2025]].round(1))

# 女性の年齢別就業率 2012 vs 2025 と、65歳以上の内訳
fe = df[(df.sex == "女") & df.age.isin(AGE5)].copy(); fe["rate"] = fe.emp / fe["pop"] * 100
rt = fe.pivot(index="age", columns="year", values="rate").reindex(AGE5)
ma = df[(df.sex == "男") & df.age.isin(AGE5)].copy(); ma["rate"] = ma.emp / ma["pop"] * 100
rm = ma.pivot(index="age", columns="year", values="rate").reindex(AGE5)
pd.DataFrame({"女2002": rt[2002], "女2012": rt[2012], "女2025": rt[2025], "男2012": rm[2012], "男2025": rm[2025]}).round(1).to_csv(RES / "w1_rate_by_age.csv")
print(pd.DataFrame({"女2012": rt[2012], "女2025": rt[2025], "男2012": rm[2012], "男2025": rm[2025]}).round(1))
old = df[(df.sex == "男女計") & df.age.isin(["65-69", "70-74", "75+"]) & df.year.isin([2012, 2025])].pivot(index="age", columns="year", values="emp")
print(old)

# --- 図1：グループ別の推移（積み上げ）
fig, ax = plt.subplots(figsize=(8, 4.6))
gg = g.loc[1973:]
ax.stackplot(gg.index, [gg[c] for c in GRP], labels=GRP, colors=[COL[c] for c in GRP], alpha=.95)
ax.set_title("就業者数の内訳（男女×年齢、万人）")
ax.set_ylabel("万人"); ax.legend(loc="upper left", fontsize=9, ncol=2, frameon=False)
ax.set_ylim(0, 7600); ax.axvline(2012, color=GRAY, lw=.8, ls="--")
save(fig, "w1_groups.png")

# --- 図2：期間ごとの増減を4グループに分ける
fig, ax = plt.subplots(figsize=(8, 4.6))
pp = [f"{a}-{b}" for a, b in PER[:4]]
x = np.arange(len(pp))
bottom_p = np.zeros(len(pp)); bottom_n = np.zeros(len(pp))
for c in GRP:
    v = np.array([dec[(dec.period == p)].loc[c, "change"] for p in pp])
    b = np.where(v >= 0, bottom_p, bottom_n)
    ax.bar(x, v, bottom=b, color=COL[c], label=c, width=.6)
    bottom_p += np.where(v >= 0, v, 0); bottom_n += np.where(v < 0, v, 0)
tt = [dec[(dec.period == p)].loc["計", "change"] for p in pp]
ax.scatter(x, tt, color=INK, zorder=5, label="合計")
for i, t in enumerate(tt):
    ax.text(i + .33, t, f"{t:+.0f}", va="center", fontsize=10)
ax.axhline(0, color=INK, lw=.8)
ax.set_xticks(x, [p.replace("-", "→") for p in pp]); ax.set_ylabel("万人")
ax.set_title("就業者の増減を男女×年齢に分ける")
ax.legend(fontsize=9, frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "w1_contrib.png")

# --- 図3：2012→2025 の人口要因と就業率要因
z = dec[dec.period == "2012-2025"].loc[GRP]
fig, ax = plt.subplots(figsize=(8, 4.4))
y = np.arange(len(GRP))
ax.barh(y - .18, z.pop_effect, .36, color=GRAY, label="人口の変化による分")
ax.barh(y + .18, z.rate_effect, .36, color=GREEN, label="就業率の変化による分")
for i, c in enumerate(GRP):
    ax.text(z.loc[c, "pop_effect"] + (6 if z.loc[c, "pop_effect"] >= 0 else -6), i - .18, f"{z.loc[c,'pop_effect']:+.0f}", va="center", ha="left" if z.loc[c, "pop_effect"] >= 0 else "right", fontsize=9)
    ax.text(z.loc[c, "rate_effect"] + 6, i + .18, f"{z.loc[c,'rate_effect']:+.0f}", va="center", fontsize=9)
ax.set_yticks(y, GRP); ax.invert_yaxis(); ax.axvline(0, color=INK, lw=.8)
ax.set_xlim(-330, 620); ax.set_xlabel("万人（2012→2025年）"); ax.set_title("増えた理由：人口か、働く人の割合か")
ax.legend(frameon=False, fontsize=9, loc="lower right")
save(fig, "w1_decomp.png")
