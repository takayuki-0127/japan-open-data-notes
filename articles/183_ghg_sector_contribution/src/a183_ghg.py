"""日本の排出量の減少は、どの部門がけん引したか（温室効果ガスインベントリ、電気・熱配分後）"""
from common import *

d = load("ghg_japan_fy1990_2024.csv")
p = d.pivot_table(index="fiscal_year", columns="item", values="mt_co2e")
SEC = [("産業部門", "産業"), ("業務その他部門", "業務その他"), ("家庭部門", "家庭"), ("運輸部門", "運輸"),
       ("エネルギー転換部門", "エネルギー転換"), ("工業プロセス及び製品の使用", "工業プロセス"), ("廃棄物", "廃棄物"),
       ("その他（間接CO2等）", "その他CO2"), ("メタン（CH4）", "メタン"), ("一酸化二窒素（N2O）", "一酸化二窒素"),
       ("代替フロン等４ガス", "代替フロン等")]
q = pd.DataFrame({s: p[k] for k, s in SEC})
q["合計"] = p["計"]
q.round(3).to_csv(RES / "a183_by_sector_mt.csv", encoding="utf-8")
B, E = 2013, 2024
ch = (q.loc[E] - q.loc[B]).drop("合計")
tot = q.loc[E, "合計"] - q.loc[B, "合計"]
c = pd.DataFrame({"mt_2013": q.loc[B].drop("合計"), "mt_2024": q.loc[E].drop("合計"), "change_mt": ch,
                  "share_of_decrease_pct": ch / tot * 100, "change_pct": ch / q.loc[B].drop("合計") * 100})
c.sort_values("change_mt").round(2).to_csv(RES / "a183_contribution_2013_2024.csv", encoding="utf-8")
sub = ["鉄鋼", "化学（含石油石炭製品）", "窯業･土石製品", "機械（含金属製品）"]
L = []
L.append(f"合計 1990 {q.loc[1990,'合計']:.1f}、ピーク {q['合計'].idxmax()} {q['合計'].max():.1f}、2024 {q.loc[E,'合計']:.1f} Mt")
L.append(f"2013→2024 {tot:.1f} Mt（{tot/q.loc[B,'合計']*100:.1f}%）；1990比 {(q.loc[E,'合計']/q.loc[1990,'合計']-1)*100:.1f}%")
for s, r in c.sort_values("change_mt").iterrows():
    L.append(f"  {s}: {r.mt_2013:.1f}→{r.mt_2024:.1f}（{r.change_mt:+.1f}、減少への寄与{r.share_of_decrease_pct:.1f}%、{r.change_pct:+.1f}%）")
en = ["産業", "業務その他", "家庭", "運輸", "エネルギー転換"]
L.append(f"エネルギー起源5部門の寄与合計 {c.loc[en,'share_of_decrease_pct'].sum():.1f}%")
for k in sub:
    L.append(f"  産業内 {k}: {p.loc[B,k]:.1f}→{p.loc[E,k]:.1f}（{p.loc[E,k]-p.loc[B,k]:+.1f}）")
for k in ["HFCs"]:
    h = p["ハイドロフルオロカーボン類（HFCs）"]
    L.append(f"HFCs 2004 {h.loc[2004]:.1f}→ピーク {h.idxmax()} {h.max():.1f}→2024 {h.loc[E]:.1f}")
for s in en:
    L.append(f"{s} 1990→2013→2024: {q.loc[1990,s]:.1f}→{q.loc[B,s]:.1f}→{q.loc[E,s]:.1f}（1990比{(q.loc[E,s]/q.loc[1990,s]-1)*100:+.1f}%）")
L.append("2013→2024 年平均 " + f"{tot/(E-B):.1f} Mt/年")
(RES / "a183_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1 積み上げ
cols = ["産業", "運輸", "業務その他", "家庭", "エネルギー転換", "工業プロセス", "廃棄物", "その他CO2", "メタン", "一酸化二窒素", "代替フロン等"]
grp = pd.DataFrame({"産業": q["産業"], "運輸": q["運輸"], "業務その他": q["業務その他"], "家庭": q["家庭"],
                    "エネルギー転換": q["エネルギー転換"],
                    "その他（工業プロセス・廃棄物・CO2以外のガス）": q[cols[5:]].sum(1)})
colors = [BLUE, ORANGE, GREEN, PURPLE, "#d6a62a", LIGHT]
fig, ax = plt.subplots(figsize=(9, 5))
ax.stackplot(grp.index, grp.T.values, labels=grp.columns, colors=colors, alpha=.95)
ax.plot(q.index, q["合計"], color=INK, lw=1.2)
ax.annotate(f"{B}年度 {q.loc[B,'合計']:.0f}", (B, q.loc[B, "合計"]), xytext=(B - 9, 1470), arrowprops=dict(arrowstyle="-", color=GRAY), fontsize=10)
ax.annotate(f"{E}年度 {q.loc[E,'合計']:.0f}", (E, q.loc[E, "合計"]), xytext=(E - 6, 1250), arrowprops=dict(arrowstyle="-", color=GRAY), fontsize=10)
ax.set_ylim(0, 1550); ax.set_xlim(1990, 2024)
ax.set_ylabel("百万トン（CO2換算）"); ax.set_title("日本の温室効果ガス排出量（部門別、電気・熱は使った部門に配分）")
ax.legend(loc="lower left", fontsize=8.5, ncol=3, frameon=True)
save(fig, "a183_stack.png")

# 図2 寄与
cc = c.sort_values("change_mt")
fig, ax = plt.subplots(figsize=(8, 5.2))
ax.barh(cc.index[::-1], cc.change_mt[::-1], color=[ORANGE if v > 0 else BLUE for v in cc.change_mt[::-1]])
for i, (s, r) in enumerate(cc[::-1].iterrows()):
    ax.text(r.change_mt + (-2 if r.change_mt < 0 else 2), i, (f"{r.change_mt:+.1f}（{r.share_of_decrease_pct:.0f}%）" if r.change_mt < 0 else f"{r.change_mt:+.1f}（増加）"),
            va="center", ha="right" if r.change_mt < 0 else "left", fontsize=9)
ax.axvline(0, color=INK, lw=.8); ax.set_xlim(-170, 30)
ax.set_xlabel("2013→2024年度の増減（百万トンCO2換算）。かっこは減少全体に占める割合")
ax.set_title(f"減少 {-tot:.0f}百万トンの内訳（2013→2024年度）")
save(fig, "a183_contribution.png")

# 図3 指数
OFF = {"産業": 1.0, "業務その他": -2.6, "家庭": -0.8, "運輸": 0, "エネルギー転換": 1.6}
fig, ax = plt.subplots(figsize=(9, 5))
for s, col in zip(en, [BLUE, GREEN, PURPLE, ORANGE, "#d6a62a"]):
    ax.plot(q.index, q[s] / q.loc[B, s] * 100, color=col, lw=2, label=s)
    ax.text(E + .3, q.loc[E, s] / q.loc[B, s] * 100 + OFF[s], f"{s} {q.loc[E,s]/q.loc[B,s]*100:.0f}", color=col, va="center", fontsize=9)
ax.axhline(100, color=GRAY, lw=.8, ls="--"); ax.axvline(B, color=GRAY, lw=.8, ls=":")
ax.set_xlim(1990, 2030); ax.set_ylabel(f"{B}年度＝100"); ax.set_title("エネルギー起源CO2の部門別の推移（電気・熱配分後）")
save(fig, "a183_index.png")
