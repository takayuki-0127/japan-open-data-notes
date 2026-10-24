"""勤務間インターバル制度の導入率は、企業規模でどれだけ違うか（就労条件総合調査 2018〜2025年）"""
from common import *

t, d = load()
w = t.pivot(index="survey_year", columns="size", values="adopted")[["計"] + SIZES]
w.to_csv(RES / "a200_adopted_by_size.csv", encoding="utf-8")
L = []
for y in [2018, 2025]:
    r = w.loc[y]
    L.append(f"{y}年調査 導入している企業: 計 {r['計']}%、" + "、".join(f"{s} {r[s]}%" for s in SIZES) + f"（1000人以上÷30～99人 {r['1000人以上']/r['30～99人']:.1f}倍、差 {r['1000人以上']-r['30～99人']:.1f}pt）")
L.append("1000人以上と30～99人の差(pt): " + "、".join(f"{y} {w.loc[y,'1000人以上']-w.loc[y,'30～99人']:.1f}" for y in w.index))
L.append("倍率: " + "、".join(f"{y} {w.loc[y,'1000人以上']/w.loc[y,'30～99人']:.1f}" for y in w.index))
x = t[t.survey_year == 2025].set_index("size")
for s in ["計"] + SIZES:
    L.append(f"2025 {s}: 導入 {x.loc[s,'adopted']}% 予定・検討 {x.loc[s,'planning']}% 予定なし {x.loc[s,'not_planned']}%、導入企業の平均間隔 {int(x.loc[s,'avg_interval_h'])}時間{int(x.loc[s,'avg_interval_min'])}分")
dd = d.set_index("item")
ind = d[d.group == "industry"].set_index("item").sort_values("adopted", ascending=False)
L.append("2025 産業別 導入 上位: " + "、".join(f"{k} {v}%" for k, v in ind.adopted.head(4).items()) + " / 下位: " + "、".join(f"{k} {v}%" for k, v in ind.adopted.tail(4).items()))
m = d[d.group == "manufacturing_size"].set_index("item")
L.append("製造業 規模別 導入: " + "、".join(f"{k} {v}%" for k, v in m.adopted.items()))
s = d[d.group == "size"].set_index("item")
s11 = (s.h11 + s.gt11h)
L.append("2025 導入企業のうち11時間以上の割合（11時間＋11時間超）÷導入: " + "、".join(f"{k} {s11[k]/s.adopted[k]:.0%}" for k in s.index))
(RES / "a200_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

COL = {"計": INK, "1000人以上": BLUE, "300～999人": GREEN, "100～299人": PURPLE, "30～99人": ORANGE}
fig, ax = plt.subplots(figsize=(9, 5))
for c in ["計"] + SIZES:
    ax.plot(w.index, w[c], color=COL[c], lw=2.4 if c in ("1000人以上", "30～99人") else 1.4, ls="--" if c == "計" else "-", marker="o", ms=4)
    ax.text(2025.15, w.loc[2025, c] + {"計": -0.15, "100～299人": 0.35, "30～99人": -0.35}.get(c, 0), f"{c} {w.loc[2025,c]}%", color=COL[c], va="center", fontsize=9)
ax.set_xlim(2017.7, 2026.6); ax.set_ylim(0); ax.set_xticks(w.index)
ax.set_xlabel("調査年（各年1月1日現在）"); ax.set_ylabel("導入している企業の割合（%）")
ax.set_title("勤務間インターバル制度を導入している企業の割合（企業規模別）")
save(fig, "a200_trend.png")

fig, ax = plt.subplots(figsize=(9, 4.2))
rows = ["計"] + SIZES; ys = np.arange(len(rows))[::-1]
left = np.zeros(len(rows))
for col, lab, c in [("adopted", "導入している", BLUE), ("planning", "導入を予定・検討している", LIGHT), ("not_planned", "予定も検討もない", "#dddddd")]:
    v = x.loc[rows, col].values
    ax.barh(ys, v, left=left, color=c, height=0.62, label=lab)
    for yy, l, vv in zip(ys, left, v):
        if vv >= 4:
            ax.text(l + vv / 2, yy, f"{vv:.1f}", ha="center", va="center", fontsize=9, color="white" if c == BLUE else INK)
    left += v
ax.set_yticks(ys); ax.set_yticklabels(rows); ax.set_xlim(0, 100); ax.set_xlabel("企業の割合（%）")
ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=9)
ax.set_title("勤務間インターバル制度の導入状況（2025年調査）", pad=26)
save(fig, "a200_status_2025.png")

o = ind.adopted.sort_values()
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(range(len(o)), o.values, color=[ORANGE if v >= 10 else BLUE for v in o.values], height=0.7)
for i, v in enumerate(o.values):
    ax.text(v + 0.2, i, f"{v:.1f}", va="center", fontsize=8.5)
ax.axvline(x.loc["計", "adopted"], color=INK, ls="--", lw=1); ax.text(x.loc["計", "adopted"] + 0.2, len(o) - 0.4, f"全体 {x.loc['計','adopted']}%", fontsize=9)
ax.set_yticks(range(len(o))); ax.set_yticklabels(o.index, fontsize=9); ax.set_xlabel("導入している企業の割合（%）")
ax.set_title("勤務間インターバル制度の導入率（産業別、2025年調査）")
save(fig, "a200_industry.png")
