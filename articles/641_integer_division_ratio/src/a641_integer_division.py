"""641 整数どうしの割り算で割合を出すと、何%の行が0になるのか

架空の300店の来店数・購入数・返品数を作り、購入率（購入÷来店）と返品率（返品÷購入）を
  r1 整数どうしの割り算（SQL Server の int / int）
  r2 100 を掛けてから整数で割る（% の整数部分、切り捨て）
  r3 100.0 を掛けて小数で割る（正しい）
の3通りで出し、0になる行・ずれの大きさ・店の順位の入れ替わり・全体の平均のずれを数える。
DuckDB（1スレッド）では // で SQL Server の整数の割り算を再現し、Python の結果と一致することを確かめる。
数字は置いた件数と率で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の店別の来店・購入・返品の件数（作成者が乱数で作成、seed 641）"
DATA.mkdir(exist_ok=True)
rng = np.random.default_rng(641)
N = 300
visits = np.round(np.exp(rng.uniform(np.log(500), np.log(20000), N))).astype(int)
p_buy = np.clip(rng.normal(0.08, 0.03, N), 0.01, 0.2)
purchases = rng.binomial(visits, p_buy)
purchases = np.maximum(purchases, 1)
p_ret = np.clip(rng.lognormal(np.log(0.02), 0.6, N), 0.002, 0.15)
returns_ = rng.binomial(purchases, p_ret)
df = pd.DataFrame({"store_id": [f"S{i:03d}" for i in range(1, N + 1)], "visits": visits, "purchases": purchases, "returns_": returns_})
df.to_csv(DATA / "store_counts.csv", index=False)

# Python：整数の割り算は // （正の数なので切り捨てと同じ）
py = df.assign(r1_int=df.purchases // df.visits, r2_pct_int=df.purchases * 100 // df.visits,
               r3_pct=df.purchases * 100.0 / df.visits, ret_pct_int=df.returns_ * 100 // df.purchases,
               ret_pct=df.returns_ * 100.0 / df.purchases)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("store_counts", df)
sq = con.execute((SQL / "02_ratio_duckdb.sql").read_text(encoding="utf-8")).df()
for c in ["r1_int", "r2_pct_int", "ret_pct_int"]:
    assert (sq[c].values == py[c].values).all(), c
for c in ["r3_pct", "ret_pct"]:
    assert np.allclose(sq[c].values, py[c].values), c
py.to_csv(RES / "per_store.csv", index=False)


def stats(trunc, exact):
    err = trunc - exact
    return {"zero_rows": int((trunc == 0).sum()), "zero_pct": round(float((trunc == 0).mean() * 100), 1),
            "true_zero_rows": int((exact == 0).sum()),
            "false_zero_pct": round(float(((trunc == 0) & (exact > 0)).sum() / (exact > 0).sum() * 100), 1),
            "mean_err_pt": round(float(err.mean()), 3), "max_err_pt": round(float(err.min()), 3),
            "mean_rel_err_pct": round(float((err / exact.where(exact > 0)).mean() * 100), 1),
            "avg_exact": round(float(exact.mean()), 3), "avg_trunc": round(float(trunc.mean()), 3)}


def rank_change(a, b, top=10):
    ra = a.rank(ascending=False, method="min"); rb = b.rank(ascending=False, method="min")
    ties = int(b.duplicated(keep=False).sum())
    ta = set(a.nlargest(top).index); tb = set(b.nlargest(top, keep="all").index)
    return {"rank_changed_stores": int((ra != rb).sum()), "tied_stores": ties, "top10_size": len(tb),
            "top10_overlap": len(ta & tb)}


buy = stats(py.r2_pct_int, py.r3_pct); buy.update(rank_change(py.r3_pct, py.r2_pct_int))
buy["r1_zero_pct"] = round(float((py.r1_int == 0).mean() * 100), 1)
ret = stats(py.ret_pct_int, py.ret_pct); ret.update(rank_change(py.ret_pct, py.ret_pct_int))
# 全体の率：店の率の平均ではなく合計どうしで出す場合
overall = {"buy_exact": round(float(df.purchases.sum() * 100 / df.visits.sum()), 3),
           "buy_int": int(df.purchases.sum() * 100 // df.visits.sum()),
           "ret_exact": round(float(df.returns_.sum() * 100 / df.purchases.sum()), 3),
           "ret_int": int(df.returns_.sum() * 100 // df.purchases.sum())}
# 率の大きさごとのずれ（返品率）
bins = [0, 1, 2, 3, 5, 100]
py["ret_bin"] = pd.cut(py.ret_pct, bins, right=False, labels=["1%未満", "1〜2%", "2〜3%", "3〜5%", "5%以上"])
bb = py.groupby("ret_bin", observed=False).apply(lambda g: pd.Series({"stores": len(g), "zero_pct": (g.ret_pct_int == 0).mean() * 100,
                                                     "mean_rel_err_pct": ((g.ret_pct_int - g.ret_pct) / g.ret_pct.where(g.ret_pct > 0)).mean() * 100})).round(1)
bb.to_csv(RES / "return_rate_bins.csv")
out = {"stores": N, "purchase_rate": buy, "return_rate": ret, "overall": overall,
       "return_bins": bb.reset_index().to_dict(orient="records")}
pd.DataFrame({"purchase": buy, "return": ret}).to_csv(RES / "summary.csv")
json.dump(out, open(RES / "a641_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：0になった店の割合
fig, ax = plt.subplots(figsize=(8.5, 3.6))
labs = ["購入率：整数どうしの割り算", "購入率：100を掛けてから整数で割る", "返品率：100を掛けてから整数で割る"]
vals = [buy["r1_zero_pct"], buy["false_zero_pct"], ret["false_zero_pct"]]
ax.barh(labs[::-1], vals[::-1], color=[ORANGE, BLUE, BLUE][::-1])
for i, v in enumerate(vals[::-1]):
    ax.text(v, i, f" {v:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, 115); ax.set_xlabel("本当は0でないのに0になった店の割合（%）")
ax.set_title(f"本当は0でないのに0と出た店の割合（返品が0件の{ret['true_zero_rows']}店は除いた）")
save(fig, "a641_zero_share.png", SRC, y=-0.06)

# 図2：返品率の正しい値と切り捨てた値
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.scatter(py.ret_pct, py.ret_pct_int, s=12, color=BLUE, alpha=0.6)
ax.plot([0, py.ret_pct.max()], [0, py.ret_pct.max()], color=GRAY, ls="--", lw=0.8)
ax.set_xlabel("正しい返品率（%）"); ax.set_ylabel("100を掛けてから整数で割った返品率（%）")
ax.set_title("切り捨てで、返品率は階段になり、1%未満はすべて0になる")
save(fig, "a641_return_scatter.png", SRC)

# 図3：返品率の大きさごとの、ずれの割合
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(bb.index.astype(str), -bb.mean_rel_err_pct, color=ORANGE)
for i, (v, s) in enumerate(zip(-bb.mean_rel_err_pct, bb.stores)):
    ax.text(i, v, f"−{v:.0f}%\n（{int(s)}店）", ha="center", va="bottom", fontsize=8)
ax.set_xlabel("正しい返品率"); ax.set_ylabel("小さく出た割合の平均（%）"); ax.set_ylim(0, 115)
ax.set_title("率が小さい店ほど、切り捨てで大きく小さく出る（返品率）")
save(fig, "a641_rel_error.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
