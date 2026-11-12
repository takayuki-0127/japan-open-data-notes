"""404 SQL を書き直したとき、結果が同じだとどう確かめるか
架空の注文20万行で、もとの集計 SQL と、違いを1つずつ入れた書き直し10本を比べる。
確かめ方は、件数と合計・EXCEPT（両方向）・EXCEPT ALL（両方向）・行のハッシュの合計・並べずに行の位置で比べる、の5つ。
答えは同じなのに「違う」と出る書き直し6本（見かけの差）でも試す。
SQL は pairs_sql.py（T-SQL でも通る書き方に寄せた。SQL Server では未検証）。DuckDB で実行する。"""
import json
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT
from pairs_sql import BASE, DIFFS, HARMLESS

SEED = 404
SRC = "架空のデータ（作成者が乱数で作成、seed 404）"
rng = np.random.default_rng(SEED)
NO, NC = 200_000, 3000
seg = rng.choice(["個人", "法人", "学校", "官公庁"], NC, p=[.55, .3, .1, .05]).astype(object)
sp = rng.choice(np.where(seg == "法人")[0], 20, replace=False); seg[sp] = "法人 "          # 後ろに空白のついた20件
cust = pd.DataFrame({"cust_id": np.arange(1, NC + 1), "segment": seg})
ts = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365 * 86400, NO), unit="s")
qty = rng.integers(1, 9, NO); price = rng.choice([198, 298, 480, 980, 1280, 2980], NO)
orders = pd.DataFrame({"order_id": np.arange(1, NO + 1), "cust_id": rng.integers(1, NC + 1, NO), "ordered_at": ts,
                       "amount": np.round(qty * price * 1.1, 2), "discount": np.where(rng.random(NO) < .3, np.round(qty * price * .05, 2), np.nan),
                       "status": rng.choice(["done", "cancel", None], NO, p=[.93, .05, .02])})
