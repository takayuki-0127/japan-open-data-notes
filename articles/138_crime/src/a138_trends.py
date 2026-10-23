"""刑法犯の認知件数（2007〜2025年）：包括罪種の推移、2007→2021年の減少と2021→2025年の増加の内訳"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load_counts, FIG, RES, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED

d = load_counts().fillna({"group": ""})
t1 = d[d.table == 1].pivot_table(index="year", columns="item", values="count")
t2 = d[d.table == 2].pivot_table(index="year", columns=["group", "item"], values="count")
Y = t1.index
tot = t1["刑法犯総数"]

# ---- 1. 包括罪種の推移 ----
cat = pd.DataFrame({
    "乗り物盗": t1["乗り物盗"], "侵入盗": t1["侵入盗"], "非侵入盗": t1["非侵入盗"],
    "粗暴犯": t1["粗暴犯"], "知能犯（詐欺など）": t1["知能犯"],
})
cat["その他（凶悪犯・風俗犯・器物損壊など）"] = tot - cat.sum(axis=1)
cat.to_csv(RES / "a138_categories.csv", encoding="utf-8-sig")
ymin = int(tot.idxmin())
summ = pd.DataFrame({"year": Y, "total": tot.values, "index_2007": (tot / tot.loc[2007] * 100).round(1).values})
summ.to_csv(RES / "a138_total.csv", index=False, encoding="utf-8-sig")
print("total 2007,min,2025:", tot.loc[2007], ymin, tot.loc[ymin], tot.loc[2025], "drop%", round((1 - tot.loc[ymin] / tot.loc[2007]) * 100, 1),
      "rise%", round((tot.loc[2025] / tot.loc[ymin] - 1) * 100, 1))

cols = [BLUE, LIGHT, "#5b8fd1", ORANGE, PURPLE, GRAY]
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ax.stackplot(Y, (cat / 1e4).T.values, labels=cat.columns, colors=cols, alpha=0.95)
ax.set_xlim(Y.min(), Y.max()); ax.set_ylabel("認知件数（万件）")
ax.set_title("刑法犯の認知件数（包括罪種別、2007〜2025年）")
ax.set_ylim(0, tot.max() / 1e4 * 1.12)
for y, dx, ha in ((2007, 6, "left"), (ymin, 0, "center"), (2025, -2, "right")):
    ax.annotate(f"{y}年 {tot.loc[y]/1e4:.1f}万件", (y, tot.loc[y] / 1e4), textcoords="offset points", xytext=(dx, 6), ha=ha, fontsize=10, color=INK)
ax.legend(loc="upper right", fontsize=9, frameon=False, bbox_to_anchor=(1.0, 0.93))
ax.text(0, -0.13, SOURCE + "。2007年は2008年分の資料の前年値", transform=ax.transAxes, fontsize=8, color=GRAY)
fig.savefig(FIG / "a138_trend.png"); plt.close(fig)

# ---- 2/3. 寄与の内訳（細かい手口・罪種） ----
def parts(y):
    s = {}
    s["自転車盗"] = t2[("乗り物盗", "自転車盗")].loc[y]
    s["オートバイ盗・自動車盗"] = t2[("乗り物盗", "オートバイ盗")].loc[y] + t2[("乗り物盗", "自動車盗")].loc[y]
    s["侵入盗（空き巣など）"] = t1["侵入盗"].loc[y]
    s["車上ねらい・部品ねらい"] = t2[("非侵入盗", "車上ねらい")].loc[y] + t2[("非侵入盗", "部品ねらい")].loc[y]
    s["自動販売機ねらい"] = t2[("非侵入盗", "自動販売機ねらい")].loc[y]
    s["万引き"] = t2[("非侵入盗", "万引き")].loc[y]
    s["置引き・ひったくり・すり"] = sum(t2[("非侵入盗", k)].loc[y] for k in ("置引き", "ひったくり", "すり"))
    s["その他の非侵入盗"] = t1["非侵入盗"].loc[y] - sum(s[k] for k in ("車上ねらい・部品ねらい", "自動販売機ねらい", "万引き", "置引き・ひったくり・すり"))
    s["器物損壊等"] = t1["うち)器物損壊等"].loc[y]
    s["占有離脱物横領"] = t1["うち)占有離脱物横領"].loc[y]
    s["詐欺"] = t1["詐欺"].loc[y]
    s["粗暴犯（暴行・傷害など）"] = t1["粗暴犯"].loc[y]
    s["その他"] = tot.loc[y] - sum(s.values())
    return pd.Series(s)


def contrib(a, b, fname):
    pa, pb = parts(a), parts(b)
    ch = (pb - pa)
    r = pd.DataFrame({f"{a}年": pa, f"{b}年": pb, "増減": ch, "全体の増減に占める割合(%)": (ch / ch.sum() * 100).round(1),
                      "増減率(%)": ((pb / pa - 1) * 100).round(1)})
    r.loc["合計"] = [pa.sum(), pb.sum(), ch.sum(), 100.0, round((pb.sum() / pa.sum() - 1) * 100, 1)]
    r.to_csv(RES / fname, encoding="utf-8-sig")
    print(r.to_string())
    return ch


def barh(ch, title, fname, a, b):
    ch = ch.sort_values()
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    c = [BLUE if v < 0 else ORANGE for v in ch.values]
    ax.barh(ch.index, ch.values / 1e4, color=c)
    span = (ch.max() - min(ch.min(), 0)) / 1e4
    for i, v in enumerate(ch.values):
        ax.text(v / 1e4 + (0.015 * span if v >= 0 else -0.015 * span), i, f"{v/1e4:+.1f}万", va="center",
                ha="left" if v >= 0 else "right", fontsize=9)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("認知件数の増減（万件）"); ax.set_title(title)
    lo, hi = min(ch.min(), 0) / 1e4, max(ch.max(), 0) / 1e4
    pad = (hi - lo) * 0.16
    ax.set_xlim(lo - pad, hi + pad)
    ax.text(0, -0.2, SOURCE, transform=ax.transAxes, fontsize=8, color=GRAY)
    fig.savefig(FIG / fname); plt.close(fig)


ch1 = contrib(2007, ymin, "a138_decline_2007_min.csv")
barh(ch1, f"2007→{ymin}年に何が減ったか（合計{ch1.sum()/1e4:.0f}万件）", "a138_decline.png", 2007, ymin)
ch2 = contrib(ymin, 2025, "a138_rise_min_2025.csv")
barh(ch2, f"{ymin}→2025年に何が増えたか（合計{ch2.sum()/1e4:+.1f}万件）", "a138_rise.png", ymin, 2025)

# 主要項目の各年
keep = pd.DataFrame({y: parts(y) for y in Y}).T
keep.insert(0, "刑法犯総数", tot)
keep.to_csv(RES / "a138_items_by_year.csv", encoding="utf-8-sig")
print(keep.loc[[2007, 2015, 2019, 2021, 2022, 2023, 2024, 2025]].round(0).to_string())
