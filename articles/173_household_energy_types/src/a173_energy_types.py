"""A173 家庭の光熱費の内訳で、52都市は何タイプに分かれるか（k-means）"""
from common import *
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score, adjusted_rand_score

d = load("kakei2024_utilities_by_city.csv")
c = d[d.kind.isin(["県庁所在市", "政令市"])].copy()
c["energy"] = c.electricity + c.gas + c.other_fuel          # 光熱費（上下水道を除く）
for k in ["electricity", "city_gas", "lpg", "other_fuel"]:
    c["s_" + k] = c[k] / c.energy
F = ["s_electricity", "s_city_gas", "s_lpg", "s_other_fuel"]
LAB = {"s_electricity": "電気代", "s_city_gas": "都市ガス", "s_lpg": "プロパンガス", "s_other_fuel": "灯油など"}
X = StandardScaler().fit_transform(c[F])
L = []
sil = {}
for k in range(2, 7):
    km = KMeans(k, n_init=50, random_state=0).fit(X)
    sil[k] = silhouette_score(X, km.labels_)
L.append("シルエット係数 " + " ".join(f"k={k}:{v:.3f}" for k, v in sil.items()))
K = max(sil, key=sil.get)
km = KMeans(K, n_init=50, random_state=0).fit(X)
ward = AgglomerativeClustering(K, linkage="ward").fit(X)
L.append(f"k={K} を採用。Ward法との一致（調整ランド指数）{adjusted_rand_score(km.labels_, ward.labels_):.2f}")
c["cl"] = km.labels_
# タイプ名：灯油の割合が最も高い群＝灯油型、都市ガスが最も高い群＝都市ガス型、残り＝電気・プロパン型
m = c.groupby("cl")[F].mean()
kero = m.s_other_fuel.idxmax(); gas = m.drop(kero).s_city_gas.idxmax()
NAME = {kero: "灯油型", gas: "都市ガス型"}
for g in m.index:
    NAME.setdefault(g, "電気・プロパン型")
c["type"] = c.cl.map(NAME)
ORDER = ["灯油型", "電気・プロパン型", "都市ガス型"]
COL = {"灯油型": ORANGE, "電気・プロパン型": GREEN, "都市ガス型": BLUE}
c.drop(columns="cl").to_csv(RES / "a173_city_types.csv", index=False)
for t in ORDER:
    s = c[c.type == t]
    L.append(f"{t}（{len(s)}都市）: 電気 {s.s_electricity.mean():.1%} 都市ガス {s.s_city_gas.mean():.1%} プロパン {s.s_lpg.mean():.1%} 灯油など {s.s_other_fuel.mean():.1%}"
             f" 光熱費 平均{s.energy.mean():,.0f}円 1人当たり{(s.energy / s.hh_size).mean():,.0f}円 ／ " + "・".join(s.area))
nat = d[d.kind == "全国"].iloc[0]
e = nat.electricity + nat.gas + nat.other_fuel
L.append(f"全国（総世帯）光熱費 {e:,.0f}円 電気 {nat.electricity / e:.1%} 都市ガス {nat.city_gas / e:.1%} プロパン {nat.lpg / e:.1%} 灯油など {nat.other_fuel / e:.1%}")
top = c.sort_values("energy")
L.append(f"光熱費 最大 {top.iloc[-1].area} {top.iloc[-1].energy:,.0f}円 最小 {top.iloc[0].area} {top.iloc[0].energy:,.0f}円 比 {top.iloc[-1].energy / top.iloc[0].energy:.2f}倍")
L.append(f"灯油などの割合と光熱費の相関 {c.s_other_fuel.corr(c.energy):.2f}、都市ガスの割合と光熱費の相関 {c.s_city_gas.corr(c.energy):.2f}")
open(RES / "a173_summary.txt", "w").write("\n".join(L) + "\n")
print("\n".join(L))

# 図1 内訳の積み上げ（タイプ順）
c["o"] = c.type.map({t: i for i, t in enumerate(ORDER)})
s = c.sort_values(["o", "s_electricity"], ascending=[False, True])
fig, ax = plt.subplots(figsize=(9, 12))
left = np.zeros(len(s))
for f, col in zip(F, [LIGHT, BLUE, GREEN, ORANGE]):
    ax.barh(s.area, s[f] * 100, left=left, color=col, label=LAB[f], height=0.75)
    left += s[f].values * 100
for i, (a, t) in enumerate(zip(s.area, s.type)):
    ax.text(101, i, t, va="center", fontsize=8, color=COL[t])
ax.set_xlim(0, 115); ax.set_xlabel("光熱費（電気・ガス・灯油など）に占める割合（%）")
ax.tick_params(axis="y", labelsize=8.5); ax.margins(y=0.005)
ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.45, 1.0), frameon=False, fontsize=9)
ax.set_title("都市ごとの光熱費の内訳（2024年、1世帯当たり）", pad=24)
save(fig, "a173_mix.png")

# 図2 散布図
fig, ax = plt.subplots(figsize=(9.5, 5.2))
for t in ORDER:
    s = c[c.type == t]
    ax.scatter(s.s_city_gas * 100, s.s_other_fuel * 100, color=COL[t], s=34, label=f"{t}（{len(s)}都市）")
    for a in s.itertuples():
        if a.s_other_fuel > 0.15 or a.s_city_gas > 0.33 or a.s_city_gas < 0.035:
            ax.annotate(a.area, (a.s_city_gas * 100, a.s_other_fuel * 100), xytext=(3, 3), textcoords="offset points", fontsize=8)
ax.set_xlabel("都市ガスの割合（%）"); ax.set_ylabel("灯油などの割合（%）")
ax.legend(frameon=False, fontsize=9)
ax.set_title(f"k-meansで{K}タイプに分けた結果（52都市）")
save(fig, "a173_scatter.png")

# 図3 光熱費の水準
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, col, ttl in [(axes[0], "energy", "1世帯当たり（円/年）"), (axes[1], "pp", "1人当たり（円/年）")]:
    c["pp"] = c.energy / c.hh_size
    for i, t in enumerate(ORDER):
        v = c[c.type == t][col]
        ax.scatter(np.full(len(v), i) + np.random.default_rng(1).uniform(-0.12, 0.12, len(v)), v / 1e4, color=COL[t], s=22, alpha=0.85)
        ax.plot([i - 0.25, i + 0.25], [v.mean() / 1e4] * 2, color=INK, lw=2)
        ax.text(i + 0.28, v.mean() / 1e4, f"{v.mean() / 1e4:.1f}", va="center", fontsize=9)
    ax.set_xticks(range(len(ORDER))); ax.set_xticklabels(ORDER); ax.set_ylabel("万円"); ax.set_title(ttl, fontsize=11)
fig.suptitle("タイプ別の光熱費（電気・ガス・灯油など、黒線は平均）", fontsize=13)
save(fig, "a173_level.png")
