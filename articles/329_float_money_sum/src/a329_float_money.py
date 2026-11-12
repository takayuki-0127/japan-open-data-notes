"""329 金額を小数（FLOAT）で持つと、合計はどれだけずれるか
架空の金額100万行（小数第2位まで）を、4バイトの浮動小数（REAL）・8バイトの浮動小数（FLOAT/DOUBLE）・10進の型（DECIMAL）で持ち、
合計・等号の判定・足す順番を比べる。DuckDB で実行（SQL Server 本体では未検証）。"""
import json
from decimal import Decimal
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 329; rng = np.random.default_rng(SEED); N = 1_000_000
cents = np.where(rng.random(N) < 0.1, -1, 1) * np.round(rng.lognormal(8.0, 1.3, N) * 100).astype(np.int64)   # 小数第2位まで（1/100 単位の整数で正を持つ）
store = rng.integers(1, 201, N)
true_total_c = int(cents.sum())
amt64 = cents / 100.0; amt32 = amt64.astype(np.float32)
df = pd.DataFrame({"id": np.arange(N), "store": store, "cents": cents})
df.head(1000).assign(amount=lambda d: d.cents / 100).to_csv(DATA / "amounts_sample_1000.csv", index=False)   # 全量は実行時に作る

con = duckdb.connect(); con.sql("SET threads = 1")   # 複数スレッドだと、DOUBLE の合計の最後の桁が実行ごとに変わることがあるため
con.register("src", df)
con.sql("""CREATE TABLE t AS SELECT id, store, CAST(cents AS DECIMAL(18,2)) / 100 AS amt_dec0, cents FROM src""")
con.sql("""CREATE TABLE m AS SELECT id, store, cents,
           CAST(cents / 100.0 AS DECIMAL(18,2)) AS amt_decimal, CAST(cents / 100.0 AS DOUBLE) AS amt_double, CAST(cents / 100.0 AS REAL) AS amt_real FROM src""")
# ---------- 1. 合計のずれ（行数を増やしながら） ----------
rowsN = [1_000, 10_000, 100_000, 1_000_000]; tot = []
for n in rowsN:
    r = con.sql(f"SELECT sum(amt_decimal), sum(amt_double), sum(amt_real), sum(cents) FROM m WHERE id < {n}").fetchone()
    t = Decimal(int(r[3])) / 100
    np32 = np.float32(0)
    c32 = np.cumsum(amt32[:n], dtype=np.float32)[-1]             # 4バイトのまま、上から順に足す
    tot.append({"行数": n, "正しい合計": float(t), "DECIMAL の差": float(Decimal(str(r[0])) - t), "DOUBLE の差（DuckDB の sum）": float(Decimal(repr(r[1])) - t),
                "REAL の差（DuckDB の sum）": float(Decimal(repr(float(r[2]))) - t), "REAL のまま順に足した差": float(Decimal(repr(float(c32))) - t),
                "DOUBLE を順に足した差": float(Decimal(repr(float(np.cumsum(amt64[:n])[-1]))) - t)})
tot = pd.DataFrame(tot); tot.to_csv(RES / "total_error.csv", index=False)
# ---------- 2. 足す順番で答えが変わるか（DOUBLE、100通りの並び） ----------
orders = {"上から順": amt64, "小さい順": np.sort(amt64), "大きい順": np.sort(amt64)[::-1], "絶対値の小さい順": amt64[np.argsort(np.abs(amt64))]}
ordres = {k: float(np.cumsum(v)[-1]) for k, v in orders.items()}
sh = []; r2 = np.random.default_rng(SEED + 1)
for i in range(100): sh.append(float(np.cumsum(r2.permutation(amt64))[-1]))
sh = np.array(sh); true_total = true_total_c / 100
order_main = {"distinct_totals_100_shuffles": int(len(set(sh.tolist()))), "max_abs_err": float(np.abs(sh - true_total).max()), "exact_hits": int((sh == true_total).sum()),
              "named_orders_err": {k: v - true_total for k, v in ordres.items()}, "pairwise_np_sum_err": float(np.sum(amt64) - true_total)}
