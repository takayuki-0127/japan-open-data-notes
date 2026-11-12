"""473 値引きやクーポンを明細に割り振る方法で、商品ごとの粗利はどれだけ変わるのか（seed 473）"""
import json, numpy as np, pandas as pd, duckdb, matplotlib.pyplot as plt
from common import *
SEED = 473; SRC = "架空の注文（seed 473）"
DEPT = ["食品", "日用品", "飲料", "化粧品", "衣料", "家電小物", "文具", "ギフト"]
MARG = [0.22, 0.14, 0.18, 0.45, 0.50, 0.25, 0.40, 0.35]            # 部門ごとの粗利率（値引き前）の目安
PRICE = [380, 300, 160, 2400, 3900, 5200, 250, 3300]               # 部門ごとの値段の目安（円）
POP = [0.26, 0.20, 0.20, 0.08, 0.07, 0.04, 0.10, 0.05]             # 売れやすさ

def make(rng, n_orders=60000, n_prod=320, coupon_share=0.25, pct_share=0.15, ship_share=1.0):
    dep = rng.choice(8, n_prod, p=[.2, .18, .12, .12, .12, .08, .1, .08])
    price = np.round(np.array(PRICE)[dep] * np.exp(rng.normal(0, .45, n_prod)), -1).clip(60)
    marg = (np.array(MARG)[dep] + rng.normal(0, .06, n_prod)).clip(.03, .7); cost = np.round(price * (1 - marg))
    w = np.array(POP)[dep] * np.exp(rng.normal(0, .6, n_prod)); w /= w.sum()
    nl = rng.choice([1, 2, 3, 4, 5, 6], n_orders, p=[.22, .26, .22, .15, .1, .05]); oid = np.repeat(np.arange(n_orders), nl); N = len(oid)
    pid = rng.choice(n_prod, N, p=w); cheap = price[pid] < 600
    qty = np.where(cheap, rng.choice([1, 2, 3, 4, 6], N, p=[.4, .25, .15, .12, .08]), rng.choice([1, 2], N, p=[.9, .1]))
    L = pd.DataFrame({"order_id": oid, "line_no": np.concatenate([np.arange(k) + 1 for k in nl]), "product_id": pid, "dept": dep[pid], "qty": qty})
    L["amount"] = (price[pid] * qty).astype(int); L["cost"] = (cost[pid] * qty).astype(int)
    tot = L.groupby("order_id").amount.sum().values
    coupon = np.where(rng.random(n_orders) < coupon_share, rng.choice([300, 500, 1000], n_orders, p=[.4, .4, .2]), 0)
    pct = np.where(rng.random(n_orders) < pct_share, np.floor(tot * 0.10), 0)
    ship = np.where(tot >= 5000, 550, 0) * (rng.random(n_orders) < ship_share)          # 5,000円以上で送料無料（会社が持つ送料）
    disc = np.minimum(coupon + pct + ship, np.floor(tot * 0.6)).astype(int)             # 値引きは注文の6割まで
    O = pd.DataFrame({"order_id": np.arange(n_orders), "total": tot, "coupon": coupon, "pct_off": pct.astype(int), "free_shipping": ship.astype(int), "discount": disc})
    P = pd.DataFrame({"product_id": np.arange(n_prod), "dept": dep, "price": price.astype(int), "unit_cost": cost.astype(int)})
    return L, O, P

def largest_remainder(raw, oid):
    """端数を切り捨ててから、余りの大きい明細に1円ずつ戻す（注文ごとに合計が値引きと同じになる）"""
    fl = np.floor(raw + 1e-9); rem = raw - fl; df = pd.DataFrame({"o": oid, "fl": fl, "rem": rem})
    short = np.round(pd.Series(raw).groupby(oid).sum().values - pd.Series(fl).groupby(oid).sum().values).astype(int)
    rk = df.groupby("o").rem.rank(method="first", ascending=False).values
    return (fl + (rk <= short[np.searchsorted(np.unique(oid), oid)])).astype(int)

