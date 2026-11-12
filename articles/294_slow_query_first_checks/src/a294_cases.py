"""遅いクエリでまず見るところ：5つの場面で、実行プランと「仕事の量」と時間を比べる（SQLite・100万行）
仕事の量は SQLite の仮想マシンの命令数（1,000命令ごとに数える）。時間と違って、機械の速さや混み具合で変わらない"""
import json, sqlite3, statistics, time, shutil, tempfile
from pathlib import Path
from common import DATA, RES
from a294_make_data import build

def con_fresh():
    src = DATA / "orders.sqlite"
    if not src.exists(): build(src)
    work = Path(tempfile.mkdtemp(prefix="zz_t294_")) / "work.sqlite"; shutil.copy(src, work)
    global WORK; WORK = work
    return sqlite3.connect(work)

def plan(con, q, p=()):
    return " / ".join(r[3] for r in con.execute("EXPLAIN QUERY PLAN " + q, p))

def measure(con, q, p=(), reps=5):
    steps = [0]
    def h(): steps[0] += 1; return 0
    con.set_progress_handler(h, 1000)
    con.execute(q, p).fetchall()
    con.set_progress_handler(None, 0)
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); res = con.execute(q, p).fetchall(); ts.append(time.perf_counter() - t)
    return {"plan": plan(con, q, p), "kilo_steps": steps[0], "ms": round(statistics.median(ts) * 1000, 2), "result": res[:3]}

con = con_fresh()
cases = []
def case(name, why, before, after, setup=None, p=()):
    b = measure(con, before, p)
    if setup:
        for s in setup: con.execute(s)
        con.execute("ANALYZE")
    a = measure(con, after, p)
    assert sorted(map(str, b["result"])) == sorted(map(str, a["result"])), name  # 答えは同じ
    cases.append({"case": name, "why": why, "before": b, "after": a,
                  "step_ratio": round(b["kilo_steps"] / max(a["kilo_steps"], 1), 1),
                  "time_ratio": round(b["ms"] / max(a["ms"], 0.01), 1)})

# 1 索引がない：1人の客の注文
case("1 索引がない", "絞り込む列に索引がないと、100万行を全部読む",
     "SELECT COUNT(*), SUM(amount) FROM orders WHERE customer_id = ?",
     "SELECT COUNT(*), SUM(amount) FROM orders WHERE customer_id = ?",
     ["CREATE INDEX ix_cust ON orders(customer_id)"], (12345,))
# 2 列に関数をかけている：日付の年で絞る
con.execute("CREATE INDEX ix_date ON orders(order_date)"); con.execute("ANALYZE")
case("2 列に関数をかけている", "列を関数で包むと、索引があっても使えない（範囲の条件に書き直す）",
     "SELECT COUNT(*), SUM(amount) FROM orders WHERE strftime('%Y-%m', order_date) = '2025-03'",
     "SELECT COUNT(*), SUM(amount) FROM orders WHERE order_date >= '2025-03-01' AND order_date < '2025-04-01'")
# 3 索引の列の順番：店×期間
con.execute("CREATE INDEX ix_date_store ON orders(order_date, store_id)")
case("3 複合索引の列の順番", "（日付, 店）の順だと期間内を全部なめる。等号の列を先にすると狭く読める",
     "SELECT COUNT(*), SUM(amount) FROM orders INDEXED BY ix_date_store WHERE store_id = 17 AND order_date >= '2025-01-01' AND order_date < '2025-07-01'",
     "SELECT COUNT(*), SUM(amount) FROM orders INDEXED BY ix_store_date WHERE store_id = 17 AND order_date >= '2025-01-01' AND order_date < '2025-07-01'",
     ["CREATE INDEX ix_store_date ON orders(store_id, order_date)"])
# 4 索引だけで答えられない：金額を取りに本体へ戻る
case("4 索引だけで答えられない", "索引に金額がないと、1行ずつ本体を読みに行く。金額も索引に含めると索引だけで済む",
     "SELECT SUM(amount) FROM orders INDEXED BY ix_store_date WHERE store_id BETWEEN 1 AND 20",
     "SELECT SUM(amount) FROM orders INDEXED BY ix_store_amt WHERE store_id BETWEEN 1 AND 20",
     ["CREATE INDEX ix_store_amt ON orders(store_id, amount)"])
con.execute("CREATE INDEX ix_status ON orders(status)"); con.execute("ANALYZE")
# 5 索引が逆効果：ほとんどの行が当てはまる条件
case("5 ほとんどの行が当てはまる", "9割の行が当てはまる条件では、索引をたどるより全部読むほうが速い",
     "SELECT SUM(amount) FROM orders INDEXED BY ix_status WHERE status = '完了'",
     "SELECT SUM(amount) FROM orders NOT INDEXED WHERE status = '完了'",
     ["SELECT 1"])
json.dump(cases, open(RES / "cases.json", "w"), ensure_ascii=False, indent=1, default=str)

# 6 絞り込みの割合を変えると、索引と全件読みのどちらが速いか
con.execute("CREATE INDEX ix_bucket ON orders(bucket)"); con.execute("ANALYZE")
sel = []
for k in [1, 2, 5, 10, 20, 30, 50, 70, 100]:
    qi = f"SELECT SUM(amount) FROM orders INDEXED BY ix_bucket WHERE bucket < {k}"
    qs = f"SELECT SUM(amount) FROM orders NOT INDEXED WHERE bucket < {k}"
    a, b = measure(con, qi), measure(con, qs)
    auto = plan(con, f"SELECT SUM(amount) FROM orders WHERE bucket < {k}")
    sel.append({"pct": k, "index_ms": a["ms"], "scan_ms": b["ms"], "index_ksteps": a["kilo_steps"], "scan_ksteps": b["kilo_steps"], "auto_plan": auto})
json.dump(sel, open(RES / "selectivity.json", "w"), ensure_ascii=False, indent=1)
for c in cases: print(c["case"], c["before"]["kilo_steps"], c["after"]["kilo_steps"], c["step_ratio"], c["before"]["ms"], c["after"]["ms"], c["time_ratio"]); print("  ", c["before"]["plan"], "=>", c["after"]["plan"])
for s in sel: print(s)
con.close(); shutil.rmtree(WORK.parent)
