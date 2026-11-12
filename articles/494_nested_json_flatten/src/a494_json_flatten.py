"""494 入れ子の JSON を平らにすると、行は何倍になり、合計はどれだけずれるのか（実務の型）

架空の注文 JSON（1件の注文に、明細の配列とクーポンの配列が入る）を、よく見る6通りで表に平らにし、
行の数と、明細の金額・クーポンの金額・送料・注文の合計の4つの合計が、正しい値からどれだけずれるかを数える。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 494
N = 20_000


def make_orders(rng, n, p_coupon=0.4, max_coupon=3):
    orders = []
    for i in range(n):
        k = int(min(rng.geometric(0.45), 8))                               # 明細 1〜8 行
        items = [{"sku": f"S{int(rng.integers(1, 500)):03d}", "qty": int(rng.integers(1, 4)),
                  "price": int(rng.choice([300, 480, 980, 1280, 1980, 2980, 4980]))} for _ in range(k)]
        for it in items: it["amount"] = it["qty"] * it["price"]
        c = int(rng.integers(1, max_coupon + 1)) if rng.random() < p_coupon else 0
        coupons = [{"code": f"C{int(rng.integers(1, 30)):02d}", "discount": int(rng.choice([100, 200, 300, 500]))} for _ in range(c)]
        sub = sum(it["amount"] for it in items); disc = sum(x["discount"] for x in coupons)
        ship = 0 if sub >= 5000 else 550
        orders.append({"order_id": i + 1, "customer": f"U{int(rng.integers(1, 6000)):04d}", "shipping": ship,
                       "order_total": sub - disc + ship, "items": items, "coupons": coupons})
    return orders


def truth(orders):
    return {"items_amount": sum(it["amount"] for o in orders for it in o["items"]),
            "coupons": sum(c["discount"] for o in orders for c in o["coupons"]),
            "shipping": sum(o["shipping"] for o in orders), "order_total": sum(o["order_total"] for o in orders)}


def flatten_all(orders, path):
    """6通りの平らにし方。それぞれの表から、4つの合計を素朴に SUM したもの"""
    res = {}
    T = truth(orders)
    # ① json_normalize で明細を行に（注文の項目を meta で付ける）
    df1 = pd.json_normalize(orders, record_path="items", meta=["order_id", "shipping", "order_total"])
    res["①明細ごとの行\n（注文の項目はくり返す）"] = (len(df1), {"items_amount": df1.amount.sum(), "coupons": np.nan,
                                                  "shipping": df1.shipping.sum(), "order_total": df1.order_total.sum()})
    # ② 明細を explode してから、クーポンも explode（順にほどく）
    df = pd.DataFrame(orders)
    d2 = df.explode("items").explode("coupons")
    ia = d2["items"].map(lambda x: x["amount"]); cd = d2["coupons"].map(lambda x: x["discount"] if isinstance(x, dict) else 0)
    res["②明細とクーポンを\n順に explode"] = (len(d2), {"items_amount": ia.sum(), "coupons": cd.sum(),
                                                "shipping": d2.shipping.sum(), "order_total": d2.order_total.sum()})
    # ③ SQL：明細とクーポンを、それぞれ注文に LEFT JOIN（同じ結果になる）
    con = duckdb.connect()
    cols = ("{'order_id':'INTEGER','customer':'VARCHAR','shipping':'INTEGER','order_total':'INTEGER',"
            "'items':'STRUCT(sku VARCHAR, qty INTEGER, price INTEGER, amount INTEGER)[]',"
            "'coupons':'STRUCT(code VARCHAR, discount INTEGER)[]'}")
    con.execute(f"CREATE TABLE raw AS SELECT * FROM read_json('{path}', format='array', columns={cols})")
    q3 = """SELECT COUNT(*) n, SUM(i.amount) ia, SUM(c.discount) cd, SUM(o.shipping) sh, SUM(o.order_total) ot
            FROM raw o
            LEFT JOIN LATERAL (SELECT UNNEST(o.items, recursive := true)) i ON true
            LEFT JOIN LATERAL (SELECT UNNEST(o.coupons, recursive := true)) c ON true"""
    r = con.execute(q3).fetchone()
    res["③SQLで明細・クーポンを\nそれぞれ横に結合"] = (r[0], {"items_amount": r[1], "coupons": r[2] or 0, "shipping": r[3], "order_total": r[4]})
    # ④ DuckDB：同じ SELECT で2つの配列を UNNEST（長さの長いほうに合わせて並べる）
    q4 = """WITH u AS (SELECT order_id, shipping, order_total, UNNEST(items) it, UNNEST(coupons) cp FROM raw)
            SELECT COUNT(*), SUM(it.amount), SUM(cp.discount), SUM(shipping), SUM(order_total) FROM u"""
    r = con.execute(q4).fetchone()
    res["④同じSELECTで2つを\nUNNEST（DuckDB）"] = (r[0], {"items_amount": r[1], "coupons": r[2] or 0, "shipping": r[3], "order_total": r[4]})
    # ⑤ 明細を行にし、クーポンは注文ごとに合計した列にする
    q5 = """WITH it AS (SELECT o.order_id, i.amount, o.shipping, o.order_total,
                   list_sum(list_transform(o.coupons, x -> x.discount)) AS coupon_sum
                   FROM raw o, LATERAL (SELECT UNNEST(o.items, recursive := true)) i)
            SELECT COUNT(*), SUM(amount), SUM(coupon_sum), SUM(shipping), SUM(order_total) FROM it"""
    r = con.execute(q5).fetchone()
    res["⑤明細を行に、クーポンは\n注文ごとの合計を列に"] = (r[0], {"items_amount": r[1], "coupons": r[2] or 0, "shipping": r[3], "order_total": r[4]})
    # ⑥ 表を3つに分ける（注文・明細・クーポン）。合計はそれぞれの表で取る
    q6o = "SELECT COUNT(*), SUM(shipping), SUM(order_total) FROM raw"
    q6i = "SELECT COUNT(*), SUM(i.amount) FROM raw o, LATERAL (SELECT UNNEST(o.items, recursive := true)) i"
    q6c = "SELECT COUNT(*), SUM(c.discount) FROM raw o, LATERAL (SELECT UNNEST(o.coupons, recursive := true)) c"
    o6, i6, c6 = con.execute(q6o).fetchone(), con.execute(q6i).fetchone(), con.execute(q6c).fetchone()
    res["⑥表を3つに分けて\nそれぞれで合計"] = (o6[0] + i6[0] + c6[0], {"items_amount": i6[1], "coupons": c6[1] or 0, "shipping": o6[1], "order_total": o6[2]},
                                     {"orders": o6[0], "items": i6[0], "coupons": c6[0]})
    con.close()
    out = []
    for k, v in res.items():
        n, s = v[0], v[1]
        row = {"method": k, "rows": int(n)}
        for key in T:
            row[key + "_err_pct"] = (np.nan if s[key] is None or (isinstance(s[key], float) and np.isnan(s[key])) else ((float(s[key]) / T[key] - 1) * 100 if T[key] else 0.0))
        if len(v) > 2: row.update({"tables": v[2]})
        out.append(row)
    return pd.DataFrame(out), T


def main():
    rng = np.random.default_rng(SEED)
    orders = make_orders(rng, N)
    path = DATA / "fictional_orders.json"
    json.dump(orders, open(path, "w"), ensure_ascii=False)
    tab, T = flatten_all(orders, path)
    n_items = sum(len(o["items"]) for o in orders); n_coupons = sum(len(o["coupons"]) for o in orders)
    share_cp = float(np.mean([len(o["coupons"]) > 0 for o in orders]))
    tab["rows_per_order"] = tab.rows / N
    tab.drop(columns=["tables"], errors="ignore").to_csv(RES / "methods.csv", index=False)

    # 正しさの確認：⑥ は4つとも0
    six = tab.iloc[-1]
    assert all(abs(six[k + "_err_pct"]) < 1e-9 for k in T)

    # クーポンの付いた注文の割合を変える
    sweep = []
    for p in [0.0, 0.1, 0.2, 0.4, 0.6, 0.8]:
        r2 = np.random.default_rng(SEED + int(p * 100))
        o2 = make_orders(r2, 4_000, p_coupon=p)
        p2 = RES / "_tmp494.json"; json.dump(o2, open(p2, "w"))
        t2, _ = flatten_all(o2, p2); p2.unlink()
        for _, x in t2.iterrows():
            sweep.append({"p_coupon": p, "method": x["method"].replace("\n", ""), "rows_per_order": x.rows / 4000,
                          "items_err": x.items_amount_err_pct, "order_total_err": x.order_total_err_pct})
    sw = pd.DataFrame(sweep); sw.to_csv(RES / "sweep_coupon_share.csv", index=False)

    res = {"orders": N, "items": n_items, "coupons": n_coupons, "share_orders_with_coupon": share_cp,
           "items_per_order": n_items / N, "truth": {k: int(v) for k, v in T.items()},
           "methods": json.loads(tab.drop(columns=["tables"], errors="ignore").to_json(orient="records", force_ascii=False)),
           "six_tables": tab.iloc[-1]["tables"]}
    json.dump(res, open(RES / "a494_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：行の数
    labs = list(tab.method)
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    y = np.arange(len(tab))[::-1]
    ax.barh(y, tab.rows_per_order, color=[GRAY, ORANGE, ORANGE, BLUE, GREEN, BLUE])
    for yy, v, n in zip(y, tab.rows_per_order, tab.rows): ax.text(v + 0.04, yy, f"{n:,}行（注文の{v:.2f}倍）", va="center", fontsize=9.5)
    ax.set_yticks(y, labs, fontsize=8.8); ax.set_xlim(0, tab.rows_per_order.max() * 1.45)
    ax.axvline(1, color=INK, lw=0.8, ls=":"); ax.set_xlabel("行の数（注文1件あたり）")
    ax.set_title(f"注文{N:,}件の JSON を平らにすると、行は何倍になるか")
    save(fig, "a494_rows.png", f"架空の注文 JSON（seed 494）。明細は平均{n_items/N:.2f}行、クーポンは{share_cp*100:.0f}%の注文に1〜3枚")

    # 図2：4つの合計のずれ
    keys = [("items_amount", "明細の金額"), ("coupons", "クーポンの金額"), ("shipping", "送料"), ("order_total", "注文の合計")]
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    w = 0.2; x = np.arange(len(tab))
    cols = [BLUE, GREEN, GRAY, ORANGE]
    for j, (k, lab) in enumerate(keys):
        v = tab[k + "_err_pct"].values
        ax.bar(x + (j - 1.5) * w, np.nan_to_num(v), width=w, color=cols[j], label=lab)
        for xi, vv in zip(x, v):
            if np.isnan(vv): ax.text(xi + (j - 1.5) * w, 3, "—", ha="center", fontsize=8, color=GRAY)
            elif abs(vv) > 0.05: ax.text(xi + (j - 1.5) * w, vv + (4 if vv > 0 else -12), f"{vv:+.0f}%", ha="center", fontsize=7.5, rotation=90)
    ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x, labs, fontsize=8)
    ax.set_ylabel("正しい合計からのずれ（%）"); ax.legend(fontsize=9, frameon=False, ncol=4, loc="upper right")
    ax.set_ylim(min(-20, np.nanmin(tab[[k + "_err_pct" for k, _ in keys]].values) * 1.2), np.nanmax(tab[[k + "_err_pct" for k, _ in keys]].values) * 1.25)
    ax.set_title("平らにした表をそのまま SUM すると、4つの合計はどれだけずれるか")
    save(fig, "a494_sums.png", "架空の注文 JSON（seed 494）で作成。①はクーポンの列がないので「—」")

    # 図3：クーポンの付いた注文の割合と、明細の金額のずれ
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    for m, c, mk in [("②明細とクーポンを順に explode", ORANGE, "o-"), ("④同じSELECTで2つをUNNEST（DuckDB）", BLUE, "s--"),
                     ("⑥表を3つに分けてそれぞれで合計", GREEN, "^-")]:
        d = sw[sw.method == m]
        ax.plot(d.p_coupon * 100, d.items_err, mk, color=c, label=m)
    ax.set_xlabel("クーポンが付いた注文の割合（%）"); ax.set_ylabel("明細の金額の合計のずれ（%）")
    ax.legend(fontsize=9, frameon=False); ax.set_title("クーポンが増えると、明細の金額の水増しも増える")
    save(fig, "a494_sweep.png", "架空の注文 JSON（各4,000件、seed 494〜）で作成。クーポンは1枚以上付く注文で1〜3枚")
    print(json.dumps({k: v for k, v in res.items() if k != "methods"}, ensure_ascii=False))
    print(tab.drop(columns=["tables"], errors="ignore").round(2).to_string())
    print(sw.round(2).to_string())


if __name__ == "__main__":
    main()
