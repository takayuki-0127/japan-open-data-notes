"""茶の栽培面積はどれだけ減ったか。荒茶の生産は茶種でどう変わったか"""
from common import *

nat, main, ar = load()
nat = nat.set_index("year"); main = main.set_index("year"); ar = ar.set_index("year")
# 全国の荒茶は累年表（aracha.xls）の方が毎年そろっているので、欠けた年を埋める（2011年産は主産県の合計）
nat["aracha_t"] = nat.aracha_t.fillna(ar.total.reindex(nat.index))
nat["yield_kg10a"] = nat.aracha_t / nat.area_ha * 100  # 栽培面積10a当たりの荒茶（kg）
nat.to_csv(RES / "a136_national.csv")

pk = nat.area_ha.idxmax(); pk_v = nat.area_ha.max(); last = nat.index.max()
L = []
L.append(f"栽培面積 最大 {nat.area_ha[nat.area_ha==pk_v].index.min()}〜{nat.area_ha[nat.area_ha==pk_v].index.max()}年 {pk_v:,.0f}ha → {last}年 {nat.area_ha[last]:,.0f}ha（{nat.area_ha[last]/pk_v-1:.1%}）")
L.append(f"1959年 {nat.area_ha[1959]:,.0f}ha、2004年 {nat.area_ha[2004]:,.0f}ha、2014年 {nat.area_ha[2014]:,.0f}ha")
for a, b in [(1983, 2004), (2004, 2014), (2014, 2024)]:
    L.append(f"{a}→{b} 年率 {(nat.area_ha[b]/nat.area_ha[a])**(1/(b-a))-1:.2%}  減少 {nat.area_ha[a]-nat.area_ha[b]:,.0f}ha")
ak = nat.aracha_t.idxmax()
L.append(f"荒茶 最大 {ak}年 {nat.aracha_t[ak]:,.0f}t → {last}年 {nat.aracha_t[last]:,.0f}t（{nat.aracha_t[last]/nat.aracha_t[ak]-1:.1%}）；2004年 {nat.aracha_t[2004]:,.0f}t")
y = nat.yield_kg10a.dropna()
L.append(f"10a当たり荒茶 1960年 {y[1960]:.0f}kg、1975年 {y[1975]:.0f}kg、2004年 {y[2004]:.0f}kg、2019年 {y[2019]:.0f}kg、2024年 {y[last]:.0f}kg")
L.append(f"主産県合計の栽培面積 2005年 {main.area_ha[2005]:,.0f}ha → 2024年 {main.area_ha[2024]:,.0f}ha（{main.area_ha[2024]/main.area_ha[2005]-1:.1%}）；全国 同期間 {nat.area_ha[2024]/nat.area_ha[2005]-1:.1%}")
# 茶種別
types = {"sencha": "普通せん茶", "bancha": "番茶", "ooi": "おおい茶（玉露・かぶせ茶・てん茶）", "tamaryokucha": "玉緑茶"}
for c, n in types.items():
    s = ar[c].dropna()
    s = s[s.index >= 1951]
    L.append(f"{n}: 1975年 {ar.loc[1975,c]:,.0f}t, 2008年 {ar.loc[2008,c]:,.0f}t, 2016年 {ar.loc[2016,c]:,.0f}t, 最大 {s.idxmax()}年 {s.max():,.0f}t")
L.append(f"てん茶 1975年 {ar.loc[1975,'tencha']:,.0f}t, 1985年 {ar.loc[1985,'tencha']:,.0f}t, 2008年 {ar.loc[2008,'tencha']:,.0f}t")
sh = ar.loc[[1975, 2008, 2016], ["sencha", "bancha", "ooi", "tamaryokucha"]].div(ar.loc[[1975, 2008, 2016], "total"], axis=0)
L.append("構成比 1975/2008/2016:\n" + sh.round(3).to_string())
ar.to_csv(RES / "a136_aracha_by_type.csv")
(RES / "a136_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：栽培面積と荒茶生産量
fig, ax = plt.subplots(figsize=(10, 4.4))
ax.plot(nat.index, nat.area_ha / 1000, color=BLUE, lw=2.2, label="栽培面積（千ha、左）")
ax.plot(main.index, main.area_ha / 1000, color=BLUE, lw=1.2, ls=":", label="うち主産県の合計（千ha、左）")
ax.set_ylabel("栽培面積（千ha）"); ax.set_ylim(0, 70)
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(nat.index, nat.aracha_t / 1000, color=ORANGE, lw=1.8, marker="o", ms=2.5, label="荒茶生産量（千t、右）")
ax2.set_ylabel("荒茶生産量（千t）"); ax2.set_ylim(0, 120)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="lower left")
ax.set_title("茶の栽培面積は1980〜83年の6.1万haから3.5万haへ4割減", loc="left")
save(fig, "a136_area.png")

# 図2：10a当たりの荒茶
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(y.index, y.values, color=GREEN, lw=1.8, marker="o", ms=3)
ax.set_ylabel("栽培面積10a当たりの荒茶（kg）")
ax.set_title("10a当たりの荒茶は1960年代の平均168kgから、2024年は211kgと最も多い", loc="left")
save(fig, "a136_yield.png")

# 図3：茶種別の荒茶生産量
fig, ax = plt.subplots(figsize=(10, 4.4))
sub = ar.loc[1951:2016]
for c, col in [("sencha", BLUE), ("bancha", ORANGE), ("ooi", GREEN), ("tamaryokucha", PURPLE)]:
    ax.plot(sub.index, sub[c] / 1000, color=col, lw=1.8, label=types[c])
ax.set_ylabel("荒茶生産量（千t）")
ax.legend(frameon=False, fontsize=9)
ax.set_title("せん茶は減り、番茶とおおい茶（抹茶の原料のてん茶など）は増えた（〜2016年産）", loc="left", fontsize=12)
save(fig, "a136_types.png")