pd.DataFrame({"並び": range(100), "合計の差（円）": sh - true_total}).to_csv(RES / "order_shuffles.csv", index=False)
# 店ごとの合計を足し直すと全体の合計と等しいか（DOUBLE と DECIMAL）
g = con.sql("SELECT (SELECT sum(s) FROM (SELECT sum(amt_double) s FROM m GROUP BY store)) = (SELECT sum(amt_double) FROM m), (SELECT sum(s) FROM (SELECT sum(amt_decimal) s FROM m GROUP BY store)) = (SELECT sum(amt_decimal) FROM m)").fetchone()
stores_eq = []
for k in range(200):   # 店ごと：明細の合計（DOUBLE）を小数第2位に丸めた値と、正しい合計が一致するか／丸めずに等号で比べると一致するか
    pass
st = con.sql("SELECT store, sum(amt_double) AS d, sum(amt_real) AS r, sum(cents) AS c FROM m GROUP BY store ORDER BY store").df()
st["true"] = st.c / 100.0
store_main = {"stores": 200, "double_equal_raw": int((st.d == st["true"]).sum()), "double_equal_after_round2": int((st.d.round(2) == st["true"]).sum()),
              "real_equal_after_round2": int((st.r.astype(float).round(2) == st["true"]).sum()), "real_max_err": float((st.r.astype(float) - st["true"]).abs().max()),
              "double_max_err": float((st.d - st["true"]).abs().max()), "group_then_total_equal_double": bool(g[0]), "group_then_total_equal_decimal": bool(g[1])}
st.to_csv(RES / "store_totals.csv", index=False)
# ---------- 3. 等号の判定：a + b = c が成り立つか（c は正しい和） ----------
eq = []; r3 = np.random.default_rng(SEED + 2)
for k in [2, 3, 5, 10, 30, 100]:
    T = 100_000; parts = np.abs(cents[r3.integers(0, N, (T, k))]) % 100_000 + 1      # 0.01〜1000.00 の正の金額を k 個
    s_true = parts.sum(axis=1) / 100.0                                                 # 正しい和を、いちばん近い DOUBLE にしたもの
    s_dbl = np.cumsum(parts / 100.0, axis=1)[:, -1]                                    # DOUBLE のまま順に足した和
    s_real = np.cumsum((parts / 100.0).astype(np.float32), axis=1, dtype=np.float32)[:, -1]
    eq.append({"足す個数": k, "DOUBLE で等号が外れる割合": float((s_dbl != s_true).mean()), "REAL で等号が外れる割合": float((s_real != (parts.sum(axis=1) / 100.0).astype(np.float32)).mean()),
               "DOUBLE を小数第2位に丸めてから比べて外れる割合": float((np.round(s_dbl, 2) != s_true).mean()), "DOUBLE の差の最大": float(np.abs(s_dbl - s_true).max())})
eq = pd.DataFrame(eq); eq.to_csv(RES / "equality.csv", index=False)
sql_eq = con.sql("SELECT 0.1::DOUBLE + 0.2::DOUBLE = 0.3::DOUBLE, 0.1::DECIMAL(9,2) + 0.2::DECIMAL(9,2) = 0.3::DECIMAL(9,2), 0.1::REAL + 0.2::REAL = 0.3::REAL").fetchone()
# REAL で表せる金額：小数第2位までの値が、4バイトで元の値に戻るか
back = float((np.round(amt32.astype(np.float64), 2) == amt64).mean()); big = float(np.abs(amt64).max())
exact7 = float(np.mean(np.abs(cents) < 2**24))
main = {"N": N, "true_total": true_total, "mean_abs_amount": float(np.abs(amt64).mean()), "max_amount": big,
        "total_error": tot.to_dict(orient="records"), "order": order_main, "stores": store_main, "equality": eq.to_dict(orient="records"),
        "sql_0.1+0.2=0.3": {"DOUBLE": bool(sql_eq[0]), "DECIMAL": bool(sql_eq[1]), "REAL": bool(sql_eq[2])},
        "real_roundtrip_share": back, "duckdb_version": duckdb.__version__}
