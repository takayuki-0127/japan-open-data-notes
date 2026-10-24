"""漁港ごとの水揚げ量は、少数の大きな港に集まっているか（水産物流通調査、2013年211漁港・2024年147漁港）"""
from common import *

d = load()
L = []
rows = []
for y, g in d.dropna(subset=["qty_t"]).groupby("year"):
    q = g.qty_t.sort_values(ascending=False); v = g.value_oku.sort_values(ascending=False); n = len(q)
    s = lambda k, x: x.head(k).sum() / x.sum()
    k50 = int((q.cumsum() / q.sum() < 0.5).sum() + 1)
    rows.append(dict(year=y, ports=n, total_t=int(q.sum()), top1=s(1, q), top5=s(5, q), top10=s(10, q), top20=s(20, q),
                     ports_for_half=k50, bottom_half_share=q.tail(n // 2).sum() / q.sum(), gini=gini(q), hhi=((q / q.sum()) ** 2).sum(),
                     value_top10=s(10, v), value_gini=gini(v)))
    L.append(f"{y}: {n}漁港 計{int(q.sum()):,}t、上位1 {s(1,q):.1%}、上位5 {s(5,q):.1%}、上位10 {s(10,q):.1%}、上位20 {s(20,q):.1%}、半分に届く港数 {k50}（{k50/n:.1%}）、下位半分 {q.tail(n//2).sum()/q.sum():.1%}、ジニ {gini(q):.2f}、金額の上位10 {s(10,v):.1%}・ジニ {gini(v):.2f}")
    L.append(f"  上位10: " + "、".join(f"{g.loc[i,'label']} {int(q[i]):,}t" for i in q.head(10).index))
pd.DataFrame(rows).round(4).to_csv(RES / "a199_concentration.csv", index=False, encoding="utf-8")
# 両年に共通する漁港
w = d.pivot_table(index=["area", "port", "pref"], columns="year", values="qty_t").dropna()
L.append(f"共通漁港 {len(w)}港: 2013 {int(w[2013].sum()):,}t → 2024 {int(w[2024].sum()):,}t（{w[2024].sum()/w[2013].sum()-1:+.1%}）、上位10の割合 {w[2013].nlargest(10).sum()/w[2013].sum():.1%} → {w[2024].nlargest(10).sum()/w[2024].sum():.1%}、ジニ {gini(w[2013]):.2f} → {gini(w[2024]):.2f}")
w["chg"] = w[2024] / w[2013] - 1
big = w[2013].nlargest(20).index
L.append("2013年の上位20港の変化: " + "、".join(f"{p[1]} {w.loc[p,'chg']:+.0%}" for p in big))
L.append(f"2013年上位20港の合計 {w.loc[big,2013].sum():,.0f}→{w.loc[big,2024].sum():,.0f}t（{w.loc[big,2024].sum()/w.loc[big,2013].sum()-1:+.1%}）、それ以外 {w.drop(big)[2013].sum():,.0f}→{w.drop(big)[2024].sum():,.0f}t（{w.drop(big)[2024].sum()/w.drop(big)[2013].sum()-1:+.1%}）")
w.to_csv(RES / "a199_common_ports.csv", encoding="utf-8")
g = d[d.year == 2024]
r = np.corrcoef(np.log10(g.qty_t), np.log10(g.price_yen_kg))[0, 1]
L.append(f"2024 水揚量と価格（対数）の相関 r={r:.2f}。1万t以上の港 {int((g.qty_t>=1e4).sum())}港の平均価格（数量加重） {(g[g.qty_t>=1e4].value_oku.sum()/g[g.qty_t>=1e4].qty_t.sum()*1e5):.0f}円/kg、1,000t未満 {int((g.qty_t<1e3).sum())}港 {(g[g.qty_t<1e3].value_oku.sum()/g[g.qty_t<1e3].qty_t.sum()*1e5):.0f}円/kg")
(RES / "a199_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：ローレンツ曲線
fig, ax = plt.subplots(figsize=(6.8, 6.2))
for y, c in [(2013, LIGHT), (2024, BLUE)]:
    gg = d[(d.year == y)].dropna(subset=["qty_t"])
    x, cc = lorenz(gg.qty_t)
    ax.plot(x * 100, cc * 100, color=c, lw=2.2, label=f"{y}年（{len(gg)}漁港、ジニ係数 {gini(gg.qty_t):.2f}）")
gg = d[d.year == 2024]; x, cc = lorenz(gg.value_oku)
ax.plot(x * 100, cc * 100, color=ORANGE, lw=1.5, ls="--", label=f"2024年 金額（ジニ係数 {gini(gg.value_oku):.2f}）")
ax.plot([0, 100], [0, 100], color=GRAY, lw=0.8)
ax.set_xlabel("水揚量の少ない港から数えた港の割合（%）"); ax.set_ylabel("水揚量の累積割合（%）")
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title("漁港の水揚量のローレンツ曲線")
save(fig, "a199_lorenz.png")

# 図2：上位20港（2024）と2013年
g = d[d.year == 2024].nlargest(20, "qty_t").iloc[::-1]
m13 = d[d.year == 2013].set_index(["area", "port", "pref"]).qty_t
fig, ax = plt.subplots(figsize=(8.5, 6.5))
ys = np.arange(len(g))
ax.barh(ys, g.qty_t / 1e4, color=BLUE, height=0.7, label="2024年")
ax.scatter([m13.get((a, p, f), np.nan) / 1e4 for a, p, f in zip(g.area, g.port, g.pref)], ys, color=ORANGE, s=20, zorder=3, label="2013年")
tot = d[d.year == 2024].qty_t.sum()
o13 = [m13.get((a, p, f), np.nan) for a, p, f in zip(g.area, g.port, g.pref)]
for y_, (q_, o_) in enumerate(zip(g.qty_t, o13)):
    ax.text(max(q_, 0 if np.isnan(o_) else o_) / 1e4 + 0.4, y_, f"{q_/tot:.1%}", va="center", fontsize=8)
ax.set_yticks(ys); ax.set_yticklabels([f"{l}（{p}）" for l, p in zip(g.label, g.pref)], fontsize=8.5)
ax.set_xlabel("上場水揚量（万t）　数字は147漁港の合計に占める割合"); ax.legend(frameon=False, loc="lower right")
ax.set_title("水揚量の多い20漁港（2024年）")
save(fig, "a199_top20.png")

# 図3：水揚量と価格
g = d[d.year == 2024]
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.scatter(g.qty_t, g.price_yen_kg, s=18, color=BLUE, alpha=0.7)
for _, rr in g.nlargest(8, "qty_t").iterrows():
    ax.annotate(rr.label, (rr.qty_t, rr.price_yen_kg), xytext=(4, 3), textcoords="offset points", fontsize=8)
for _, rr in g.nlargest(1, "price_yen_kg").iterrows():
    ax.annotate(rr.label, (rr.qty_t, rr.price_yen_kg), xytext=(4, 3), textcoords="offset points", fontsize=8, color=GRAY)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("上場水揚量（t、対数目盛）"); ax.set_ylabel("平均卸売価格（円/kg、対数目盛）")
ax.set_title(f"水揚量が多い港ほど平均価格は安い（2024年、147漁港、r={r:.2f}）")
save(fig, "a199_qty_price.png")
