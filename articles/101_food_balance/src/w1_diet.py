"""W1：国民1人・1年当たり供給純食料（kg）と1日当たり供給熱量（kcal）の長期推移（1960〜2024年度）"""
from common import *

kg, kc = wide("kg"), wide("kcal")
Y0, Y1 = 1960, int(kg.index.max())
ITEMS = {"米": "穀類_米", "小麦": "穀類_小麦", "いも類": "いも類", "大豆": "豆類_大豆", "野菜": "野菜", "果実": "果実",
         "肉類": "肉類", "牛肉": "肉類_牛肉", "豚肉": "肉類_豚肉", "鶏肉": "肉類_鶏肉", "鶏卵": "鶏卵",
         "牛乳・乳製品": "牛乳及び乳製品", "魚介類": "魚介類", "砂糖類": "砂糖類", "油脂類": "油脂類",
         "みそ": "みそ", "しょうゆ": "しょうゆ"}

# 1. 品目別：1960年度・ピーク・最新年度
rows = []
for name, col in ITEMS.items():
    s = kg[col].dropna()
    rows.append({"品目": name, f"{Y0}年度kg": s.loc[Y0], "ピーク年度": int(s.idxmax()), "ピークkg": s.max(),
                 f"{Y1}年度kg": s.loc[Y1], f"倍率_{Y1}/{Y0}": s.loc[Y1] / s.loc[Y0], f"ピーク比_{Y1}": s.loc[Y1] / s.max()})
tab = pd.DataFrame(rows)
tab.round(3).to_csv(RES / "w1_items.csv", index=False, encoding="utf-8-sig")
print(tab.round(2).to_string(index=False))

# 長い形の推移も保存
long = kg[[c for c in ITEMS.values()]].rename(columns={v: k for k, v in ITEMS.items()})
long.to_csv(RES / "w1_kg_per_person.csv", encoding="utf-8-sig")

# 2. 熱量の構成（1日当たり kcal）
GROUPS = {"米": ["穀類_米"], "小麦・その他の穀物": ["穀類_小麦", "穀類_大麦", "穀類_はだか麦", "穀類_とうもろこし", "穀類_こうりゃん", "穀類_その他の雑穀"],
          "畜産物（肉・卵・乳）": ["肉類", "鶏卵", "牛乳及び乳製品"], "油脂類": ["油脂類"], "砂糖類": ["砂糖類"],
          "魚介類": ["魚介類"], "いも・でん粉": ["いも類", "でん粉"], "豆類・みそ・しょうゆ": ["豆類", "みそ", "しょうゆ"],
          "野菜・果実・その他": ["野菜", "果実", "海藻類", "その他食料計"]}
comp = pd.DataFrame({g: kc[c].fillna(0).sum(1) for g, c in GROUPS.items()})
comp["合計"] = kc["合計"]
comp["差（その他）"] = comp["合計"] - comp[list(GROUPS)].sum(1)
comp.round(1).to_csv(RES / "w1_kcal_groups.csv", encoding="utf-8-sig")
share = comp[list(GROUPS)].div(comp["合計"], axis=0) * 100
print("\n1日当たり供給熱量", comp.loc[[1960, 1965, 1990, 1996, Y1], "合計"].round(0).to_dict(),
      "ピーク", int(comp["合計"].idxmax()), round(comp["合計"].max(), 1))
print("構成比（%）\n", share.loc[[1960, 1990, Y1]].round(1).T.to_string())
print("差の最大", comp["差（その他）"].abs().max().round(2))

def labels(ax, items, gap):
    """線の右端に名前を置く（重ならないように上下にずらす）"""
    ys = sorted([(long[n].iloc[-1], n, c) for n, c in items])
    pos = []
    for y, n, c in ys:
        y2 = max(y, pos[-1] + gap) if pos else y
        pos.append(y2); ax.text(Y1 + 0.8, y2, n, color=c, va="center")


# 図1：主な品目の推移（実数、2枚）
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
ax = axes[0]
for name, c in [("米", BLUE), ("野菜", GREEN), ("牛乳・乳製品", PURPLE), ("小麦", ORANGE)]:
    ax.plot(long.index, long[name], color=c, lw=2)
labels(ax, [("米", BLUE), ("野菜", GREEN), ("牛乳・乳製品", PURPLE), ("小麦", ORANGE)], 6)
ax.set_title("1人1年当たり供給純食料（kg）：多い品目"); ax.set_xlim(Y0, Y1 + 12); ax.set_ylim(0)
ax = axes[1]
for name, c in [("魚介類", BLUE), ("肉類", RED), ("果実", GREEN), ("砂糖類", GRAY), ("鶏卵", ORANGE), ("油脂類", PURPLE)]:
    ax.plot(long.index, long[name], color=c, lw=2)
labels(ax, [("魚介類", BLUE), ("肉類", RED), ("果実", GREEN), ("砂糖類", GRAY), ("鶏卵", ORANGE), ("油脂類", PURPLE)], 2.2)
ax.set_title("同：少ない品目"); ax.set_xlim(Y0, Y1 + 12); ax.set_ylim(0)
for a in axes: a.set_xlabel("年度")
fig.text(0, -0.03, SOURCE + "。2024年度は概算値", fontsize=8, color=GRAY)
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# 図2：1960年度→最新年度の倍率（対数軸）
t = tab.set_index("品目")[f"倍率_{Y1}/{Y0}"].sort_values()
fig, ax = plt.subplots(figsize=(8, 6))
cols = [RED if v >= 1 else BLUE for v in t]
ax.barh(t.index, t.values, color=cols); ax.set_xscale("log"); ax.axvline(1, color=INK, lw=1)
for i, v in enumerate(t.values):
    ax.text(v * (1.08 if v >= 1 else 0.92), i, f"{v:.2f}倍", va="center", ha="left" if v >= 1 else "right", fontsize=9)
ax.set_xticks([0.25, 0.5, 1, 2, 4, 8, 16]); ax.set_xticklabels(["0.25", "0.5", "1", "2", "4", "8", "16"])
ax.set_xlim(0.15, 40)
ax.set_title(f"1人1年当たり供給純食料：{Y0}年度→{Y1}年度の倍率")
fig.text(0, -0.03, SOURCE + "。2024年度は概算値", fontsize=8, color=GRAY)
fig.savefig(FIG / "w1_ratio.png"); plt.close(fig)

# 図3：1日当たり供給熱量の構成
fig, ax = plt.subplots(figsize=(10, 5))
pal = [BLUE, LIGHT, RED, ORANGE, GRAY, "#5fa8d3", "#c9a227", GREEN, "#b6d7a8"]
ax.stackplot(comp.index, [comp[g] for g in GROUPS], labels=list(GROUPS), colors=pal, alpha=0.95)
ax.set_ylabel("kcal／人・日"); ax.set_xlim(Y0, Y1); ax.set_xlabel("年度")
ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False, fontsize=9)
ax.set_title("国民1人・1日当たり供給熱量の内訳")
fig.text(0, -0.03, SOURCE + "。2024年度は概算値", fontsize=8, color=GRAY)
fig.savefig(FIG / "w1_kcal.png"); plt.close(fig)
