"""野菜の産地はどれだけ集中しているか：品目別のHHI・上位県シェア（2014年産と2024年産）"""
from common import *

p = load("pref_harvest.csv"); n = load("national_harvest.csv")
p = p.dropna(subset=["harvest_t"])
p = p.merge(n[["year", "item", "harvest_t"]].rename(columns={"harvest_t": "nat"}), on=["year", "item"])
p["share"] = p.harvest_t / p.nat
rows = []
for (y, it), g in p.groupby(["year", "item"]):
    g = g.sort_values("share", ascending=False)
    rows.append(dict(year=y, item=it, n_pref=len(g), coverage=g.share.sum(), hhi=(g.share ** 2).sum() * 10000,
                     top1_pref=g.pref.iloc[0], top1=g.share.iloc[0], top3=g.share.iloc[:3].sum(), top5=g.share.iloc[:5].sum(),
                     nat_t=g.nat.iloc[0]))
r = pd.DataFrame(rows)
r.to_csv(RES / "a191_concentration.csv", index=False, float_format="%.4f")
w = r.pivot(index="item", columns="year", values=["hhi", "top1", "top3", "coverage", "n_pref"])
w.columns = [f"{a}_{b}" for a, b in w.columns]
w["top1_pref_2024"] = r[r.year == 2024].set_index("item").top1_pref
w["top1_pref_2014"] = r[r.year == 2014].set_index("item").top1_pref
w["d_hhi"] = w.hhi_2024 - w.hhi_2014
w = w.sort_values("hhi_2024", ascending=False)
w.to_csv(RES / "a191_compare.csv", float_format="%.4f")
L = []
L.append(f"品目数 {len(w)}")
L.append("HHI上位（2024）:\n" + w[["hhi_2024", "top1_pref_2024", "top1_2024", "top3_2024", "hhi_2014", "coverage_2024"]].head(12).round(3).to_string())
L.append("HHI下位（2024）:\n" + w[["hhi_2024", "top1_pref_2024", "top1_2024", "top3_2024", "hhi_2014", "coverage_2024"]].tail(10).round(3).to_string())
L.append(f"上位3県で5割以上 {int((w.top3_2024>=0.5).sum())}品目、1県で3割以上 {int((w.top1_2024>=0.3).sum())}品目、HHI2500以上 {int((w.hhi_2024>=2500).sum())}")
L.append(f"HHIが上がった品目 {int((w.d_hhi>0).sum())}/{len(w)}、中央値 2014 {w.hhi_2014.median():.0f} → 2024 {w.hhi_2024.median():.0f}")
L.append("HHI変化の大きい品目:\n" + w.sort_values("d_hhi")[["hhi_2014", "hhi_2024", "d_hhi", "top1_pref_2014", "top1_pref_2024"]].iloc[list(range(5)) + list(range(-6, 0))].round(0).to_string())
L.append("1位の県が入れ替わった品目: " + ", ".join(f"{i}({a}→{b})" for i, a, b in zip(w.index, w.top1_pref_2014, w.top1_pref_2024) if a != b))
L.append(f"カバー率（調査した県の合計÷全国）最小 2024: {w.coverage_2024.min():.3f} ({w.coverage_2024.idxmin()})")
(RES / "a191_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：上位3県シェア（2024）
s = w.sort_values("top3_2024")
fig, ax = plt.subplots(figsize=(9, 10))
y = np.arange(len(s))
ax.barh(y, s.top1_2024 * 100, color=BLUE, label="1位の県")
ax.barh(y, (s.top3_2024 - s.top1_2024) * 100, left=s.top1_2024 * 100, color=LIGHT, label="2〜3位の県")
for yy, (it, t3, pf) in enumerate(zip(s.index, s.top3_2024, s.top1_pref_2024)):
    ax.text(t3 * 100 + 1, yy, pf, va="center", fontsize=8, color=INK)
ax.set_yticks(y); ax.set_yticklabels(s.index, fontsize=9)
ax.axvline(50, color=GRAY, lw=0.8, ls="--")
ax.set_xlim(0, 105); ax.set_xlabel("全国の収穫量に占める割合（%、2024年産）")
ax.set_title("野菜41品目の産地の集中度：上位3県の割合（右の県名は1位）")
ax.legend(loc="lower right", frameon=False)
save(fig, "a191_top3.png")

# 図2：HHI 2014 vs 2024
fig, ax = plt.subplots(figsize=(8, 7))
ax.scatter(w.hhi_2014, w.hhi_2024, color=BLUE, s=28)
m = max(w.hhi_2014.max(), w.hhi_2024.max()) * 1.05
ax.plot([0, m], [0, m], color=GRAY, lw=0.8, ls="--")
lab = w.reindex(w.d_hhi.abs().sort_values(ascending=False).index).head(10).index.tolist() + w.head(4).index.tolist()
for it in set(lab):
    ax.annotate(it, (w.hhi_2014[it], w.hhi_2024[it]), fontsize=8.5, xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("HHI（2014年産）"); ax.set_ylabel("HHI（2024年産）"); ax.set_xlim(0, m); ax.set_ylim(0, m)
ax.set_title("産地の集中度（HHI）の10年の変化：点線より上は集中が進んだ品目")
save(fig, "a191_hhi_change.png")

# 図3：主な品目の1位県シェアの変化
sel = ["ばれいしょ", "たまねぎ", "にんじん", "キャベツ", "レタス", "はくさい", "だいこん", "トマト", "ねぎ"]
sel = [i for i in sel if i in w.index]
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(sel))
ax.bar(x - 0.2, w.loc[sel, "top3_2014"] * 100, 0.4, color=GRAY, label="2014年産")
ax.bar(x + 0.2, w.loc[sel, "top3_2024"] * 100, 0.4, color=BLUE, label="2024年産")
for i, it in enumerate(sel):
    ax.text(i + 0.2, w.loc[it, "top3_2024"] * 100 + 1, f"{w.loc[it,'top3_2024']*100:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(sel); ax.set_ylabel("上位3県の割合（%）"); ax.set_ylim(0, 100)
ax.set_title("収穫量の多い野菜の上位3県の割合")
ax.legend(frameon=False)
save(fig, "a191_major.png")
