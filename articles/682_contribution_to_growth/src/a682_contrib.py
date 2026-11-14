"""682 店ごとの前年比を並べるのと、全体の伸びへの寄与度で並べるのでは、順位はどれだけ違うのか

架空の30店の売上2年分。前の年の売上は店ごとに大きく違う（対数正規、平均 約2億円）。
今年の伸び率は、平均 +4%（この乱数では全体で +2.5%）、小さい店ほど振れが大きい（標準偏差 3%〜18%）。
  前年比＝今年 ÷ 前の年 − 1
  寄与度＝(今年 − 前の年) ÷ 全店の前の年の合計（ポイント）。全店を足すと全体の前年比になる
  寄与率＝(今年 − 前の年) ÷ 全店の増えた額の合計。全店を足すと 100%
場面A：そのまま。場面B：同じ店の伸び率から一律に差し引き、全体の伸びを +0.3% にしたもの（寄与率が振れる様子を見る）。
前年比と寄与度の順位の違いを数える。DuckDB の SQL（1スレッド）でも出し、Python と一致を確かめる。
数字は置いた売上と伸び率で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from scipy import stats
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の30店の売上（作成者が乱数で作成、seed 682）"
rng = np.random.default_rng(682)
NS = 30
s1 = np.round(rng.lognormal(np.log(15000), .8, NS), -1)                 # 万円
size_rank = stats.rankdata(s1) / NS                                      # 0〜1（大きいほど1）
sd = .18 - .15 * size_rank
g = .04 + sd * rng.standard_normal(NS)
s2a = np.round(s1 * (1 + g), -1)
target = .003
shift = (s2a.sum() - s1.sum() * (1 + target)) / s1.sum()
s2b = np.round(s1 * (1 + g - shift), -1)
stores = [f"店{i + 1:02d}" for i in range(NS)]
rows = []
for sc, s2 in [("A", s2a), ("B", s2b)]:
    for st, a, b in zip(stores, s1, s2):
        rows += [(sc, st, 2024, a), (sc, st, 2025, b)]
D = pd.DataFrame(rows, columns=["scene", "store", "year", "sales"])
DATA.mkdir(exist_ok=True)
D.to_csv(DATA / "store_sales.csv", index=False)


def calc(s2):
    T = pd.DataFrame({"store": stores, "prev": s1, "cur": s2})
    T["yoy"] = 100 * (T.cur / T.prev - 1)
    T["contrib_pt"] = 100 * (T.cur - T.prev) / T.prev.sum()
    T["contrib_share"] = 100 * (T.cur - T.prev) / (T.cur.sum() - T.prev.sum())
    T["rank_yoy"] = T.yoy.rank(ascending=False, method="first").astype(int)
    T["rank_contrib"] = T.contrib_pt.rank(ascending=False, method="first").astype(int)
    return T


TA, TB = calc(s2a), calc(s2b)
TA.round(4).to_csv(RES / "stores_A.csv", index=False); TB.round(4).to_csv(RES / "stores_B.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("store_sales", D)
q = (SQL / "02_contrib_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
for sc, T in [("A", TA), ("B", TB)]:
    sq = con.execute(q, [sc]).df().set_index("store").loc[stores]
    assert np.allclose(sq.yoy, T.yoy.values) and np.allclose(sq.contrib_pt, T.contrib_pt.values)
    assert np.allclose(sq.contrib_share, T.contrib_share.values)

total_yoy = {sc: round(float(100 * (T.cur.sum() / T.prev.sum() - 1)), 3) for sc, T in [("A", TA), ("B", TB)]}
assert np.isclose(TA.contrib_pt.sum(), 100 * (TA.cur.sum() / TA.prev.sum() - 1)) and np.isclose(TA.contrib_share.sum(), 100)
top5_y = set(TA.nsmallest(5, "rank_yoy").store); top5_c = set(TA.nsmallest(5, "rank_contrib").store)
diff = (TA.rank_yoy - TA.rank_contrib).abs()
best_yoy = TA.loc[TA.rank_yoy == 1].iloc[0]; best_c = TA.loc[TA.rank_contrib == 1].iloc[0]
out = {"stores": NS, "total_prev": float(s1.sum()),
       "total_yoy_pct": total_yoy,
       "A": {"spearman": round(float(stats.spearmanr(TA.yoy, TA.contrib_pt)[0]), 3),
             "top5_overlap": len(top5_y & top5_c),
             "rank_moved_ge5": int((diff >= 5).sum()), "rank_moved_ge10": int((diff >= 10).sum()), "rank_moved_max": int(diff.max()),
             "best_yoy": {"store": best_yoy.store, "yoy": round(best_yoy.yoy, 1), "contrib_pt": round(best_yoy.contrib_pt, 3),
                          "rank_contrib": int(best_yoy.rank_contrib)},
             "best_contrib": {"store": best_c.store, "yoy": round(best_c.yoy, 1), "contrib_pt": round(best_c.contrib_pt, 3),
                              "rank_yoy": int(best_c.rank_yoy)},
             "sum_contrib_pt": round(float(TA.contrib_pt.sum()), 3), "sum_contrib_share": round(float(TA.contrib_share.sum()), 3),
             "top5_contrib_share_sum": round(float(TA.nsmallest(5, "rank_contrib").contrib_share.sum()), 1),
             "share_of_sales_top5_contrib": round(float(100 * TA.nsmallest(5, "rank_contrib").prev.sum() / s1.sum()), 1)},
       "B": {"contrib_share_max": round(float(TB.contrib_share.max()), 1), "contrib_share_min": round(float(TB.contrib_share.min()), 1),
             "contrib_pt_max": round(float(TB.contrib_pt.max()), 3), "contrib_pt_min": round(float(TB.contrib_pt.min()), 3),
             "n_share_over_100": int((TB.contrib_share.abs() > 100).sum()),
             "sum_contrib_share": round(float(TB.contrib_share.sum()), 3)}}
json.dump(out, open(RES / "a682_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：前年比と寄与度
fig, ax = plt.subplots(figsize=(9, 4.8))
sz = 20 + 400 * TA.prev / TA.prev.max()
ax.scatter(TA.yoy, TA.contrib_pt, s=sz, color=BLUE, alpha=.55, edgecolor="white")
for _, r in TA.iterrows():
    if r.rank_yoy <= 3 or r.rank_contrib <= 3:
        ax.annotate(f"{r.store}（前年比{r.rank_yoy}位・寄与度{r.rank_contrib}位）", (r.yoy, r.contrib_pt),
                    textcoords="offset points", xytext=(6, 6), fontsize=8.5)
ax.axhline(0, color=GRAY, lw=.8); ax.axvline(0, color=GRAY, lw=.8)
ax.set_xlabel("前年比（%）"); ax.set_ylabel("全体の伸びへの寄与度（ポイント）")
ax.set_title(f"場面A：前年比が高い店と、全体を押し上げた店は違う（円の大きさは前の年の売上）")
save(fig, "a682_scatter.png", SRC)

# 図2：順位の入れ替わり
fig, ax = plt.subplots(figsize=(7.5, 6.2))
for _, r in TA.iterrows():
    big = abs(r.rank_yoy - r.rank_contrib) >= 5
    ax.plot([0, 1], [r.rank_yoy, r.rank_contrib], color=ORANGE if big else LIGHT, lw=1.8 if big else 1.1)
    ax.text(-.03, r.rank_yoy, r.store, ha="right", va="center", fontsize=7.5)
    ax.text(1.03, r.rank_contrib, r.store, ha="left", va="center", fontsize=7.5)
ax.set_ylim(NS + .8, .2); ax.set_xlim(-.3, 1.3)
ax.set_xticks([0, 1]); ax.set_xticklabels(["前年比の順位", "寄与度の順位"])
ax.set_yticks([1, 5, 10, 15, 20, 25, 30]); ax.set_ylabel("順位")
for sp in ["left", "bottom"]:
    ax.spines[sp].set_visible(False)
ax.set_title(f"場面A：順位が5以上動いた店（橙）は {int((diff >= 5).sum())}店", fontsize=12)
save(fig, "a682_ranks.png", SRC)

# 図3：場面Bの寄与率と寄与度
fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
order = TB.sort_values("contrib_pt", ascending=True)
y = np.arange(NS)
axes[0].barh(y, order.contrib_pt, color=[BLUE if v >= 0 else ORANGE for v in order.contrib_pt])
axes[0].set_xlabel("寄与度（ポイント）"); axes[0].set_title(f"寄与度：合計は全体の前年比 {total_yoy['B']:+.1f}%", fontsize=11)
axes[1].barh(y, order.contrib_share, color=[BLUE if v >= 0 else ORANGE for v in order.contrib_share])
axes[1].set_xlabel("寄与率（%）"); axes[1].set_title(f"寄与率：合計は100%だが、±100%を超える店が{int((TB.contrib_share.abs() > 100).sum())}店", fontsize=11)
for ax in axes:
    ax.axvline(0, color=INK, lw=.8)
axes[0].set_yticks(y); axes[0].set_yticklabels(order.store, fontsize=7)
fig.suptitle("場面B（全体がほぼ横ばい）：寄与率は分母が0に近く、大きく振れる", fontsize=12)
save(fig, "a682_share_flat.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