def allocate(L, O):
    d = O.set_index("order_id").discount.reindex(L.order_id).values.astype(float); oid = L.order_id.values
    sa = L.groupby("order_id").amount.transform("sum").values; sq = L.groupby("order_id").qty.transform("sum").values
    out = {}
    out["金額の割合"] = largest_remainder(d * L.amount.values / sa, oid)
    out["数量の割合"] = largest_remainder(d * L.qty.values / sq, oid)
    top = L.sort_values(["order_id", "amount", "line_no"], ascending=[True, False, True]).groupby("order_id").head(1).index
    t = np.zeros(len(L), dtype=int); t[top] = d[top].astype(int); out["いちばん高い明細に寄せる"] = t
    out["割り振らない（別の行）"] = np.zeros(len(L), dtype=int)
    rnd = {"四捨五入": np.round(d * L.amount.values / sa + 1e-9), "切り捨て": np.floor(d * L.amount.values / sa + 1e-9), "切り上げ": np.ceil(d * L.amount.values / sa - 1e-9)}
    return out, rnd
METHODS = ["金額の割合", "数量の割合", "いちばん高い明細に寄せる", "割り振らない（別の行）"]; MC = [BLUE, ORANGE, GREEN, GRAY]

rng = np.random.default_rng(SEED); L, O, P = make(rng); A, RND = allocate(L, O); res = {}
res["n_orders"] = int(len(O)); res["n_lines"] = int(len(L)); res["sales"] = int(L.amount.sum()); res["discount_total"] = int(O.discount.sum())
res["discount_share_of_sales"] = float(O.discount.sum() / L.amount.sum()); res["orders_with_discount"] = float((O.discount > 0).mean())
res["multi_line_discount_orders"] = float(((O.discount > 0) & (L.groupby("order_id").size().values > 1)).mean())
for m in METHODS[:3]: assert (pd.Series(A[m]).groupby(L.order_id.values).sum().values == O.discount.values).all(), m

# ---- SQL（DuckDB）と一致するか ----
con = duckdb.connect(); con.execute("SET threads=1"); con.register("lines", L); con.register("orders", O)
q = con.execute(open(SQL / "01_allocate_tsql.sql", encoding="utf-8").read()).df().sort_values(["order_id", "line_no"]).reset_index(drop=True)
assert (q.alloc_top.values == A["いちばん高い明細に寄せる"]).all()
assert np.abs(q.alloc_amount_round.values - RND["四捨五入"]).max() <= 1          # .5 ちょうどの丸めの向きだけ違いうる
res["sql_check"] = "DuckDB の結果が pandas と一致（いちばん高い明細は全行一致、四捨五入は .5 ちょうどの行を除いて一致）"
res["sql_round_half_rows"] = int((q.alloc_amount_round.values != RND["四捨五入"]).sum())

# ---- 1. 商品ごと・部門ごとの粗利 ----
prod = {}; dept = {}
for m in METHODS:
    t = L.assign(net=L.amount - A[m], gp=L.amount - A[m] - L.cost)
    g = t.groupby("product_id").agg(net=("net", "sum"), gp=("gp", "sum")); g["rate"] = g.gp / g.net; prod[m] = g
    h = t.groupby("dept").agg(net=("net", "sum"), gp=("gp", "sum")); h["rate"] = h.gp / h.net; dept[m] = h
PR = pd.DataFrame({m: prod[m].rate for m in METHODS}); GP = pd.DataFrame({m: prod[m].gp for m in METHODS})
PR.insert(0, "dept", [DEPT[i] for i in P.set_index("product_id").dept.reindex(PR.index)]); PR.reset_index().to_csv(RES / "product_margin_by_method.csv", index=False)
DR = pd.DataFrame({m: dept[m].rate for m in METHODS}); DR.index = DEPT; DR.to_csv(RES / "dept_margin_by_method.csv")
base = "金額の割合"
res["n_products"] = int(len(PR)); res["neg_products"] = {m: int((GP[m] < 0).sum()) for m in METHODS}
sg = np.sign(GP[METHODS[:3]]); res["sign_differs_among_3"] = int((sg.nunique(axis=1) > 1).sum())
res["sign_differs_any_of_4"] = int((np.sign(GP[METHODS]).nunique(axis=1) > 1).sum())
for m in METHODS[1:]:
    dd = (PR[m] - PR[base]) * 100
    res[f"rate_diff_vs_amount__{m}"] = {"median_abs_pt": float(dd.abs().median()), "p90_abs_pt": float(dd.abs().quantile(.9)), "max_abs_pt": float(dd.abs().max()), "over_5pt": int((dd.abs() > 5).sum())}
