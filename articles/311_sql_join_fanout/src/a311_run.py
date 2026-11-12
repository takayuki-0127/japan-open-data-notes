"""311 表をつなぐと、合計はなぜ増えたり減ったりするのか
架空の注文・明細・支払・店マスタを作り、素朴な結合7つの合計を正解と比べ、5つの照合が見つけるかを数える"""
import json, re
import numpy as np, pandas as pd, duckdb
from common import SQL, RES, tsql_to_duckdb

SEED = 311
rng = np.random.default_rng(SEED)
N_ORD, N_STORE = 40_000, 50


def make():
    stores = pd.DataFrame({"store_code": [f"S{n:03d}" for n in range(1, N_STORE + 1)],
                           "region": rng.choice(["関東", "関西", "中部", "九州"], N_STORE, p=[.4, .25, .2, .15])})
    # 注文：店は大きさに差をつける。3% はマスタにない店コード（新しい店・打ち間違い・末尾の空白）
    w = rng.gamma(2.0, 1.0, N_STORE); w /= w.sum()
    code = rng.choice(stores.store_code, N_ORD, p=w).astype(object)
    bad = rng.random(N_ORD) < 0.03
    kinds = rng.choice(3, N_ORD)
    for k in np.where(bad)[0]:
        code[k] = [f"S{rng.integers(51, 56):03d}", code[k].lower(), code[k] + " "][kinds[k]]
    n_items = rng.choice([1, 2, 3, 4, 5, 6], N_ORD, p=[.30, .27, .20, .12, .07, .04])
    orders = pd.DataFrame({"order_id": np.arange(1, N_ORD + 1), "store_code": code,
                           "shipping_fee": rng.choice([0, 550, 880], N_ORD, p=[.35, .5, .15])})
    oid = np.repeat(orders.order_id.values, n_items)
    items = pd.DataFrame({"order_id": oid, "line_no": np.concatenate([np.arange(1, n + 1) for n in n_items]),
                          "line_amount": (rng.lognormal(7.6, 0.7, len(oid)).round(-1)).astype(int)})
    orders["order_amount"] = items.groupby("order_id").line_amount.sum().reindex(orders.order_id).values + orders.shipping_fee
    # 支払：8% の注文は2回に分けて支払う（ポイントと現金など）。0.5% は支払の行がまだない
    split = rng.random(N_ORD) < 0.08
    nopay = rng.random(N_ORD) < 0.005
    rows = []
    for o, amt, sp, npay in zip(orders.order_id.values, orders.order_amount.values, split, nopay):
        if npay:
            continue
        if sp:
            a = int(round(amt * rng.uniform(0.1, 0.5), -1)); rows += [(o, 1, a), (o, 2, amt - a)]
        else:
            rows.append((o, 1, amt))
    payments = pd.DataFrame(rows, columns=["order_id", "pay_no", "paid_amount"])
    # 履歴つきの店マスタ：10店は地域の区分が変わり、古い行と今の行の2行がある
    perm = stores.sample(N_STORE, random_state=SEED).reset_index(drop=True)   # 区分が変わる順（固定）

    def hist(k):
        h = pd.concat([stores.assign(is_current=1), perm.head(k).assign(region="（旧区分）", is_current=0)])
        return h.sort_values(["store_code", "is_current"]).reset_index(drop=True)
    # S7 用：増える分と消える分がいちばん近くなる店の数を探す
    base = orders.order_amount.sum(); inm = orders.store_code.isin(stores.store_code)
    sweep = []
    for k in range(0, 21):
        mult = np.where(inm, np.where(orders.store_code.isin(perm.head(k).store_code), 2, 1), 0)
        sweep.append({"区分が変わった店の数": k, "合計の差(%)": round(((orders.order_amount * mult).sum() / base - 1) * 100, 3),
                      "行数の差(%)": round((mult.sum() / N_ORD - 1) * 100, 3), "増えた行": int((mult == 2).sum()), "消えた行": int((mult == 0).sum())})
    sweep = pd.DataFrame(sweep); k7 = int(sweep["合計の差(%)"].abs().idxmin())
    return stores, orders, items, payments, hist(10), hist(k7), sweep, k7


def blocks(path):
    out = {}
    for b in re.split(r"-- name: ", (SQL / path).read_text(encoding="utf-8"))[1:]:
        name, body = b.split("\n", 1)
        out[name.strip()] = body.strip()
    return out


def run(con, q):
    return con.execute(tsql_to_duckdb(q).replace("dbo.", "")).fetchone()