orph = rng.random(NO) < .01; orders.loc[orph, "cust_id"] = 90001                      # マスタにない顧客（1%）
dupi = rng.choice(NO, 800, replace=False)                                              # まったく同じ明細の行（正しい重複）800行
orders = pd.concat([orders, orders.iloc[dupi].assign(order_id=lambda d: d.order_id + 1_000_000)], ignore_index=True)
cust.to_csv(DATA / "customers.csv", index=False)
orders.sample(5000, random_state=SEED).sort_values("order_id").to_csv(DATA / "orders_sample5000.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("c0", cust); con.register("o0", orders)
con.execute("CREATE TABLE customers AS SELECT * FROM c0")
con.execute("""CREATE TABLE orders AS SELECT order_id, cust_id, ordered_at, CAST(amount AS DECIMAL(12,2)) AS amount,
               CAST(discount AS DECIMAL(12,2)) AS discount, status FROM o0 ORDER BY order_id""")
con.execute("CREATE TABLE customers_dup AS SELECT * FROM customers UNION ALL SELECT * FROM customers WHERE cust_id <= 15")
con.execute("CREATE TABLE orders_f AS SELECT order_id, cust_id, ordered_at, CAST(amount AS DOUBLE)/3 AS amount FROM orders ORDER BY order_id")
con.execute("CREATE TABLE orders_f_desc AS SELECT * FROM orders_f ORDER BY order_id DESC")


def make(a, b):
    con.execute("DROP TABLE IF EXISTS ra"); con.execute("DROP TABLE IF EXISTS rb")
    con.execute("CREATE TABLE ra AS " + a); con.execute("CREATE TABLE rb AS " + b)


def cols(t): return [r[0] for r in con.execute(f"DESCRIBE {t}").fetchall()], [r[1] for r in con.execute(f"DESCRIBE {t}").fetchall()]


def norm(t):
    """そろえてから比べる：列を名前の順に並べ、数は小数2桁の DECIMAL に、文字は TRIM なしでそのまま"""
    c, ty = cols(t); out = []
    for n, y in sorted(zip(c, ty)):
        out.append(f'CAST(ROUND("{n}", 2) AS DECIMAL(18,2)) AS "{n}"' if any(k in y for k in ["DOUBLE", "DECIMAL", "INT", "FLOAT", "HUGEINT"]) else f'"{n}"')
    return f"(SELECT {', '.join(out)} FROM {t})"


def checks(A, B, numcol):
    """5つの確かめ方。True＝「違いあり」と出た"""
    r = {}
    try:
        la, lb = con.execute(f"SELECT * FROM {A}").fetchall(), con.execute(f"SELECT * FROM {B}").fetchall()
        r["並べずに行の位置で比べる"] = la != lb
    except Exception: r["並べずに行の位置で比べる"] = True
    try:
        a = con.execute(f'SELECT COUNT(*), SUM("{numcol}") FROM {A}').fetchone(); b = con.execute(f'SELECT COUNT(*), SUM("{numcol}") FROM {B}').fetchone()
        r["件数と合計（ぴったり）"] = a != b
        r["件数と合計（合計は0.1%まで許す）"] = a[0] != b[0] or abs(float(a[1]) - float(b[1])) / abs(float(a[1])) > 0.001
    except Exception: r["件数と合計（ぴったり）"] = r["件数と合計（合計は0.1%まで許す）"] = True
    for name, op in [("EXCEPT（両方向）", "EXCEPT"), ("EXCEPT ALL（両方向）", "EXCEPT ALL")]:
        try:
            n = con.execute(f"SELECT COUNT(*) FROM ((SELECT * FROM {A} {op} SELECT * FROM {B}) UNION ALL (SELECT * FROM {B} {op} SELECT * FROM {A}))").fetchone()[0]
            r[name] = n > 0
        except Exception: r[name] = True
    try:
        def h(T):
            c, _ = cols("ra" if "ra" in T else "rb") if not T.startswith("(") else (None, None)
            c = [x[0] for x in con.execute(f"DESCRIBE SELECT * FROM {T}").fetchall()]
            e = " || '|' || ".join(f"COALESCE(CAST(\"{x}\" AS VARCHAR), '<NULL>')" for x in c)
            return con.execute(f"SELECT COUNT(*), SUM(CAST(('0x' || substr(md5({e}), 1, 13)) AS BIGINT)) FROM {T}").fetchone()
        r["行のハッシュの合計と件数"] = h(A) != h(B)
    except Exception: r["行のハッシュの合計と件数"] = True
    return r


METH = ["並べずに行の位置で比べる", "件数と合計（ぴったり）", "件数と合計（合計は0.1%まで許す）", "EXCEPT（両方向）", "EXCEPT ALL（両方向）", "行のハッシュの合計と件数"]
rows = []
for name, d in DIFFS.items():
    make(d.get("a", BASE), d["b"])
    na, nb = con.execute("SELECT COUNT(*) FROM ra").fetchone()[0], con.execute("SELECT COUNT(*) FROM rb").fetchone()[0]
    sa, sb = [float(con.execute(f'SELECT SUM("{d["num"]}") FROM {t}').fetchone()[0]) for t in ("ra", "rb")]
    ndiff = con.execute("SELECT COUNT(*) FROM ((SELECT * FROM ra EXCEPT ALL SELECT * FROM rb) UNION ALL (SELECT * FROM rb EXCEPT ALL SELECT * FROM ra))").fetchone()[0]
    assert ndiff > 0, name
    r = checks("ra", "rb", d["num"]); rn = checks(norm("ra"), norm("rb"), d["num"])
    rows.append({"種類": "違いあり", "書き直し": name, "行数（前）": na, "行数（後）": nb, "合計の差": sb - sa, "合計の差（割合）": (sb - sa) / sa,
                 **{m: int(r[m]) for m in METH}, **{m + "_そろえた後": int(rn[m]) for m in METH}})
for name, d in HARMLESS.items():
    make(d["a"], d["b"])
    r = checks("ra", "rb", d["num"])
    try: rn = checks(norm("ra"), norm("rb"), d["num"])
    except Exception: rn = {m: True for m in METH}
    rows.append({"種類": "答えは同じ", "書き直し": name, "行数（前）": con.execute("SELECT COUNT(*) FROM ra").fetchone()[0],
                 "行数（後）": con.execute("SELECT COUNT(*) FROM rb").fetchone()[0], "合計の差": None, "合計の差（割合）": None,
                 **{m: int(r[m]) for m in METH}, **{m + "_そろえた後": int(rn[m]) for m in METH}})
res = pd.DataFrame(rows); res.to_csv(RES / "pairs_checks.csv", index=False)
D, H = res[res["種類"] == "違いあり"], res[res["種類"] == "答えは同じ"]
summ = pd.DataFrame({"確かめ方": METH,
                     "違い10個のうち見つけた数": [int(D[m].sum()) for m in METH],
                     "同じ答え6本で「違う」と出た数": [int(H[m].sum()) for m in METH],
                     "そろえた後：見つけた数": [int(D[m + "_そろえた後"].sum()) for m in METH],
                     "そろえた後：「違う」と出た数": [int(H[m + "_そろえた後"].sum()) for m in METH]})
summ.to_csv(RES / "summary.csv", index=False)
json.dump({"注文の行数": int(len(orders)), "顧客": NC, "確かめ方ごと": summ.to_dict("records"),
           "見つからなかった書き直し": {m: D.loc[D[m] == 0, "書き直し"].tolist() for m in METH}},
          open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
def grid(df, suffix, title, fname, note):
    fig, ax = plt.subplots(figsize=(9.6, 0.42 * len(df) + 2.2))
    M = df[[m + suffix for m in METH]].values
    ax.imshow(np.where(M == 1, 1, 0), cmap="Blues" if "違い" in title else "Oranges", vmin=0, vmax=1.6, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]): ax.text(j, i, "見つけた" if (M[i, j] and "違い" in title) else ("「違う」と出た" if M[i, j] else "―"), ha="center", va="center", fontsize=8.5)
    ax.set_xticks(range(len(METH))); ax.set_xticklabels([m.replace("（", "\n（") for m in METH], fontsize=8.5); ax.xaxis.tick_top()
    ax.set_yticks(range(len(df))); ax.set_yticklabels(df["書き直し"], fontsize=9)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title(title, pad=44, fontsize=12)
    save(fig, fname, SRC + note, y=0.0)
grid(D, "", "違いを1つ入れた書き直し10本：どの確かめ方が見つけたか", "a404_found.png", "")
grid(H, "", "答えは同じ書き直し6本：どの確かめ方が「違う」と出したか（そろえる前）", "a404_false_alarm.png", "")
fig, ax = plt.subplots(figsize=(9, 4.4)); x = np.arange(len(METH)); w = .38
ax.bar(x - w / 2, summ["そろえた後：見つけた数"], w, color=BLUE, label="違い10個のうち見つけた数")
ax.bar(x + w / 2, summ["そろえた後：「違う」と出た数"], w, color=ORANGE, label="同じ答え6本で「違う」と出た数")
for i in range(len(METH)):
    ax.text(i - w / 2, summ["そろえた後：見つけた数"][i] + .15, str(summ["そろえた後：見つけた数"][i]), ha="center", fontsize=9)
    ax.text(i + w / 2, summ["そろえた後：「違う」と出た数"][i] + .15, str(summ["そろえた後：「違う」と出た数"][i]), ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([m.replace("（", "\n（") for m in METH], fontsize=8.5); ax.set_ylim(0, 11.5)
ax.set_title("列の順・数の型・小数の桁をそろえてから比べたとき"); ax.legend(frameon=False)
save(fig, "a404_after_normalize.png", SRC + "。数は小数2桁に丸めて DECIMAL にし、列は名前の順に並べた", y=-0.06)
pd.set_option("display.width", 250); print(res.drop(columns=[c for c in res.columns if "そろえた後" in c]).to_string()); print(summ.to_string())
