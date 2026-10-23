"""医科診療医療費のシェアが伸びている病気（傷病大分類）はどれか（2011〜2023年度）"""
from common import *

d = load("ika_by_disease_2011_2023.csv")
Y = [c for c in d.columns if c.startswith("y")]; yrs = [int(c[1:]) for c in Y]
tot = d[d.cls == "0"].iloc[0][Y].astype(float)
g = d[d.cls != "0"].set_index("name")[Y].astype(float)
SHORT = {"新生物＜腫瘍＞": "がんなど（新生物）", "循環器系の疾患": "循環器", "筋骨格系及び結合組織の疾患": "筋骨格系", "腎尿路生殖器系の疾患": "腎尿路生殖器",
         "呼吸器系の疾患": "呼吸器", "損傷，中毒及びその他の外因の影響": "けが・中毒", "内分泌，栄養及び代謝疾患": "内分泌・代謝（糖尿病など）",
         "精神及び行動の障害": "精神", "消化器系の疾患": "消化器", "神経系の疾患": "神経系", "眼及び付属器の疾患": "眼", "感染症及び寄生虫症": "感染症",
         "皮膚及び皮下組織の疾患": "皮膚", "症状，徴候及び異常臨床所見・異常検査所見で他に分類されないもの": "症状・異常所見",
         "血液及び造血器の疾患並びに免疫機構の障害": "血液・免疫", "妊娠，分娩及び産じょく": "妊娠・分娩", "周産期に発生した病態": "周産期",
         "先天奇形，変形及び染色体異常": "先天奇形", "耳及び乳様突起の疾患": "耳", "特殊目的用コード（COVID-19を含む）": "特殊目的用コード（コロナ）"}
sh = g.div(tot, axis=1) * 100
a, b = "y2011", "y2023"
t = pd.DataFrame({"y2011_oku": g[a], "y2023_oku": g[b], "growth_pct": (g[b] / g[a] - 1) * 100, "share2011": sh[a], "share2023": sh[b],
                  "share_pt": sh[b] - sh[a], "contrib_pct_of_increase": (g[b] - g[a]) / (tot[b] - tot[a]) * 100})
t.index = [SHORT.get(i, i) for i in t.index]
t = t.sort_values("share_pt", ascending=False)
t.round(2).to_csv(RES / "a167_change_2011_2023.csv", encoding="utf-8")
sh.T.set_index(pd.Index(yrs)).rename(columns=SHORT).round(3).to_csv(RES / "a167_share_by_year.csv", encoding="utf-8")
L = [f"医科診療医療費 総数 2011年度 {tot[a]/1e4:.2f}兆円 → 2023年度 {tot[b]/1e4:.2f}兆円（{tot[b]/tot[a]-1:+.1%}）"]
L.append("シェアの変化（2011→2023、ポイント）:\n" + t[["share2011", "share2023", "share_pt", "growth_pct", "contrib_pct_of_increase"]].round(1).to_string())
L.append(f"2019→2023 総数 {tot['y2023']/tot['y2019']-1:+.1%}；呼吸器 2019 {g.loc['呼吸器系の疾患','y2019']:.0f} → 2020 {g.loc['呼吸器系の疾患','y2020']:.0f} → 2023 {g.loc['呼吸器系の疾患','y2023']:.0f}億円")
(RES / "a167_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))

# 図1：シェアの変化（2011→2023、ポイント）
fig, ax = plt.subplots(figsize=(9.5, 6.2))
u = t.drop(index=["特殊目的用コード（コロナ）"]).sort_values("share_pt")
ax.barh(u.index, u.share_pt, color=[ORANGE if v > 0 else BLUE for v in u.share_pt])
for i, v in enumerate(u.share_pt):
    ax.text(v + (0.05 if v >= 0 else -0.05), i, f"{v:+.2f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-3.3, 2.5); ax.set_xlabel("医科診療医療費に占める割合の変化（ポイント、2011→2023年度）")
ax.set_title("シェアが最も伸びたのは「がんなど（新生物）」、最も下がったのは循環器と精神")
save(fig, "a167_share_change.png")

# 図2：主な分類のシェアの推移
fig, ax = plt.subplots(figsize=(9.5, 4.8))
keys = ["循環器系の疾患", "新生物＜腫瘍＞", "筋骨格系及び結合組織の疾患", "腎尿路生殖器系の疾患", "呼吸器系の疾患", "内分泌，栄養及び代謝疾患", "精神及び行動の障害"]
cols = [GRAY, ORANGE, GREEN, PURPLE, BLUE, "#c9a227", "#8c564b"]
for k, c in zip(keys, cols):
    ax.plot(yrs, sh.loc[k].values, color=c, lw=2.2 if k in ("新生物＜腫瘍＞", "循環器系の疾患") else 1.6, marker="o", ms=3)
    off = {"筋骨格系及び結合組織の疾患": 0.3, "呼吸器系の疾患": 0.1, "腎尿路生殖器系の疾患": -0.05, "内分泌，栄養及び代謝疾患": -0.15, "精神及び行動の障害": -0.1}.get(k, 0)
    ax.text(2023.2, sh.loc[k, "y2023"] + off, SHORT[k], color=c, fontsize=8.5, va="center")
ax.set_xlim(2011, 2026.6); ax.set_xticks(range(2011, 2024, 2)); ax.set_ylabel("医科診療医療費に占める割合（%）")
ax.set_title("循環器は20.8%から18.2%へ、がんなどは13.1%から15.0%へ")
save(fig, "a167_share_trend.png")

# 図3：伸び率と規模（2011→2023）
fig, ax = plt.subplots(figsize=(9.5, 5.0))
v = t.drop(index=["特殊目的用コード（コロナ）"])
ax.scatter(v.y2011_oku / 1e4, v.growth_pct, s=v.y2023_oku / 120, color=LIGHT, edgecolor=BLUE)
for n_, r in v.iterrows():
    if r.y2011_oku > 9000 or abs(r.growth_pct) > 40 or n_ == "感染症":
        ax.text(r.y2011_oku / 1e4 + 0.05, r.growth_pct, n_, fontsize=8.5, va="center")
ax.axhline((tot[b] / tot[a] - 1) * 100, color=ORANGE, lw=1, ls="--"); ax.text(5.6, (tot[b] / tot[a] - 1) * 100 + 1.2, f"全体 {(tot[b]/tot[a]-1)*100:+.0f}%", color=ORANGE, fontsize=9)
ax.set_xlabel("2011年度の医療費（兆円）"); ax.set_ylabel("2011→2023年度の伸び（%）")
ax.set_title("医療費の大きさと伸び（円の大きさは2023年度の医療費）")
save(fig, "a167_growth_size.png")