def main():
    stores, orders, items, payments, store_history, store_history_small, sweep, k7 = make()
    con = duckdb.connect()
    for n, df in [("stores", stores), ("orders", orders), ("order_items", items), ("payments", payments), ("store_history", store_history), ("store_history_small", store_history_small)]:
        con.register(n + "_df", df); con.execute(f"CREATE TABLE {n} AS SELECT * FROM {n}_df")
    truth = {"S1": int(orders.shipping_fee.sum()), "S2": int(orders.order_amount.sum()), "S3": int(items.line_amount.sum()),
             "S4": int(orders.order_amount.sum()), "S5": int(orders.order_amount.sum()), "S6": int(orders.order_amount.sum()), "S7": int(orders.order_amount.sum())}
    naive, fixed, checks = blocks("naive.sql"), blocks("fixed.sql"), blocks("checks.sql")
    # 場面ごとの「結合（FROM 句）」「足す列」「元の表と列」「相手の表とキー」
    spec = {
        "S1": ("dbo.orders AS o JOIN dbo.order_items AS i ON i.order_id = o.order_id", "o.shipping_fee", "dbo.orders", "shipping_fee", "dbo.order_items", "order_id"),
        "S2": ("dbo.orders AS o JOIN dbo.payments AS p ON p.order_id = o.order_id", "o.order_amount", "dbo.orders", "order_amount", "dbo.payments", "order_id"),
        "S3": ("dbo.orders AS o JOIN dbo.order_items AS i ON i.order_id = o.order_id JOIN dbo.payments AS p ON p.order_id = o.order_id", "i.line_amount", "dbo.order_items", "line_amount", "dbo.payments", "order_id"),
        "S4": ("dbo.orders AS o JOIN dbo.stores AS s ON s.store_code = o.store_code", "o.order_amount", "dbo.orders", "order_amount", "dbo.stores", "store_code"),
        "S5": ("dbo.orders AS o LEFT JOIN dbo.store_history AS h ON h.store_code = o.store_code", "o.order_amount", "dbo.orders", "order_amount", "dbo.store_history", "store_code"),
        "S6": ("dbo.orders AS o JOIN dbo.store_history AS h ON h.store_code = o.store_code", "o.order_amount", "dbo.orders", "order_amount", "dbo.store_history", "store_code"),
        "S7": ("dbo.orders AS o JOIN dbo.store_history_small AS h ON h.store_code = o.store_code", "o.order_amount", "dbo.orders", "order_amount", "dbo.store_history_small", "store_code"),
    }
    rows, found = [], []
    n_orders = len(orders)
    for name in naive:
        s = name[:2]; joined, col, st, sc, right, key = spec[s]
        nv = int(run(con, naive[name])[0]); fx = int(run(con, fixed[name])[0])
        after = int(run(con, f"SELECT COUNT(*) FROM {joined}")[0])
        extra = int(run(con, checks["C2_結合後に注文番号が重なっていないか"].replace("{JOINED}", joined))[0])
        lost = int(run(con, checks["C3_結合後に注文番号が減っていないか"].replace("{JOINED}", joined))[0])
        c4 = run(con, checks["C4_合計を元の表の合計と比べる"].replace("{JOINED}", joined).replace("{COL}", col).replace("{SRC_TABLE}", st).replace("{SRC_COL}", sc))
        dup = int(run(con, checks["C5_つなぐ相手のキーが重なっていないか"].replace("{RIGHT}", right).replace("{KEY}", key))[0])
        # S1 の正解は「明細のある注文の送料」＝全注文（明細のない注文はない）。S3 の元の表は明細
        rows.append({"場面": name, "正解": truth[s], "素朴な結合": nv, "直した書き方": fx, "素朴÷正解": round(nv / truth[s], 4),
                     "差(%)": round((nv / truth[s] - 1) * 100, 2), "結合前の行数": n_orders if s != "S3" else len(items),
                     "結合後の行数": after, "増えた行": extra, "消えた注文": lost, "消えた注文(%)": round(lost / n_orders * 100, 2),
                     "相手のキーの重なり": dup})
        base = n_orders
        tol = 0.5   # 「0.5% 以内の差は丸めの違いとして通す」照合
        found.append({"場面": name,
                      "C1 行数を比べる": int(after != base),
                      "C2 注文番号の重なり": int(extra > 0),
                      "C3 注文番号の欠け": int(lost > 0),
                      "C4 合計を比べる": int(int(c4[0]) != int(c4[1])),
                      "C5 相手のキーの重なり": int(dup > 0),
                      "C1（0.5%以内は通す）": int(abs(after / base - 1) * 100 > tol),
                      "C4（0.5%以内は通す）": int(abs(int(c4[1]) / int(c4[0]) - 1) * 100 > tol)})
        assert fx == truth[s], (name, fx, truth[s])
    res = pd.DataFrame(rows); fd = pd.DataFrame(found)
    # S2・S3 の直した書き方は、支払の行がない注文（0.5%）を内部結合で落とす。その分を別に記録
    nopay = n_orders - payments.order_id.nunique()
    res.to_csv(RES / "scenarios.csv", index=False); fd.to_csv(RES / "checks_found.csv", index=False)
    sweep.to_csv(RES / "cancel_sweep.csv", index=False)
    best = sweep.iloc[k7]
    summary = {"seed": SEED, "注文": n_orders, "明細": len(items), "支払": len(payments), "店": N_STORE,
               "マスタにない店コードの注文": int((~orders.store_code.isin(stores.store_code)).sum()),
               "分けて支払った注文": int((payments.groupby("order_id").size() > 1).sum()),
               "支払の行がない注文": int(nopay), "履歴が2行の店": 10,
               "1注文あたりの明細": round(len(items) / n_orders, 3),
               "見つけた数(7場面中)": {c: int(fd[c].sum()) for c in fd.columns[1:]},
               "S7で使った店の数（合計の差が最も小さい点）": {k: float(v) for k, v in best.items()}}
    (RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(res.drop(columns=["正解", "素朴な結合", "直した書き方"]).to_string()); print(fd.to_string()); print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(sweep.to_string())


if __name__ == "__main__":
    main()
