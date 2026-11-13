"""602 平均単価を「明細の単価の平均」で出すか「金額の合計÷数量」で出すかで、品目の単価はどれだけ違うのか

架空の80品目・明細4万行（2025年）を作る。まとめ買いほど単価が下がる（数量値引き）・大口の取引先は単価が低い。
  U0 金額の合計÷数量の合計（1個あたりの平均単価）
  U1 明細の単価の単純平均（1行を同じ重さで数える）
  U2 日ごとの平均単価の平均（平均の平均）
品目ごとの差・単価の順位の入れ替わり・「平均単価×数量」で売上を戻したときのずれを数える。
DuckDB（1スレッド）の SQL と pandas の結果が一致することを確かめる。数字は置いた値引きの仕方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の品目と売上明細（作成者が乱数で作成、seed 602）"
rng = np.random.default_rng(602)
N_ITEM, N_LINE = 80, 40000
list_price = rng.choice([150, 280, 450, 800, 1200, 2500, 4800], N_ITEM)
# 品目ごとの値引きの効き方（数量が多いほど下がる度合い）と、大口の割合
slope = rng.uniform(0.0, 0.06, N_ITEM)
big_share = rng.uniform(0.0, 0.12, N_ITEM)
w = rng.gamma(1.0, 1.0, N_ITEM); w /= w.sum()
item = rng.choice(N_ITEM, N_LINE, p=w)
is_big = rng.random(N_LINE) < big_share[item]
qty = np.where(is_big, rng.integers(20, 61, N_LINE), rng.choice([1, 1, 1, 2, 2, 3, 4, 5, 6, 10], N_LINE))
disc = np.clip(slope[item] * np.log1p(qty - 1), 0, 0.25) + np.where(is_big, rng.uniform(0.02, 0.08, N_LINE), 0)
unit = np.round(list_price[item] * (1 - disc) * rng.uniform(0.97, 1.03, N_LINE)).astype(int)
days = pd.date_range("2025-01-01", "2025-12-31")
SL = pd.DataFrame({"line_id": np.arange(1, N_LINE + 1), "item_id": [f"I{i + 1:03d}" for i in item],
                   "sold_on": rng.choice(days, N_LINE), "qty": qty, "unit_price": unit})
SL["amount"] = SL.qty * SL.unit_price
SL = SL.sort_values(["sold_on", "line_id"]).reset_index(drop=True)
SL.assign(sold_on=SL.sold_on.dt.strftime("%Y-%m-%d")).to_csv(DATA / "sales_lines.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales_lines", SL)
q = [x for x in (SQL / "02_avg_price_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
a = con.execute(q[0]).df().set_index("item_id").sort_index()
b = con.execute(q[1]).df().set_index("item_id").sort_index()
it = a.join(b)
# pandas で同じ値
g = SL.groupby("item_id")
assert np.allclose(it.p_simple, g.unit_price.mean()) and np.allclose(it.p_weighted, g.amount.sum() / g.qty.sum())
assert np.allclose(it.p_daily_mean, SL.groupby(["item_id", "sold_on"]).unit_price.mean().groupby("item_id").mean())

it["diff_simple_pct"] = (it.p_simple / it.p_weighted - 1) * 100
it["diff_daily_pct"] = (it.p_daily_mean / it.p_weighted - 1) * 100
it["big_qty_share"] = SL[SL.qty >= 20].groupby("item_id").qty.sum().reindex(it.index).fillna(0) / it.qty
it["rev_simple"] = it.p_simple * it.qty
it.round(3).to_csv(RES / "by_item.csv")
rev_err = float(it.rev_simple.sum() / it.amount.sum() - 1) * 100
rho = stats.spearmanr(it.p_simple, it.p_weighted).correlation
# 単価の順位の入れ替わり（同じ定価の品目どうしで比べる＝定価の違いに埋もれない比較）
moved = 0; grp_n = 0
for lp, sub in it.join(pd.Series(list_price, index=[f"I{i + 1:03d}" for i in range(N_ITEM)], name="list")).groupby("list"):
    if len(sub) < 2:
        continue
    grp_n += len(sub)
    moved += int((sub.p_simple.rank(method="first") != sub.p_weighted.rank(method="first")).sum())
# 大口の割合と差の関係
r_big = float(np.corrcoef(it.big_qty_share, it.diff_simple_pct)[0, 1])
out = {"items": N_ITEM, "lines": N_LINE, "total_amount": int(SL.amount.sum()), "total_qty": int(SL.qty.sum()),
       "diff_simple_pct": {"median": round(float(it.diff_simple_pct.median()), 2), "max": round(float(it.diff_simple_pct.max()), 2),
                           "min": round(float(it.diff_simple_pct.min()), 2), "share_over_5pct": round(float((it.diff_simple_pct > 5).mean() * 100), 1),
                           "share_over_10pct": round(float((it.diff_simple_pct > 10).mean() * 100), 1)},
       "diff_daily_pct": {"median": round(float(it.diff_daily_pct.median()), 2), "max": round(float(it.diff_daily_pct.max()), 2)},
       "revenue_from_simple_vs_actual_pct": round(rev_err, 2), "spearman_simple_vs_weighted": round(float(rho), 3),
       "rank_moved_within_same_list_price": moved, "items_in_compared_groups": grp_n,
       "corr_bigshare_diff": round(r_big, 3)}
json.dump(out, open(RES / "a602_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：品目ごとの差（大口の数量の割合との関係）
fig, ax = plt.subplots(figsize=(8, 4))
ax.scatter(it.big_qty_share * 100, it.diff_simple_pct, color=BLUE, s=24, label="明細の単価の平均（U1）")
ax.scatter(it.big_qty_share * 100, it.diff_daily_pct, color=ORANGE, s=16, marker="^", label="日ごとの平均の平均（U2）")
ax.axhline(0, color=GRAY, lw=0.8)
ax.set_xlabel("数量のうち、20個以上の大口の取引の割合（%）"); ax.set_ylabel("金額÷数量の平均単価との差（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("品目ごと：大口の多い品目ほど、単価の平均は高く出る")
save(fig, "a602_diff_by_item.png", SRC)
# 図2：分布
fig, ax = plt.subplots(figsize=(8, 3.8))
bins = np.arange(-2, it.diff_simple_pct.max() + 3, 2)
ax.hist(it.diff_simple_pct, bins=bins, color=BLUE, edgecolor="white")
ax.axvline(it.diff_simple_pct.median(), color=ORANGE, lw=1.5, ls="--")
ax.set_xlabel("明細の単価の平均と、金額÷数量の平均単価との差（%）"); ax.set_ylabel("品目の数")
ax.set_title(f"{N_ITEM}品目の差の分布（中央値 U1 {out['diff_simple_pct']['median']:+.1f}%）")
save(fig, "a602_diff_hist.png", SRC)
# 図3：1品目の例（差が最大の品目）：数量と単価
top = it.diff_simple_pct.idxmax(); s = SL[SL.item_id == top]
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.scatter(s.qty, s.unit_price, s=8, color=LIGHT, alpha=0.7)
ax.axhline(it.loc[top, "p_simple"], color=BLUE, lw=1.5, label=f"明細の単価の平均 {it.loc[top, 'p_simple']:,.0f}円")
ax.axhline(it.loc[top, "p_weighted"], color=GREEN, lw=1.5, ls="--", label=f"金額÷数量 {it.loc[top, 'p_weighted']:,.0f}円")
ax.set_xscale("log"); ax.set_xticks([1, 2, 5, 10, 20, 50]); ax.set_xticklabels(["1", "2", "5", "10", "20", "50"]); ax.set_xlabel("1行の数量（対数の目盛り）"); ax.set_ylabel("単価（円）")
ax.legend(frameon=False, fontsize=9); ax.set_title(f"差がいちばん大きい品目（{top}）：行の数は小口、数量は大口が占める")
save(fig, "a602_example_item.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(it.loc[top])
