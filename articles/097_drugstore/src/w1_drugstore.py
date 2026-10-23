"""W1：ドラッグストアは百貨店・スーパーをどれだけ追い上げたか（業態別の販売額、2014〜2025年）

- 水準（販売額）には調査対象の見直しによる断層があるので、伸びは公表の前年比をつないだ指数（2014年＝100）で比べる
- 2025年の販売額は、同じ年の公表値どうしで比べる
- ドラッグストアの商品別の構成比は、同じ年の中の比なので断層の影響が小さい
"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, chain_annual, note, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, PURPLE, RED, LIGHT

v, y = load("annual_value"), load("annual_yoy")
GYO = {"百貨店": "百貨店|合計", "スーパー": "スーパー|合計", "コンビニ": "コンビニ|商品販売額",
       "ドラッグストア": "ドラッグストア|商品販売額", "ホームセンター": "ホームセンター|商品販売額", "家電大型専門店": "家電大型専門店|商品販売額"}
COL = {"百貨店": PURPLE, "スーパー": BLUE, "コンビニ": GREEN, "ドラッグストア": ORANGE, "ホームセンター": GRAY, "家電大型専門店": INK}

# 1) 業態別：2025年の販売額と、前年比をつないだ指数
rows = []
idx = {}
for k, col in GYO.items():
    ix = chain_annual(y[col], 2014).loc[2014:2025]
    idx[k] = ix
    rows.append({"業態": k, "販売額2014_兆円": v.loc[2014, col] / 1e6, "販売額2019_兆円": v.loc[2019, col] / 1e6,
                 "販売額2025_兆円": v.loc[2025, col] / 1e6, "指数2019": ix[2019], "指数2025": ix[2025],
                 "年率_2014_2025": ((ix[2025] / 100) ** (1 / 11) - 1) * 100})
tab = pd.DataFrame(rows)
tab.round(2).to_csv(RES / "w1_by_format.csv", index=False, encoding="utf-8")
pd.DataFrame(idx).round(1).to_csv(RES / "w1_index_2014eq100.csv", encoding="utf-8")
print(tab.round(2).to_string(index=False))

# 店舗数・1店当たり
st = v.loc[2014:2025, "ドラッグストア|店舗数"]
per = v.loc[2014:2025, "ドラッグストア|商品販売額"] / st / 100  # 億円
print("ドラッグストア店舗数", st[2014], "→", st[2025], " 1店当たり(億円)", round(per[2014], 2), "→", round(per[2025], 2))

# 2) ドラッグストアの商品別構成比
items = [c for c in v.columns if c.startswith("ドラッグストア|") and c not in ("ドラッグストア|商品販売額", "ドラッグストア|店舗数")]
mix = v.loc[2014:2025, items].div(v.loc[2014:2025, "ドラッグストア|商品販売額"], axis=0) * 100
mix.columns = [c.split("|")[1] for c in mix.columns]
mix.round(2).to_csv(RES / "w1_drugstore_mix.csv", encoding="utf-8")
print(mix.loc[[2014, 2019, 2025]].round(1).T.to_string())

# 3) 食品の売上：業態ごとの指数（2014年＝100）と2025年の金額
FOOD = {"スーパー（飲食料品）": "スーパー|飲食料品", "コンビニ（FF・日配＋加工食品）": None,
        "ドラッグストア（食品）": "ドラッグストア|食品", "百貨店（飲食料品）": "百貨店|飲食料品"}
fidx, frow = {}, []
for k, col in FOOD.items():
    if col is None:  # コンビニは2系列の前年比を前年の金額で重み付け
        a, b = "コンビニ|FF・日配食品", "コンビニ|加工食品"
        ia, ib = chain_annual(y[a], 2014), chain_annual(y[b], 2014)
        w = v.loc[2014, a] / (v.loc[2014, a] + v.loc[2014, b])
        ix = (w * ia + (1 - w) * ib).loc[2014:2025]
        amt = (v.loc[2025, a] + v.loc[2025, b])
    else:
        ix = chain_annual(y[col], 2014).loc[2014:2025]
        amt = v.loc[2025, col]
    fidx[k] = ix
    frow.append({"業態": k, "食品の販売額2025_兆円": amt / 1e6, "指数2019": ix[2019], "指数2025": ix[2025]})
ftab = pd.DataFrame(frow)
ftab.round(2).to_csv(RES / "w1_food_by_format.csv", index=False, encoding="utf-8")
print(ftab.round(2).to_string(index=False))

# 図1：業態別の指数
fig, ax = plt.subplots(figsize=(8, 4.8))
for k, ix in idx.items():
    ax.plot(ix.index, ix.values, color=COL[k], lw=2.4 if k == "ドラッグストア" else 1.6)
    ax.annotate(f"{k} {ix[2025]:.0f}", (2025.15, ix[2025]), color=COL[k], fontsize=10, va="center")
ax.axhline(100, color=GRAY, lw=0.8)
ax.set_xlim(2014, 2028.2); ax.set_xticks(range(2014, 2026, 2))
ax.set_title("業態別の販売額（2014年＝100、公表の前年比をつないだ指数、名目）", loc="left")
note(ax, "商品販売額（コンビニはサービス売上を除く）。" + "出典：経済産業省「商業動態統計」（e-Stat）を加工して作成", -0.1)
fig.savefig(FIG / "w1_index.png"); plt.close(fig)

# 図2：ドラッグストアの商品構成
order = ["食品", "家庭用品・日用消耗品・ペット用品", "ビューティケア（化粧品・小物）", "ＯＴＣ医薬品", "調剤医薬品", "トイレタリー",
         "ヘルスケア用品（衛生用品）・介護・ベビー", "健康食品", "その他"]
short = {"家庭用品・日用消耗品・ペット用品": "家庭用品・日用品・ペット", "ビューティケア（化粧品・小物）": "化粧品など",
         "ヘルスケア用品（衛生用品）・介護・ベビー": "衛生用品・介護・ベビー", "ＯＴＣ医薬品": "市販薬（OTC）", "調剤医薬品": "調剤"}
fig, ax = plt.subplots(figsize=(8, 4.8))
yy = np.arange(len(order))[::-1]
ax.barh(yy + 0.2, mix.loc[2014, order], height=0.38, color=LIGHT, label="2014年")
ax.barh(yy - 0.2, mix.loc[2025, order], height=0.38, color=ORANGE, label="2025年")
for i, o in zip(yy, order):
    ax.text(mix.loc[2025, o] + 0.4, i - 0.2, f"{mix.loc[2025, o]:.1f}%", va="center", fontsize=9)
    ax.text(mix.loc[2014, o] + 0.4, i + 0.2, f"{mix.loc[2014, o]:.1f}%", va="center", fontsize=9, color=GRAY)
ax.set_yticks(yy); ax.set_yticklabels([short.get(o, o) for o in order])
ax.legend(frameon=False, loc="lower right")
ax.set_title("ドラッグストアの商品別の割合（商品販売額に占める%）", loc="left")
note(ax, "調剤は2019年に調査対象の見直しで割合が上がった。出典：経済産業省「商業動態統計」（e-Stat）を加工して作成", -0.1)
fig.savefig(FIG / "w1_drugstore_mix.png"); plt.close(fig)

# 図3：食品の売上の伸び
FCOL = {"スーパー（飲食料品）": BLUE, "コンビニ（FF・日配＋加工食品）": GREEN, "ドラッグストア（食品）": ORANGE, "百貨店（飲食料品）": PURPLE}
fig, ax = plt.subplots(figsize=(8, 4.8))
for k, ix in fidx.items():
    ax.plot(ix.index, ix.values, color=FCOL[k], lw=2.4 if "ドラッグ" in k else 1.6)
    off = {"スーパー（飲食料品）": 4, "コンビニ（FF・日配＋加工食品）": -4}.get(k, 0)
    ax.annotate(f"{k.split('（')[0]} {ix[2025]:.0f}", (2025.15, ix[2025] + off), color=FCOL[k], fontsize=10, va="center")
ax.axhline(100, color=GRAY, lw=0.8)
ax.set_xlim(2014, 2027.6); ax.set_xticks(range(2014, 2026, 2))
ax.set_title("食品の販売額（2014年＝100、名目）", loc="left")
note(ax, "コンビニは FF・日配食品と加工食品の合計。出典：経済産業省「商業動態統計」（e-Stat）を加工して作成", -0.1)
fig.savefig(FIG / "w1_food.png"); plt.close(fig)