res["dept_rate_pct"] = {m: {DEPT[i]: round(float(v) * 100, 1) for i, v in enumerate(dept[m].rate.values)} for m in METHODS}
res["dept_range_pt"] = {DEPT[i]: round(float((DR.iloc[i, :3].max() - DR.iloc[i, :3].min()) * 100), 1) for i in range(8)}
res["dept_rank_change"] = int((DR[METHODS[:3]].rank(ascending=False).nunique(axis=1) > 1).sum())
res["total_gp"] = {m: int(prod[m].gp.sum()) for m in METHODS}; res["total_gp_no_alloc_minus_discount"] = int(prod[METHODS[3]].gp.sum() - O.discount.sum())
ln = {m: int(((L.amount.values - A[m]) < 0).sum()) for m in METHODS}; res["lines_negative_net"] = ln
res["lines_below_cost"] = {m: float(((L.amount.values - A[m] - L.cost.values) < 0).mean()) for m in METHODS}

# ---- 2. 端数 ----
rr = {}
for k, v in RND.items():
    s_ = pd.Series(v).groupby(L.order_id.values).sum().values - O.discount.values; has = O.discount.values > 0
    rr[k] = {"orders_not_matching_pct": float((s_[has] != 0).mean() * 100), "total_gap_yen": int(s_.sum()), "max_gap_yen": int(np.abs(s_).max())}
rr["切り捨てて余りを戻す"] = {"orders_not_matching_pct": 0.0, "total_gap_yen": 0, "max_gap_yen": 0}
res["rounding"] = rr; pd.DataFrame(rr).T.to_csv(RES / "rounding.csv")
multi = (L.groupby("order_id").size().values > 1) & (O.discount.values > 0)
s_ = pd.Series(RND["四捨五入"]).groupby(L.order_id.values).sum().values - O.discount.values; res["round_mismatch_among_multi_line_pct"] = float((s_[multi] != 0).mean() * 100)

# ---- 3. 値引きの多さ・クーポンの形を変える（各5回） ----
rows = []
for cs, ps, lab in [(0.10, 0.05, "値引きが少ない"), (0.25, 0.15, "基本"), (0.50, 0.30, "値引きが多い")]:
    o = []
    for rep in range(5):
        rg = np.random.default_rng(SEED * 100 + int(cs * 100) + rep); L2, O2, P2 = make(rg, n_orders=30000, coupon_share=cs, pct_share=ps); A2, _ = allocate(L2, O2)
        gp = {m: (L2.amount - A2[m] - L2.cost).groupby(L2.product_id).sum() for m in METHODS}; nt = {m: (L2.amount - A2[m]).groupby(L2.product_id).sum() for m in METHODS}
        dq = ((gp["数量の割合"] / nt["数量の割合"]) - (gp[base] / nt[base])).abs() * 100
        o.append([O2.discount.sum() / L2.amount.sum() * 100, (gp[base] < 0).sum(), (gp["数量の割合"] < 0).sum(), (gp["いちばん高い明細に寄せる"] < 0).sum(), dq.median(), dq.quantile(.9),
                  (np.sign(pd.DataFrame(gp)[METHODS[:3]]).nunique(axis=1) > 1).sum()])
    o = np.mean(o, axis=0); rows.append({"scene": lab, "discount_share_pct": o[0], "neg_amount": o[1], "neg_qty": o[2], "neg_top": o[3], "rate_diff_median_pt": o[4], "rate_diff_p90_pt": o[5], "sign_differs": o[6]})
sw = pd.DataFrame(rows); sw.to_csv(RES / "sweep_discount_level.csv", index=False); res["sweep"] = sw.round(2).to_dict("records")
json.dump(res, open(RES / "a473_main.json", "w"), ensure_ascii=False, indent=1)
L.head(2000).to_csv(DATA / "order_lines_sample.csv", index=False); O.head(800).to_csv(DATA / "orders_sample.csv", index=False); P.to_csv(DATA / "products.csv", index=False)

