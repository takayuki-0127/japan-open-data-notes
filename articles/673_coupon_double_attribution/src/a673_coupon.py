"""673 1つの注文を、使ったクーポンそれぞれに全額付けると、クーポン別の売上の合計は実際の何倍になるのか

架空の通販の注文 3万件。クーポンは8種類（A〜H）。注文の 45% はクーポンなし、残りは1〜3枚を併用する。
クーポンごとに「よく併用される」度合いが違う（送料無料の G・H は他と一緒に使われやすい）。
クーポン別の売上を3通りで出す：
  全額：使ったクーポンそれぞれに注文の全額を付ける
  按分：注文の金額を、クーポンの値引き額の比で分ける
  最初の1つ：注文画面で最初に入れたクーポンだけに付ける
3つの合計を、クーポンを使った注文の実際の売上と比べ、クーポン別の順位の入れ替わりを見る。
併用の割合を変えたときの倍率も出す。全額と按分は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。
数字は置いた併用の起き方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の通販の注文とクーポン（作成者が乱数で作成、seed 673）"
rng = np.random.default_rng(673)
CODES = list("ABCDEFGH")
DISC = np.array([500, 300, 1000, 200, 800, 400, 600, 600])     # 値引き額（円）
POPW = np.array([.20, .18, .10, .14, .08, .10, .10, .10])      # 選ばれやすさ
STACKW = np.array([1, 1, .6, 1.2, .7, 1, 2.6, 2.4])            # 併用されやすさ（G・H は送料無料）


def make(n, p_none=.45, p_n=(.62, .28, .10), seed=673):
    r = np.random.default_rng(seed)
    amount = np.round(r.lognormal(np.log(6000), .6, n), -1).astype(int)
    k = np.where(r.random(n) < p_none, 0, r.choice([1, 2, 3], n, p=p_n))
    rows = []
    for oid in np.nonzero(k)[0]:
        first = r.choice(8, p=POPW)
        chosen = [first]
        if k[oid] > 1:
            w = POPW * STACKW; w[first] = 0; w = w / w.sum()
            chosen += list(r.choice(8, k[oid] - 1, replace=False, p=w))
        for pos, c in enumerate(chosen):
            rows.append((oid + 1, CODES[c], pos + 1, int(DISC[c])))
    O = pd.DataFrame({"order_id": np.arange(1, n + 1), "amount": amount})
    OC = pd.DataFrame(rows, columns=["order_id", "coupon", "entry_order", "discount"])
    return O, OC


def attribute(O, OC):
    M = OC.merge(O, on="order_id")
    M["share"] = M.discount / M.groupby("order_id").discount.transform("sum")
    full = M.groupby("coupon").amount.sum()
    prop = (M.amount * M.share).groupby(M.coupon).sum()
    first = M[M.entry_order == 1].groupby("coupon").amount.sum()
    actual = O[O.order_id.isin(OC.order_id)].amount.sum()
    return pd.DataFrame({"full": full, "prop": prop, "first": first}).reindex(CODES).fillna(0), actual


O, OC = make(30_000)
DATA.mkdir(exist_ok=True)
O.to_csv(DATA / "orders.csv", index=False); OC.to_csv(DATA / "order_coupons.csv", index=False)
T, actual = attribute(O, OC)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("orders", O); con.register("order_coupons", OC)
q = (SQL / "02_attribution_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df().set_index("coupon").reindex(CODES)
assert np.allclose(sq.full_amount, T.full) and np.allclose(sq.prop_amount, T.prop)
T["rank_full"] = T.full.rank(ascending=False).astype(int); T["rank_prop"] = T.prop.rank(ascending=False).astype(int); T["rank_first"] = T["first"].rank(ascending=False).astype(int)
T["stack_rate"] = OC.groupby("coupon").order_id.apply(lambda s: (OC[OC.order_id.isin(s)].groupby("order_id").size() > 1).mean()).reindex(CODES)
T.round(1).to_csv(RES / "by_coupon.csv")
ratio_full = T.full.sum() / actual
# 併用の割合を変える
sweep = []
for p3, lab in [((1, 0, 0), "併用なし"), ((.8, .15, .05), "少ない"), ((.62, .28, .10), "基本"), ((.4, .4, .2), "多い"), ((.2, .45, .35), "とても多い")]:
    o, oc = make(30_000, p_n=p3, seed=6731)
    t, a = attribute(o, oc)
    n_per = oc.groupby("order_id").size()
    sweep.append({"setting": lab, "avg_coupons_per_order": round(float(n_per.mean()), 3), "stacked_order_pct": round(100 * float((n_per > 1).mean()), 2),
                  "ratio_full": round(float(t.full.sum() / a), 3), "ratio_prop": round(float(t.prop.sum() / a), 3)})
SW = pd.DataFrame(sweep); SW.to_csv(RES / "by_stacking.csv", index=False)
n_per = OC.groupby("order_id").size()
out = {"orders": len(O), "orders_with_coupon": int(n_per.size), "stacked_order_pct": round(100 * float((n_per > 1).mean()), 2),
       "avg_coupons_per_coupon_order": round(float(n_per.mean()), 3), "actual_sales_coupon_orders": int(actual),
       "sum_full": int(T.full.sum()), "sum_prop": round(float(T.prop.sum()), 1), "sum_first": int(T["first"].sum()),
       "ratio_full": round(float(ratio_full), 3),
       "by_coupon": {c: {"full": int(T.full[c]), "prop": round(float(T.prop[c]), 0), "first": int(T["first"][c]),
                         "rank_full": int(T.rank_full[c]), "rank_prop": int(T.rank_prop[c]), "rank_first": int(T.rank_first[c]),
                         "full_over_prop": round(float(T.full[c] / T.prop[c]), 2), "stack_rate_pct": round(100 * float(T.stack_rate[c]), 1)} for c in CODES},
       "rank_changed_full_vs_prop": int((T.rank_full != T.rank_prop).sum()),
       "sweep": sweep}
json.dump(out, open(RES / "a673_main.json", "w"), ensure_ascii=False, indent=1)

# 図1
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = np.arange(8); w = .27
for i, (k, c, lab) in enumerate([("full", ORANGE, "全額を付ける"), ("prop", BLUE, "値引き額で按分"), ("first", GRAY, "最初の1つに付ける")]):
    ax.bar(x + (i - 1) * w, T[k] / 1e6, w, color=c, label=lab)
ax.set_xticks(x); ax.set_xticklabels([f"{c}\n{d}円" for c, d in zip(CODES, DISC)]); ax.set_ylabel("クーポン別の売上（百万円）")
ax.legend(frameon=False, fontsize=9); ax.set_title(f"全額を付けると、どのクーポンも按分の{T.full.div(T.prop).min():.1f}〜{T.full.div(T.prop).max():.1f}倍に見える")
save(fig, "a673_by_coupon.png", SRC)
# 図2：合計の倍率と併用の割合
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(SW.stacked_order_pct, SW.ratio_full, marker="o", color=ORANGE, label="全額を付けた合計÷実際の売上")
ax.plot(SW.stacked_order_pct, SW.ratio_prop, marker="s", color=BLUE, label="按分の合計÷実際の売上")
for xx, v in zip(SW.stacked_order_pct, SW.ratio_full): ax.text(xx, v + .03, f"{v:.2f}倍", ha="center", fontsize=9)
ax.set_xlabel("クーポンを使った注文のうち、2枚以上併用した割合（%）"); ax.set_ylabel("倍"); ax.set_ylim(.8, 2.4)
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("併用が多いほど、クーポン別の売上の合計は実際より大きくなる")
save(fig, "a673_ratio_by_stacking.png", SRC)
# 図3：順位（3通り）
fig, ax = plt.subplots(figsize=(7.5, 5))
cols3 = ["rank_full", "rank_prop", "rank_first"]
for c in CODES:
    ys = [T[k][c] for k in cols3]
    col = ORANGE if c in "GH" else GRAY
    ax.plot([0, 1, 2], ys, marker="o", color=col, lw=2 if c in "GH" else 1)
    ax.text(-.06, ys[0], c, ha="right", va="center", fontsize=10); ax.text(2.06, ys[2], c, ha="left", va="center", fontsize=10)
ax.set_xlim(-.4, 2.4); ax.set_ylim(8.6, .4); ax.set_xticks([0, 1, 2]); ax.set_xticklabels(["全額を付ける", "値引き額で按分", "最初の1つに付ける"])
ax.set_yticks(range(1, 9)); ax.set_ylabel("売上の順位"); ax.spines["bottom"].set_visible(False)
ax.set_title("送料無料の G・H は、付け方しだいで3位から7位まで動く")
save(fig, "a673_rank.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "by_coupon"}, ensure_ascii=False, indent=1)); print(T)
