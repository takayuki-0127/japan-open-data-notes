"""集計をストアドプロシージャ（引数の型と検査つき）にまとめると、何を止められるか。
DuckDB では T-SQL のプロシージャがないので、同じ検査を Python の関数＋パラメータ付きの文で再現した（sql/sp_sales_summary.sql と同じ規則）。
架空の依頼 1,000件（85%は正しい入力、15%はよくある入力の誤り）を、文字列をつなぐ形とプロシージャの形の両方に通して結果を比べる。seed 295"""
import json, datetime as dt, numpy as np, pandas as pd, duckdb
from common import RES, DATA
rng = np.random.default_rng(295)
con = duckdb.connect()
stores = [f"S{i:03d}" for i in range(1, 51)]
n = 200_000
day0 = dt.date(2024, 1, 1)
orders = pd.DataFrame({"store_code": rng.choice(stores, n), "order_date": [day0 + dt.timedelta(int(d)) for d in rng.integers(0, 731, n)],
                       "amount": np.round(rng.lognormal(8, 0.6, n)).astype(int), "status": rng.choice(["完了", "取消"], n, p=[0.93, 0.07])})
con.register("o", orders); con.execute("CREATE TABLE orders AS SELECT * FROM o"); con.execute("CREATE TABLE stores AS SELECT unnest(?) AS store_code", [stores])

def truth(store, f, t):
    return con.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE store_code=? AND order_date BETWEEN ? AND ? AND status='完了'", [store, f, t]).fetchone()

def adhoc(store, f, t):  # 文字列をつないで作る
    q = f"SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE store_code = '{store}' AND order_date BETWEEN '{f}' AND '{t}' AND status = '完了'"
    try: return ("ok", con.execute(q).fetchone())
    except Exception as e: return ("error", type(e).__name__)

class Rejected(Exception): pass
def proc(store, f, t):  # プロシージャ：型をそろえて受け取り、検査してから集計
    try:
        if store is None or f is None or t is None: raise Rejected("必須")
        f, t = dt.date.fromisoformat(str(f)), dt.date.fromisoformat(str(t))   # DATE 型で受け取る
        if len(store) != 4: raise Rejected("長さ")                             # IF LEN(@store_code) <> 4 THROW
        if f > t: raise Rejected("期間の逆転")
        if not con.execute("SELECT COUNT(*) FROM stores WHERE store_code=?", [store]).fetchone()[0]: raise Rejected("店コードなし")
        return ("ok", con.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE store_code=? AND order_date>=? AND order_date<? AND status='完了'",
                                  [store, f, t + dt.timedelta(1)]).fetchone())
    except Rejected as e: return ("rejected", str(e))
    except ValueError as e: return ("rejected", "日付の形")

KINDS = {"正しい入力": 0.85, "期間の逆転": 0.03, "ありえない日付": 0.03, "全角の店コード": 0.03, "存在しない店コード": 0.02, "引用符入りの文字": 0.02, "空欄": 0.02}
def make_request(kind):
    s = str(rng.choice(stores)); a = day0 + dt.timedelta(int(rng.integers(0, 700))); b = a + dt.timedelta(int(rng.integers(0, 30)))
    f, t, exp = a.isoformat(), b.isoformat(), (s, a.isoformat(), b.isoformat())
    if kind == "期間の逆転": f, t = (b + dt.timedelta(1)).isoformat(), a.isoformat(); exp = None
    elif kind == "ありえない日付": f = f[:8] + "31" if f[5:7] in ("02", "04", "06", "09", "11") else f[:5] + "13" + f[7:]; exp = None
    elif kind == "全角の店コード": s = s.translate(str.maketrans("S0123456789", "Ｓ０１２３４５６７８９")); exp = None
    elif kind == "存在しない店コード": s = f"S{int(rng.integers(51, 100)):03d}"; exp = None
    elif kind == "引用符入りの文字": s = s + "' OR '1'='1"; exp = None
    elif kind == "空欄": t = None; exp = None
    return s, f, t, exp

names = list(KINDS); kinds = rng.choice(names, 1000, p=list(KINDS.values()))
rows = []
for k in kinds:
    s, f, t, exp = make_request(k)
    right = truth(*exp) if exp else None
    for impl, fn in [("文字列をつなぐ", adhoc), ("プロシージャ", proc)]:
        st, val = fn(s, f, t)
        if exp is not None: outcome = "正しい答え" if (st == "ok" and tuple(val) == tuple(right)) else ("誤った答え" if st == "ok" else "止まった")
        else: outcome = "止まった（エラー・はね返し）" if st != "ok" else ("黙って0を返した" if val[0] == 0 else "黙って誤った数字を返した")
        rows.append({"kind": k, "impl": impl, "status": st, "outcome": outcome, "reason": None if st == "ok" else str(val), "orders": val[0] if st == "ok" else None, "sales": val[1] if st == "ok" else None})
df = pd.DataFrame(rows); df.to_csv(RES / "requests_outcomes.csv", index=False)
tab = df.groupby(["impl", "kind", "outcome"]).size().unstack(fill_value=0)
tab.to_csv(RES / "outcome_table.csv")
summary = {}
for impl in ["文字列をつなぐ", "プロシージャ"]:
    d = df[df.impl == impl]; bad = d[d.kind != "正しい入力"]
    summary[impl] = {"requests": int(len(d)), "bad_inputs": int(len(bad)),
                     "silent_wrong": int(bad.outcome.str.startswith("黙って").sum()), "stopped": int(bad.outcome.str.startswith("止まった").sum()),
                     "valid_correct": int((d[d.kind == "正しい入力"].outcome == "正しい答え").sum()), "valid": int((d.kind == "正しい入力").sum())}
inj = df[(df.kind == "引用符入りの文字") & (df.impl == "文字列をつなぐ")]
summary["injection_sales_ratio_median"] = float((inj.sales / orders[orders.status == "完了"].amount.sum()).median()) if len(inj) else None
# 1か月の正しい依頼で、引用符入りの文字が返す数字は全店の何倍か
s0 = "S017"; ok = truth(s0, "2025-04-01", "2025-04-30"); bad = adhoc(s0 + "' OR '1'='1", "2025-04-01", "2025-04-30")[1]
summary["example"] = {"right": [int(x) for x in ok], "injected": [int(x) for x in bad], "ratio": round(bad[1] / ok[1], 1)}
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1)); print(tab.to_string())
