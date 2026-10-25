"""A215 国民医療費の伸びを、人口の数・年齢構成・年齢ごとの一人当たり医療費に分ける（LMDI法、1997〜2023年度）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import load, GROUPS, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

C, N, T = load()
Nt = N.sum(axis=1); S = N.div(Nt, axis=0); PC = C / N * 10  # 一人当たり（万円）：億円/千人=10万円 → ×10で万円
L = lambda a, b: np.where(np.isclose(a, b), a, (a - b) / (np.log(a) - np.log(b)))

def lmdi(y0, y1):
    w = L(C.loc[y1].values, C.loc[y0].values)
    pop = (w * np.log(Nt[y1] / Nt[y0])).sum(); st = (w * np.log(S.loc[y1] / S.loc[y0])).sum(); pc = (w * np.log(PC.loc[y1] / PC.loc[y0])).sum()
    return pd.Series({"total": C.loc[y1].sum() - C.loc[y0].sum(), "pop": pop, "structure": st, "percap": pc})

ann = pd.DataFrame({y: lmdi(y - 1, y) for y in range(1998, 2024)}).T
ann_pct = ann.div(C.sum(axis=1).shift(1).loc[ann.index], axis=0) * 100
cum = ann.loc[2001:].cumsum()  # 2000年度起点
ann.round(0).to_csv(RES / "lmdi_annual_oku.csv"); ann_pct.round(3).to_csv(RES / "lmdi_annual_pct.csv"); cum.round(0).to_csv(RES / "lmdi_cumulative_from2000_oku.csv")
pd.concat([C.add_prefix("cost_"), N.round(0).add_prefix("pop_"), PC.round(2).add_prefix("pc_")], axis=1).to_csv(RES / "cost_pop_percap_by_age.csv")
per = {}
for a, b in [(2000, 2010), (2010, 2019), (2019, 2023), (2000, 2023)]:
    per[f"{a}-{b}"] = lmdi(a, b)
per = pd.DataFrame(per).T; per.round(0).to_csv(RES / "lmdi_periods_oku.csv")

O = []
t0, t1 = C.loc[2000].sum(), C.loc[2023].sum()
O.append(f"国民医療費 1997 {C.loc[1997].sum()/1e4:.2f}兆円, 2000 {t0/1e4:.2f}兆円 → 2023 {t1/1e4:.2f}兆円（+{(t1/t0-1)*100:.1f}%、+{(t1-t0)/1e4:.2f}兆円）")
for k, r in per.iterrows():
    O.append(f"{k}: 増加 {r.total/1e4:+.2f}兆円 = 人口の数 {r['pop']/1e4:+.2f} + 年齢構成 {r.structure/1e4:+.2f} + 一人当たり {r.percap/1e4:+.2f}（構成比 人口{r['pop']/r.total*100:.0f}%・年齢{r.structure/r.total*100:.0f}%・単価{r.percap/r.total*100:.0f}%）")
for a, b in [(2000, 2010), (2010, 2019), (2019, 2023), (2000, 2023)]:
    r = ann.loc[a + 1:b].sum()
    O.append(f"[年ごとに分けて累積] {a}-{b}: 増加 {r.total/1e4:+.2f}兆円 = 人口の数 {r['pop']/1e4:+.2f} + 年齢構成 {r.structure/1e4:+.2f} + 一人当たり {r.percap/1e4:+.2f}（年齢{r.structure/r.total*100:.0f}%・単価{r.percap/r.total*100:.0f}%・人口{r['pop']/r.total*100:.0f}%）")
O.append("年平均の寄与（2000→2023、%/年）: " + ", ".join(f"{k} {ann_pct.loc[2001:, k].mean():.2f}" for k in ["total", "pop", "structure", "percap"]))
O.append(f"年齢構成の寄与がプラスの年: {(ann.loc[2001:,'structure']>0).sum()}/{len(ann.loc[2001:])}、一人当たりがマイナスの年: {list(ann.index[(ann.percap<0)])}")
O.append(f"75歳以上の人口割合 2000 {S.loc[2000,'75+']*100:.1f}% → 2023 {S.loc[2023,'75+']*100:.1f}%、医療費に占める割合 {C.loc[2000,'75+']/t0*100:.1f}% → {C.loc[2023,'75+']/t1*100:.1f}%")
O.append("年齢別一人当たり（万円）2000→2023: " + ", ".join(f"{g} {PC.loc[2000,g]:.1f}→{PC.loc[2023,g]:.1f}（{(PC.loc[2023,g]/PC.loc[2000,g]-1)*100:+.0f}%）" for g in GROUPS))
O.append(f"全体の一人当たり 2000 {t0/Nt[2000]*10:.1f}万円 → 2023 {t1/Nt[2023]*10:.1f}万円（{(t1/Nt[2023]/(t0/Nt[2000])-1)*100:+.0f}%）、人口 {Nt[2000]/10:.0f}万→{Nt[2023]/10:.0f}万人")
O.append("年ごとの寄与（%）: " + "; ".join(f"{y}: 計{r.total:+.1f} 人{r['pop']:+.1f} 構{r.structure:+.1f} 単{r.percap:+.1f}" for y, r in ann_pct.iterrows()))
open(RES / "summary.txt", "w").write("\n".join(O) + "\n"); print("\n".join(O))

cols = ["#a9c9ef", "#6fa6e3", "#2a78d6", "#f4c19a", "#eb9a6a", "#c4471d"]
names = {"0-14": "0〜14歳", "15-44": "15〜44歳", "45-64": "45〜64歳", "65-69": "65〜69歳", "70-74": "70〜74歳", "75+": "75歳以上"}
fig, ax = plt.subplots(figsize=(9, 5))
ax.stackplot(C.index, *[C[g] / 1e4 for g in GROUPS], colors=cols, labels=[names[g] for g in GROUPS])
cs = (C / 1e4).cumsum(axis=1)
for g in GROUPS:
    ax.text(2023.3, cs[g].iloc[-1] - C[g].iloc[-1] / 2e4, f"{names[g]} {C[g].iloc[-1]/1e4:.1f}", va="center", fontsize=9)
ax.axvline(2000, color=GRAY, lw=0.8, ls=":"); ax.text(2000.2, 47, "介護保険の開始", fontsize=8, color=GRAY)
ax.set_xlim(1997, 2023); ax.set_ylim(0, 50); ax.set_ylabel("兆円"); ax.set_xticks(range(1998, 2024, 3))
ax.set_title(f"国民医療費の年齢別の内訳（{C.loc[1997].sum()/1e4:.1f}兆円 → {t1/1e4:.1f}兆円）")
fig.text(0.01, -0.02, SOURCE, fontsize=8, color=GRAY); fig.savefig(FIG / "a215_total.png"); plt.close()

fig, ax = plt.subplots(figsize=(9, 5))
z = pd.concat([pd.DataFrame(0, index=[2000], columns=cum.columns), cum]) / 1e4
for k, c, n in [("total", INK, "増えた額（合計）"), ("percap", BLUE, "年齢ごとの一人当たり医療費"), ("structure", ORANGE, "年齢構成（高齢化）"), ("pop", GRAY, "人口の数")]:
    ax.plot(z.index, z[k], color=c, lw=2.4 if k != "pop" else 1.8, ls="--" if k == "total" else "-")
    ax.text(2023.3, z[k].iloc[-1], f"{n} {z[k].iloc[-1]:+.1f}", va="center", fontsize=9, color=c)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xlim(2000, 2030); ax.set_xticks(range(2000, 2024, 4))
ax.set_ylabel("2000年度からの増加（兆円）"); ax.set_title("医療費の増加を3つに分ける（2000年度起点の累積）")
fig.text(0.01, -0.02, SOURCE + "。LMDI法による要因分解（年ごとに分けて累積）", fontsize=8, color=GRAY); fig.savefig(FIG / "a215_decomp.png"); plt.close()

fig, ax = plt.subplots(figsize=(9, 5))
d = ann_pct.loc[2001:]
x = np.array(d.index)
pos = lambda s: s.clip(lower=0); neg = lambda s: s.clip(upper=0)
bp = np.zeros(len(d)); bn = np.zeros(len(d))
for k, c, n in [("structure", ORANGE, "年齢構成"), ("percap", BLUE, "一人当たり"), ("pop", GRAY, "人口の数")]:
    ax.bar(x, pos(d[k]), bottom=bp, color=c, label=n, width=0.7); bp += pos(d[k]).values
    ax.bar(x, neg(d[k]), bottom=bn, color=c, width=0.7); bn += neg(d[k]).values
ax.plot(x, d.total, color=INK, marker="o", ms=4, lw=1.2, label="前年度からの伸び率（合計）")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(range(2001, 2024, 2)); ax.set_ylabel("前年度比（%）")
ax.legend(frameon=False, ncol=4, loc="upper left", fontsize=9); ax.set_ylim(-4.5, 7.5)
ax.set_title("毎年の伸び率の内訳：年齢構成は毎年+1%前後を押し上げている")
fig.text(0.01, -0.02, SOURCE + "。LMDI法", fontsize=8, color=GRAY); fig.savefig(FIG / "a215_annual.png"); plt.close()
