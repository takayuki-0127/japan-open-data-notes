"""年齢別の1人あたり医療費のカーブは、どう変わったか（国民医療費 2008・2013・2018・2023年度）"""
from common import *

d = load("medical_cost_by_age.csv")  # oku：国民医療費（億円）、percap_k：人口一人当たり（千円）
d = d[d.age != "総数"].copy()
d["pop"] = d.oku * 1e8 / (d.percap_k * 1e3)  # 人口（推計に使われた人数を逆算）
# 85歳以上にまとめる（2018・2023は85〜89と90以上を合算）
d["age2"] = d.age.replace({"85-89": "85+", "90+": "85+"})
g = d.groupby(["year", "sex", "age2"], sort=False).agg(oku=("oku", "sum"), pop=("pop", "sum")).reset_index()
g["percap"] = g.oku * 1e8 / g["pop"] / 1e3  # 千円
AGES = list(dict.fromkeys(g[g.year == 2008].age2))
g["ai"] = g.age2.map({a: i for i, a in enumerate(AGES)})
g.to_csv(RES / "a159_percap_85plus.csv", index=False, encoding="utf-8")
A = g[g.sex == "all"].pivot(index="age2", columns="year", values="percap").loc[AGES]
O = g[g.sex == "all"].pivot(index="age2", columns="year", values="oku").loc[AGES]
P = g[g.sex == "all"].pivot(index="age2", columns="year", values="pop").loc[AGES]
tot = d[(d.sex == "all")].groupby("year").agg(oku=("oku", "sum"), pop=("pop", "sum"))
L = ["国民医療費（年齢階級の合計、兆円）: " + "、".join(f"{y} {v/1e4:.1f}" for y, v in tot.oku.items()),
     "人口一人当たり（千円）: " + "、".join(f"{y} {o*1e8/p/1e3:.1f}" for y, (o, p) in tot.iterrows())]
L.append("年齢別 一人当たり（千円）:\n" + A.round(1).to_string())
grow = (A[2023] / A[2008] - 1) * 100
L.append("2008→2023 一人当たりの伸び（%）:\n" + grow.round(1).to_string())
for y in [2008, 2013, 2018, 2023]:
    o = O[y]; p = P[y]
    s65 = o[AGES[13:]].sum() / o.sum(); s75 = o[AGES[15:]].sum() / o.sum(); p65 = p[AGES[13:]].sum() / p.sum()
    L.append(f"{y}: 65歳以上が医療費に占める割合 {s65:.1%}（人口の {p65:.1%}）、75歳以上 {s75:.1%}、65歳以上の一人当たり/65歳未満 {o[AGES[13:]].sum()/p[AGES[13:]].sum()/(o[AGES[:13]].sum()/p[AGES[:13]].sum()):.2f}倍")
# 伸びを「年齢ごとの単価の伸び」と「人口構成の変化」に分ける（2008→2023）
c08 = (O[2008].sum()); c23 = O[2023].sum()
fixed_pop = (A[2023] * 1e3 * P[2008]).sum() / 1e8  # 2008年の人口構成・2023年の単価
L.append(f"要因分解 2008→2023: 総額 {c08/1e4:.1f}→{c23/1e4:.1f}兆円（+{(c23/c08-1)*100:.1f}%）。2008年の人口のまま単価だけ2023年にすると {fixed_pop/1e4:.1f}兆円（+{(fixed_pop/c08-1)*100:.1f}%）")
M = g[g.sex == "m"].pivot(index="age2", columns="year", values="percap").loc[AGES]
F = g[g.sex == "f"].pivot(index="age2", columns="year", values="percap").loc[AGES]
L.append("2023 女性/男性 一人当たり比:\n" + (F[2023] / M[2023]).round(2).to_string())
(RES / "a159_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

lab = [a.replace("+", "以上").replace("-", "〜") for a in AGES]
# 図1：カーブ
fig, ax = plt.subplots(figsize=(10, 5.6))
for y, col in zip([2008, 2013, 2018, 2023], [LIGHT, GRAY, BLUE, ORANGE]):
    ax.plot(range(len(AGES)), A[y] / 10, marker="o", ms=4, color=col, lw=2.2 if y == 2023 else 1.6, label=f"{y}年度")
ax.set_xticks(range(len(AGES))); ax.set_xticklabels(lab, rotation=45, fontsize=9)
ax.set_ylabel("人口一人当たりの医療費（万円/年）"); ax.set_xlabel("年齢（歳）")
ax.legend(frameon=False); ax.set_title("年齢別の一人当たり医療費のカーブ（85歳以上はまとめた値）")
save(fig, "a159_curve.png")

# 図2：伸び
avg = (tot.oku[2023] * 1e8 / tot["pop"][2023]) / (tot.oku[2008] * 1e8 / tot["pop"][2008]) * 100 - 100
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(range(len(AGES)), grow, color=[ORANGE if v > avg else BLUE for v in grow], width=0.7)
for i, v in enumerate(grow):
    ax.text(i, v + 1, f"{v:.0f}", ha="center", fontsize=8.5)
ax.axhline(avg, color=INK, ls="--", lw=1)
ax.set_xticks(range(len(AGES))); ax.set_xticklabels(lab, rotation=45, fontsize=9)
ax.set_ylabel("2008→2023年度の伸び（%）"); ax.set_xlabel("年齢（歳）")
ax.set_title("一人当たり医療費は、どの年齢で伸びたか（破線は全年齢の平均）")
save(fig, "a159_growth.png")

# 図3：男女（2023）
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.plot(range(len(AGES)), M[2023] / 10, marker="o", ms=4, color=BLUE, lw=2, label="男性")
ax.plot(range(len(AGES)), F[2023] / 10, marker="o", ms=4, color=ORANGE, lw=2, label="女性")
ax.fill_between(range(len(AGES)), M[2023] / 10, F[2023] / 10, where=(F[2023] > M[2023]).values, color=ORANGE, alpha=0.15, interpolate=True)
ax.set_xticks(range(len(AGES))); ax.set_xticklabels(lab, rotation=45, fontsize=9)
ax.set_ylabel("人口一人当たりの医療費（万円/年）"); ax.set_xlabel("年齢（歳）")
ax.legend(frameon=False); ax.set_title("男女で比べた一人当たり医療費（2023年度）")
save(fig, "a159_sex.png")
