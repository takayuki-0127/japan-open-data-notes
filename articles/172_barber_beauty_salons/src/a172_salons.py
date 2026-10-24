"""理容所は減り、美容所は増えた？ 生活衛生施設の60年（1965〜2024年度）"""
from common import *

d = load("seikatsu_eisei_facilities.csv").set_index("year")
L = []
b, s = d.barber_shops, d.beauty_salons
L.append(f"理容所 1965 {b[1965]:,} → 最大 {b.idxmax()} {b.max():,} → 2024 {b[2024]:,}（最大比 {b[2024]/b.max()-1:+.1%}）")
L.append(f"美容所 1965 {s[1965]:,} → 2024 {s[2024]:,}（{s[2024]/s[1965]:.2f}倍）、2000→2024 {s[2024]/s[2000]-1:+.1%}")
cross = d.index[(s > b)].min()
L.append(f"美容所が理容所を上回った年 {cross}（{cross-1}: 理容 {b[cross-1]:,} 美容 {s[cross-1]:,}）")
L.append(f"2024 美容所÷理容所 {s[2024]/b[2024]:.2f}倍")
d["barbers_per_shop"] = d.barbers / d.barber_shops; d["beauticians_per_salon"] = d.beauticians / d.beauty_salons
for y in [1965, 1985, 2005, 2024]:
    L.append(f"{y} 1施設当たり 理容師 {d.barbers_per_shop[y]:.2f}人 美容師 {d.beauticians_per_salon[y]:.2f}人")
L.append(f"理容師 最大 {d.barbers.idxmax()} {d.barbers.max():,} → 2024 {d.barbers[2024]:,}（{d.barbers[2024]/d.barbers.max()-1:+.1%}）、美容師 2024 {d.beauticians[2024]:,}（1965の{d.beauticians[2024]/d.beauticians[1965]:.1f}倍）")
for c, n in [("ordinary_public_bath", "一般公衆浴場（銭湯）"), ("cleaning", "クリーニング"), ("cinema", "映画館"), ("simple_lodging", "簡易宿所"), ("hotel_ryokan", "旅館・ホテル")]:
    x = d[c].dropna()
    L.append(f"{n}: 最大 {x.idxmax()} {x.max():,} → 2024 {x[2024]:,}（最大比 {x[2024]/x.max()-1:+.1%}）")
d.to_csv(RES / "a172_series.csv")
(RES / "a172_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))

# 図1 理容所と美容所
fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.plot(d.index, b / 1e4, color=BLUE, lw=2.4, label="理容所")
ax.plot(d.index, s / 1e4, color=ORANGE, lw=2.4, label="美容所")
ax.axvline(cross, color=GRAY, lw=0.8, ls=":")
ax.text(cross + 0.5, 25, f"{cross}年度に\n美容所が上回る", fontsize=9, color=GRAY)
ax.set_ylabel("施設数（万）"); ax.set_ylim(0, 30); ax.legend(frameon=False, loc="upper left")
ax.annotate(f"{b[2024]/1e4:.1f}万", (2024, b[2024]/1e4), xytext=(5, -4), textcoords="offset points", fontsize=9, color=BLUE)
ax.annotate(f"{s[2024]/1e4:.1f}万", (2024, s[2024]/1e4), xytext=(5, -4), textcoords="offset points", fontsize=9, color=ORANGE)
ax.set_title("理容所と美容所の数（1965〜2024年度）")
save(fig, "a172_shops.png")

# 図2 1施設当たりの従業者
fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.plot(d.index, d.barbers_per_shop, color=BLUE, lw=2.2, label="理容所1か所当たりの理容師")
ax.plot(d.index, d.beauticians_per_salon, color=ORANGE, lw=2.2, label="美容所1か所当たりの美容師")
ax.set_ylabel("人"); ax.set_ylim(1.4, 2.4); ax.legend(frameon=False)
ax.set_title("1施設当たりの従業理容師・美容師")
save(fig, "a172_per_shop.png")

# 図3 ほかの生活衛生施設（最大の年=100）
fig, ax = plt.subplots(figsize=(9.5, 4.4))
for c, n, col in [("ordinary_public_bath", "一般公衆浴場（銭湯）", PURPLE), ("cleaning", "クリーニング", GREEN), ("cinema", "映画館", GRAY), ("barber_shops", "理容所", BLUE), ("simple_lodging", "簡易宿所", ORANGE)]:
    x = d[c].dropna(); ax.plot(x.index, x / x.max() * 100, lw=2, color=col, label=n)
ax.set_ylabel("それぞれの最大の年＝100"); ax.set_ylim(0, 105); ax.legend(frameon=False, fontsize=9, ncol=2, loc="lower left")
ax.set_title("ほかの生活衛生施設の数（最大の年＝100）")
save(fig, "a172_others.png")