# ---- 図 ----
fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
ax[0].bar(range(4), [res["neg_products"][m] for m in METHODS], color=MC)
for i, m in enumerate(METHODS): ax[0].text(i, res["neg_products"][m] + .4, f'{res["neg_products"][m]}', ha="center", fontsize=11)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(["金額の割合", "数量の割合", "いちばん高い\n明細に寄せる", "割り振らない\n（別の行）"], fontsize=9); ax[0].set_ylabel("粗利が赤字になった商品の数"); ax[0].set_title(f"赤字になった商品の数（{len(PR)}商品のうち）")
ax[1].scatter(PR[base] * 100, PR["数量の割合"] * 100, s=12, color=ORANGE, alpha=.7, label="数量の割合"); ax[1].scatter(PR[base] * 100, PR["いちばん高い明細に寄せる"] * 100, s=12, color=GREEN, alpha=.6, label="いちばん高い明細に寄せる")
lo = min(PR[METHODS[:3]].min().min() * 100, -5); ax[1].plot([lo, 70], [lo, 70], color=GRAY, lw=1); ax[1].axhline(0, color=GRAY, lw=.6, ls=":")
ax[1].set_xlabel("金額の割合で割り振ったときの粗利率（%）"); ax[1].set_ylabel("ほかの方法での粗利率（%）"); ax[1].set_title("商品ごとの粗利率（1点が1商品）"); ax[1].legend(fontsize=9, frameon=False)
save(fig, "a473_products.png", f"出典：{SRC}。注文6万件・明細{len(L):,}行。値引きは売上の{res['discount_share_of_sales']*100:.1f}%")

fig, ax = plt.subplots(figsize=(11, 4.3)); xs = np.arange(8); wd = .2
for i, (m, c) in enumerate(zip(METHODS, MC)): ax.bar(xs + (i - 1.5) * wd, DR[m] * 100, wd, color=c, label=m)
ax.set_xticks(xs); ax.set_xticklabels(DEPT); ax.set_ylabel("部門の粗利率（%）"); ax.set_title("部門ごとの粗利率（割り振り方ごと）"); ax.legend(fontsize=9, frameon=False, ncol=2)
for i in range(8): ax.text(i, DR.iloc[i].max() * 100 + 1, f"幅{res['dept_range_pt'][DEPT[i]]}", ha="center", fontsize=8, color=INK)
save(fig, "a473_departments.png", f"出典：{SRC}。「幅」は、割り振る3つの方法のあいだの粗利率の差（ポイント）。灰色は値引きを商品に割り振らない場合")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.3)); ks = list(rr.keys())
ax[0].bar(range(4), [rr[k]["orders_not_matching_pct"] for k in ks], color=[ORANGE, ORANGE, ORANGE, BLUE])
for i, k in enumerate(ks): ax[0].text(i, rr[k]["orders_not_matching_pct"] + 1, f'{rr[k]["orders_not_matching_pct"]:.1f}%\n差 {rr[k]["total_gap_yen"]:+,}円', ha="center", fontsize=8.5)
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(["四捨五入", "切り捨て", "切り上げ", "切り捨てて\n余りを戻す"], fontsize=9); ax[0].set_ylabel("明細の合計が値引きと合わない注文（%）"); ax[0].set_ylim(0, max(rr[k]["orders_not_matching_pct"] for k in ks) * 1.3 + 5)
ax[0].set_title("端数の扱いと、合計が合わない注文（値引きのある注文のうち）")
ax[1].bar(range(4), [res["lines_below_cost"][m] * 100 for m in METHODS], color=MC)
for i, m in enumerate(METHODS): ax[1].text(i, res["lines_below_cost"][m] * 100 + .1, f'{res["lines_below_cost"][m]*100:.1f}%', ha="center", fontsize=10)
ax[1].set_xticks(range(4)); ax[1].set_xticklabels(["金額の割合", "数量の割合", "いちばん高い\n明細に寄せる", "割り振らない\n（別の行）"], fontsize=9); ax[1].set_ylabel("原価を下回った明細（%）"); ax[1].set_title("割り振ったあと、原価を下回った明細の割合")
save(fig, "a473_rounding_lines.png", f"出典：{SRC}。左は金額の割合で割り振る場合")
print(json.dumps(res, ensure_ascii=False)[:4500])
