"""664 平均単価の前年比を、品目の構成の変化と単価の変化に分けると、それぞれどれだけになるのか

架空の店の12品目（3分類×4品目）の、2024年と2025年の数量と単価。平均単価＝売上÷数量。
2025年は高い品目の数量が増え（構成の変化）、単価も上がった。とくに高い品目ほど値上げが大きい。
平均単価の差を、単価の効果と構成（ミックス）の効果に分ける。
  価格を先に：単価＝Σ s0(p1−p0)、構成＝Σ(s1−s0)p1
  構成を先に：構成＝Σ(s1−s0)p0、単価＝Σ s1(p1−p0)
  両方の平均（対称）
品目の単位と分類の単位でも比べる。DuckDB（1スレッド）と pandas の一致を確かめる。seed 664。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の店の12品目の数量と単価（作成者が乱数で作成、seed 664）"
rng = np.random.default_rng(664)
cats = {"飲み物": [120, 160, 220, 380], "総菜": [280, 420, 560, 780], "弁当": [450, 580, 720, 980]}
rows = []
for c, prices in cats.items():
    for k, p0 in enumerate(prices):
        q0 = int(rng.normal(9000, 800) * (p0 / 300) ** -0.9)
        tier = k / 3  # 0＝分類の中で安い、1＝高い
        dq = 1 + (-0.12 + 0.30 * tier) + rng.normal(0, 0.03)
        dp = 1 + (0.01 + 0.07 * tier) + rng.normal(0, 0.005)
        p1 = round(p0 * dp)
        rows += [(f"{c}{k + 1}", c, 2024, q0, p0), (f"{c}{k + 1}", c, 2025, int(q0 * dq), p1)]
I = pd.DataFrame(rows, columns=["item", "category", "year", "qty", "price"])
# 分類の構成も少し変える：弁当が増える
I.loc[(I.year == 2025) & (I.category == "弁当"), "qty"] = (I.loc[(I.year == 2025) & (I.category == "弁当"), "qty"] * 1.08).astype(int)
I.to_csv(DATA / "items.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("items", I)
qs = [x for x in (SQL / "02_mix_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
Di = con.execute(qs[0]).df().iloc[0]; Dc = con.execute(qs[1]).df().iloc[0]

def decomp(df, key):
    g = df.groupby([key, "year"]).apply(lambda d: pd.Series({"qty": d.qty.sum(), "sales": (d.qty * d.price).sum()}), include_groups=False).reset_index()
    g["price"] = g.sales / g.qty; g["share"] = g.qty / g.groupby("year").qty.transform("sum")
    w = g[g.year == 2024].set_index(key)[["share", "price"]].join(g[g.year == 2025].set_index(key)[["share", "price"]], lsuffix="0", rsuffix="1")
    s0, s1, p0, p1 = w.share0, w.share1, w.price0, w.price1
    r = {"avg0": (s0 * p0).sum(), "avg1": (s1 * p1).sum(),
         "price_first_price": (s0 * (p1 - p0)).sum(), "price_first_mix": ((s1 - s0) * p1).sum(),
         "mix_first_price": (s1 * (p1 - p0)).sum(), "mix_first_mix": ((s1 - s0) * p0).sum(),
         "interaction": ((s1 - s0) * (p1 - p0)).sum()}
    r["sym_price"] = (r["price_first_price"] + r["mix_first_price"]) / 2; r["sym_mix"] = (r["price_first_mix"] + r["mix_first_mix"]) / 2
    return r, w
Ri, Wi = decomp(I, "item"); Rc, Wc = decomp(I, "category")
for k in ["avg0", "avg1", "price_first_price", "price_first_mix", "mix_first_price", "mix_first_mix", "interaction"]:
    assert np.isclose(Ri[k], Di[k]), k
for k in ["price_first_price", "price_first_mix", "mix_first_price", "mix_first_mix"]:
    assert np.isclose(Rc[k], Dc[k]), k
Wi.round(5).to_csv(RES / "by_item.csv"); Wc.round(5).to_csv(RES / "by_category.csv")
d = Ri["avg1"] - Ri["avg0"]
pct = lambda v: round(v / Ri["avg0"] * 100, 2)
out = {"avg_price_2024": round(Ri["avg0"], 2), "avg_price_2025": round(Ri["avg1"], 2), "change_yen": round(d, 2), "change_pct": pct(d),
       "simple_price_index_pct": round(float(((Wi.price1 / Wi.price0) * Wi.share0).sum() * 100 - 100), 2),
       "qty_change_pct": round(float(I[I.year == 2025].qty.sum() / I[I.year == 2024].qty.sum() * 100 - 100), 2),
       "item_level": {"price_first": {"price": pct(Ri["price_first_price"]), "mix": pct(Ri["price_first_mix"])},
                      "mix_first": {"price": pct(Ri["mix_first_price"]), "mix": pct(Ri["mix_first_mix"])},
                      "symmetric": {"price": pct(Ri["sym_price"]), "mix": pct(Ri["sym_mix"])},
                      "interaction": pct(Ri["interaction"])},
       "category_level": {"price_first": {"price": pct(Rc["price_first_price"]), "mix": pct(Rc["price_first_mix"])},
                          "mix_first": {"price": pct(Rc["mix_first_price"]), "mix": pct(Rc["mix_first_mix"])},
                          "symmetric": {"price": pct(Rc["sym_price"]), "mix": pct(Rc["sym_mix"])}}}
out["item_level"]["mix_share_of_change_sym"] = round(Ri["sym_mix"] / d * 100, 1)
out["category_level"]["mix_share_of_change_sym"] = round(Rc["sym_mix"] / d * 100, 1)
json.dump(out, open(RES / "a664_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：品目ごとの数量の伸びと値上げ
fig, ax = plt.subplots(figsize=(8.5, 3.8))
dq = (Wi.share1 / Wi.share0 - 1) * 100; dp = (Wi.price1 / Wi.price0 - 1) * 100
colors = {"飲み物": BLUE, "総菜": GREEN, "弁当": ORANGE}
for c in cats:
    m = Wi.index.str.startswith(c)
    ax.scatter(Wi.price0[m], dq[m], s=20 + dp[m] * 25, color=colors[c], label=c, alpha=0.85)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xlabel("2024年の単価（円）"); ax.set_ylabel("数量の割合の変化（%）")
leg = ax.legend(frameon=False, fontsize=9, title="点の大きさ＝値上げ率", title_fontsize=8)
for h in leg.legend_handles:
    h.set_sizes([40])
ax.set_title("高い品目ほど、数量の割合が増え、値上げも大きい")
save(fig, "a664_items.png", SRC)
# 図2：分け方の順番
fig, ax = plt.subplots(figsize=(8.5, 3.4))
lab = ["価格を先に", "両方の平均", "構成を先に"]
pr = [out["item_level"][k]["price"] for k in ["price_first", "symmetric", "mix_first"]]
mx = [out["item_level"][k]["mix"] for k in ["price_first", "symmetric", "mix_first"]]
ax.barh(lab[::-1], pr[::-1], color=BLUE, label="単価の効果")
ax.barh(lab[::-1], mx[::-1], left=pr[::-1], color=ORANGE, label="構成の効果")
for i, (a, b) in enumerate(zip(pr[::-1], mx[::-1])):
    ax.text(a / 2, i, f"{a:+.2f}", ha="center", va="center", color="white", fontsize=9)
    ax.text(a + b / 2, i, f"{b:+.2f}", ha="center", va="center", color="white", fontsize=9)
ax.set_xlabel(f"平均単価の前年比への寄与（ポイント、合計 {out['change_pct']:+.2f}%）"); ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
ax.set_xlim(0, out["change_pct"] * 1.05)
ax.set_title("どちらを先に分けるかで、単価と構成の取り分が変わる", pad=22)
save(fig, "a664_order.png", SRC, y=-0.05)
# 図3：品目と分類
fig, ax = plt.subplots(figsize=(8.5, 3.0))
lab = ["分類（3つ）で分ける", "品目（12）で分ける"]
pr = [out["category_level"]["symmetric"]["price"], out["item_level"]["symmetric"]["price"]]
mx = [out["category_level"]["symmetric"]["mix"], out["item_level"]["symmetric"]["mix"]]
ax.barh(lab, pr, color=BLUE, label="単価の効果"); ax.barh(lab, mx, left=pr, color=ORANGE, label="構成の効果")
for i, (a, b) in enumerate(zip(pr, mx)):
    ax.text(a / 2, i, f"{a:+.2f}", ha="center", va="center", color="white", fontsize=9)
    ax.text(a + b / 2, i, f"{b:+.2f}", ha="center", va="center", color="white", fontsize=9)
ax.set_xlim(0, out["change_pct"] * 1.05); ax.set_xlabel("平均単価の前年比への寄与（ポイント、両方の平均で分けた値）")
ax.legend(frameon=False, fontsize=9, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
ax.set_title("粗い単位で分けると、分類の中の構成の変化が「単価」に入る", pad=22)
save(fig, "a664_level.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