json.dump(main, open(RES / "a329_main.json", "w"), ensure_ascii=False, indent=1)
print(tot.T.to_string()); print(json.dumps(order_main, ensure_ascii=False)); print(json.dumps(store_main, ensure_ascii=False)); print(eq.to_string()); print(main["sql_0.1+0.2=0.3"], back)

SRC = "架空の金額（作成者が乱数で作成、seed 329）。DuckDB と NumPy で計算（SQL Server 本体では未検証）"
fig, ax = plt.subplots(figsize=(8.2, 4.2)); x = np.arange(len(rowsN)); w = 0.38
a = tot["REAL のまま順に足した差"].abs().clip(lower=1e-6); b = tot["DOUBLE を順に足した差"].abs().clip(lower=1e-6)
ax.bar(x - w / 2, a, w, color=ORANGE, label="4バイトの浮動小数（REAL）"); ax.bar(x + w / 2, b, w, color=BLUE, label="8バイトの浮動小数（FLOAT・DOUBLE）")
for xi, v, raw in zip(x - w / 2, a, tot["REAL のまま順に足した差"]): ax.text(xi, v * 1.3, f"{raw:+,.2f}" if abs(raw) < 100 else f"{raw:+,.0f}", ha="center", fontsize=8.5)
for xi, v, raw in zip(x + w / 2, b, tot["DOUBLE を順に足した差"]): ax.text(xi, v * 1.3, f"{raw:+.1e}" if raw else "0", ha="center", fontsize=8.5)
ax.set_yscale("log"); ax.set_xticks(x); ax.set_xticklabels([f"{n:,}行" for n in rowsN]); ax.set_ylabel("正しい合計との差の大きさ（円、対数目盛）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("上から順に足したときの合計のずれ（10進の型は、どの行数でも差0）", loc="left", fontsize=11.5)
save(fig, "a329_total_error.png", SRC)
fig, ax = plt.subplots(figsize=(8.2, 4.0))
ax.plot(eq["足す個数"], eq["DOUBLE で等号が外れる割合"] * 100, marker="o", color=BLUE, label="8バイトのまま等号で比べる")
ax.plot(eq["足す個数"], eq["REAL で等号が外れる割合"] * 100, marker="o", color=ORANGE, label="4バイトのまま等号で比べる")
ax.plot(eq["足す個数"], eq["DOUBLE を小数第2位に丸めてから比べて外れる割合"] * 100, marker="o", color=GREEN, label="8バイトを小数第2位に丸めてから比べる")
ax.set_xscale("log"); ax.set_xticks(eq["足す個数"]); ax.set_xticklabels(eq["足す個数"]); ax.set_xlabel("足し合わせる金額の個数"); ax.set_ylabel("「明細の和 = 正しい合計」が外れた割合（%）"); ax.legend(frameon=False)
ax.set_title("明細を足した値と合計を等号で比べると、2個の和でも外れることがある", loc="left", fontsize=11.5)
save(fig, "a329_equality.png", SRC)
fig, ax = plt.subplots(figsize=(8.2, 3.8)); d = (sh - true_total)
ax.hist(d * 1e6, bins=30, color=BLUE); ax.axvline(0, color=INK, lw=0.8)
ax.set_xlabel("正しい合計との差（100万分の1円）"); ax.set_ylabel("並びの数（100通り中）")
ax.set_title(f"同じ100万行でも、足す順番を変えると合計が変わる（100通りで{order_main['distinct_totals_100_shuffles']}種類の答え）", loc="left", fontsize=11.5)
save(fig, "a329_order.png", SRC)
