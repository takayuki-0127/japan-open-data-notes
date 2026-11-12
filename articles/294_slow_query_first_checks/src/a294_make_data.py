"""架空の注文データ（100万行）を SQLite に作る。seed 294"""
import sqlite3, numpy as np
from common import DATA
N = 1_000_000
rng = np.random.default_rng(294)
def build(path=DATA / "orders.sqlite"):
    if path.exists(): path.unlink()
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE orders(order_id INTEGER PRIMARY KEY, customer_id INTEGER, store_id INTEGER,
                   order_date TEXT, amount INTEGER, status TEXT, bucket INTEGER)""")
    cust = rng.integers(1, 100_001, N); store = rng.integers(1, 201, N)
    day = rng.integers(0, 365 * 3, N)  # 2023-01-01 から3年
    dates = (np.datetime64("2023-01-01") + day).astype(str)
    amt = np.round(rng.lognormal(8, 0.6, N)).astype(int)
    st = rng.choice(["完了", "取消", "返品"], N, p=[0.9, 0.07, 0.03])
    bucket = rng.integers(0, 100, N)  # 0〜99 の一様。絞り込みの割合を変える実験用
    rows = zip(range(1, N + 1), cust.tolist(), store.tolist(), dates.tolist(), amt.tolist(), st.tolist(), bucket.tolist())
    con.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", rows)
    con.commit(); con.execute("ANALYZE"); con.commit(); con.close()
    return path
if __name__ == "__main__":
    print(build())
