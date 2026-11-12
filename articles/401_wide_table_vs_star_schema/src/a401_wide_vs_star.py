"""401 集計用の表は、1枚の大きな表と、事実とマスタに分けた表のどちらが直しやすいか
架空の売上（商品・店のマスタつき）で、同じ8本のレポートを2つの持ち方で書き、
7つの場面（マスタの変更・マスタの不備）で、直す行数と、直さないときに合わないレポートの数を数える。
SQL は sql_reports.py にあり、DuckDB で実行する（T-SQL でも同じ書き方。SQL Server では未検証）。"""
import json, re
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK
from sql_reports import REPORTS, USES

SEED = 401
rng = np.random.default_rng(SEED)
SRC = "架空のデータ（作成者が乱数で作成、seed 401）"

# ---------------- データ ----------------
DEPTS = ["食品", "飲料", "日用品", "衣料", "家電", "雑貨"]
REGIONS = ["北", "東", "中", "西", "南"]
NP_, NS = 200, 20
prod = pd.DataFrame({"product_id": np.arange(1, NP_ + 1),
                     "product_name": [f"商品{i:03d}" for i in range(1, NP_ + 1)],
                     "dept": rng.choice(DEPTS, NP_, p=[.28, .18, .2, .14, .08, .12]),
                     "unit_price": rng.choice([120, 180, 250, 380, 480, 980, 1980, 4980], NP_)})
store = pd.DataFrame({"store_id": np.arange(1, NS + 1),
                      "store_name": [f"店{i:02d}" for i in range(1, NS + 1)],
                      "region": rng.choice(REGIONS, NS)})
days = pd.date_range("2024-01-01", "2025-12-31", freq="D")
N = 300_000
pop = rng.dirichlet(np.full(NP_, 0.6))
fact = pd.DataFrame({"sale_id": np.arange(1, N + 1),
                     "sale_date": rng.choice(days, N),
                     "store_id": rng.integers(1, NS + 1, N),
                     "product_id": rng.choice(prod.product_id, N, p=pop),
                     "qty": rng.integers(1, 6, N)})
fact = fact.merge(prod[["product_id", "unit_price"]], on="product_id")
fact["amount"] = fact.qty * fact.unit_price
fact = fact.drop(columns="unit_price").sort_values("sale_id").reset_index(drop=True)
prod.to_csv(DATA / "product.csv", index=False); store.to_csv(DATA / "store.csv", index=False)
fact.sample(5000, random_state=SEED).sort_values("sale_id").to_csv(DATA / "fact_sales_sample5000.csv", index=False)


def fresh():
    """2つの持ち方を作る。star＝事実とマスタ、wide＝マスタの列を写して持つ1枚の表"""
    con = duckdb.connect(); con.execute("SET threads=1")
    con.register("p0", prod); con.register("s0", store); con.register("f0", fact)
    con.execute("CREATE TABLE product AS SELECT product_id, product_name, dept FROM p0")
    con.execute("CREATE TABLE store AS SELECT * FROM s0")
    con.execute("CREATE TABLE fact_sales AS SELECT sale_id, CAST(sale_date AS DATE) AS sale_date, store_id, product_id, qty, amount FROM f0")
    con.execute("""CREATE TABLE sales_wide AS
        SELECT f.sale_id, f.sale_date, f.store_id, s.store_name, s.region,
               f.product_id, p.product_name, p.dept, f.qty, f.amount
        FROM fact_sales f JOIN product p ON p.product_id=f.product_id JOIN store s ON s.store_id=f.store_id""")
    return con


def run(con, form):
    out = {}
    for name, q in REPORTS.items():
        d = con.execute(q[form]).df()
        out[name] = d.sort_values(list(d.columns)).reset_index(drop=True)
    return out


def n_diff(a, b):
    """8本のうち、結果が合わないレポートの本数"""
    return sum(0 if (a[k].shape == b[k].shape and (a[k].values == b[k].values).all()) else 1 for k in a)


# ---------------- 1. 8本のレポートの行数（SQL の長さ） ----------------
con = fresh()
base_s, base_w = run(con, "star"), run(con, "wide")
assert n_diff(base_s, base_w) == 0, "はじめは2つの持ち方で同じ答え"
lines = pd.DataFrame([{"レポート": k, "事実とマスタ": len([l for l in q["star"].strip().split("\n") if l.strip()]),
                       "1枚の表": len([l for l in q["wide"].strip().split("\n") if l.strip()]),
                       "つなぐ表の数": len(re.findall(r"\bJOIN\b", q["star"]))} for k, q in REPORTS.items()])
lines.to_csv(RES / "sql_lines.csv", index=False)

# ---------------- 2. 7つの場面 ----------------
MOVE = prod.product_id.iloc[:12].tolist()                 # 部門が変わる12商品
REG_ST = [3, 9, 15]                                       # 地域が変わる3店
D0 = "2025-07-01"
rows = []


def rec(scene, want, star_rows, wide_rows, star_lines, wide_lines, star_wrong, wide_wrong, note):
    rows.append(dict(場面=scene, 求められたこと=want, 直す行_事実とマスタ=star_rows, 直す行_1枚の表=wide_rows,
                     直すSQLの行_事実とマスタ=star_lines, 直すSQLの行_1枚の表=wide_lines,
                     直さないと合わないレポート_事実とマスタ=star_wrong, 直さないと合わないレポート_1枚の表=wide_wrong, メモ=note))


# S1 商品の部門替え：全期間を「今の部門」で見たい
con = fresh()
before_w = run(con, "wide")
con.execute(f"UPDATE product SET dept='雑貨' WHERE product_id IN ({','.join(map(str, MOVE))})")
truth = run(con, "star")                                   # マスタを直せば、全期間が今の部門
wide_rows = con.execute(f"SELECT COUNT(*) FROM sales_wide WHERE product_id IN ({','.join(map(str, MOVE))})").fetchone()[0]
rec("S1 商品の部門替え（12商品）", "全期間を今の部門で", 12, wide_rows, 0, 0, 0, n_diff(before_w, truth),
    "1枚の表は、写してある部門の列を全部書き換える")
# S1b 1枚の表を直したが、毎日の取り込みが古い写しのまま（7/1以降の行に古い部門が入り続けた）
con.execute(f"UPDATE sales_wide SET dept='雑貨' WHERE product_id IN ({','.join(map(str, MOVE))}) AND sale_date < DATE '{D0}'")
part = run(con, "wide")
left = con.execute(f"SELECT COUNT(*) FROM sales_wide w JOIN product p ON p.product_id=w.product_id WHERE w.dept<>p.dept").fetchone()[0]
rec("S1b 過去分だけ直して、取り込みを直し忘れ", "全期間を今の部門で", 0, left, 0, 0, 0, n_diff(part, truth),
    "7/1以降の行に古い部門が入り続ける")

# S2 部門替えのあと：「売れた時点の部門」で見たい
con = fresh()
truth = run(con, "wide")                                   # 写しは売れた時点の値（7/1より前は元の部門）
con.execute(f"UPDATE sales_wide SET dept='雑貨' WHERE product_id IN ({','.join(map(str, MOVE))}) AND sale_date >= DATE '{D0}'")
truth = run(con, "wide")
con.execute(f"UPDATE product SET dept='雑貨' WHERE product_id IN ({','.join(map(str, MOVE))})")
star_now = run(con, "star")
# 事実とマスタでは、期間つきのマスタ（履歴）に変え、部門を使うレポートのつなぎ方を直す
con.execute("""CREATE TABLE product_hist AS
    SELECT product_id, product_name, dept, DATE '1900-01-01' AS valid_from, DATE '9999-12-31' AS valid_to FROM product""")
for pid in MOVE:
    old = prod.loc[prod.product_id == pid, "dept"].iloc[0]
    con.execute(f"UPDATE product_hist SET valid_from=DATE '{D0}' WHERE product_id={pid}")
    con.execute(f"INSERT INTO product_hist SELECT product_id, product_name, '{old}', DATE '1900-01-01', DATE '{D0}' FROM product WHERE product_id={pid}")
hist = {}
for name, q in REPORTS.items():
    sql = q["star"].replace("JOIN product p ON p.product_id=f.product_id",
                            "JOIN product_hist p ON p.product_id=f.product_id AND f.sale_date>=p.valid_from AND f.sale_date<p.valid_to")
    d = con.execute(sql).df(); hist[name] = d.sort_values(list(d.columns)).reset_index(drop=True)
assert n_diff(hist, truth) == 0
n_join = sum(1 for q in REPORTS.values() if "JOIN product p" in q["star"])
rec("S2 売れた時点の部門で見たい", "売れた時点の部門で", 12 + 12, 0, n_join, 0, n_diff(star_now, truth), 0,
    "事実とマスタは、期間つきのマスタに変えて、商品をつなぐレポートを全部直す")

# S3 店の地域の区分替え（3店）：今の地域で全期間
con = fresh(); before_w = run(con, "wide")
for sid in REG_ST: con.execute(f"UPDATE store SET region='中' WHERE store_id={sid}")
truth = run(con, "star")
wide_rows = con.execute(f"SELECT COUNT(*) FROM sales_wide WHERE store_id IN ({','.join(map(str, REG_ST))})").fetchone()[0]
rec("S3 店の地域の区分替え（3店）", "全期間を今の地域で", 3, wide_rows, 0, 0, 0, n_diff(before_w, truth), "")

# S4 商品名の誤字を1件直す
con = fresh(); before_w = run(con, "wide")
con.execute("UPDATE product SET product_name='商品001（改）' WHERE product_id=1")
truth = run(con, "star")
wide_rows = con.execute("SELECT COUNT(*) FROM sales_wide WHERE product_id=1").fetchone()[0]
rec("S4 商品名の誤りを1件直す", "全期間を正しい名前で", 1, wide_rows, 0, 0, 0, n_diff(before_w, truth), "")

# S5 新しい属性（自社ブランドかどうか）を足して、1本のレポートに使う
con = fresh()
rec("S5 商品に新しい属性を足す", "新しい属性で分けたレポートを1本", NP_, N, 0, 0, 0, 0,
    "新しいレポート1本はどちらの持ち方でも書く。事実とマスタは列を足して200行に値を入れる。1枚の表は列を足して30万行に値を入れる")

# S6 マスタにない商品コードの売上が入ってきた（500行）
con = fresh()
orphan = fact.sample(500, random_state=SEED).copy(); orphan["sale_id"] += 10_000_000; orphan["product_id"] = 9999
con.register("o1", orphan)
con.execute("INSERT INTO fact_sales SELECT sale_id, CAST(sale_date AS DATE), store_id, product_id, qty, amount FROM o1")
con.execute("""INSERT INTO sales_wide SELECT o.sale_id, CAST(o.sale_date AS DATE), o.store_id, s.store_name, s.region, o.product_id, NULL, NULL, o.qty, o.amount
               FROM o1 o JOIN store s ON s.store_id=o.store_id""")
star_o, wide_o = run(con, "star"), run(con, "wide")
tot_all = con.execute("SELECT SUM(amount) FROM fact_sales").fetchone()[0]
tot_star = con.execute("SELECT SUM(f.amount) FROM fact_sales f JOIN product p ON p.product_id=f.product_id").fetchone()[0]
# 正解＝500行も数える（部門・商品名は「不明」）。1枚の表は NULL のまま数えるので、合計は合う
rec("S6 マスタにない商品コードの売上（500行）", "500行も落とさずに数える", 1, 0, 0, 0,
    sum(1 for k in REPORTS if "JOIN product p" in REPORTS[k]["star"]), 0,
    f"事実とマスタは、内部結合で500行（売上の{(tot_all-tot_star)/tot_all:.2%}）が黙って消える。1枚の表は部門が空欄の行として残る")
s6_drop = (tot_all - tot_star) / tot_all

# S7 商品マスタに同じ商品が2行入った（5商品）
con = fresh()
con.execute("INSERT INTO product SELECT * FROM product WHERE product_id IN (21,22,23,24,25)")
star_d = run(con, "star")
tot_dup = con.execute("SELECT SUM(f.amount) FROM fact_sales f JOIN product p ON p.product_id=f.product_id").fetchone()[0]
rec("S7 商品マスタに同じ商品が2行（5商品）", "二重に数えない", 5, 0, 0, 0, n_diff(star_d, base_s), 0,
    f"事実とマスタは、つないだ行が増えて売上が+{tot_dup/fact.amount.sum()-1:.2%}。1枚の表は、取り込みのときに増える")
s7_up = tot_dup / fact.amount.sum() - 1

sc = pd.DataFrame(rows); sc.to_csv(RES / "scenes.csv", index=False)

# ---------------- 3. どの列を使うレポートが何本か ----------------
uses = pd.DataFrame([{"レポート": k, **{c: int(c in v) for c in ["dept", "product_name", "region", "store_name"]}} for k, v in USES.items()])
uses.to_csv(RES / "report_uses.csv", index=False)

# ---------------- 4. 時間（参考） ----------------
import time
con = fresh(); tm = {}
for form in ["star", "wide"]:
    t0 = time.perf_counter()
    for _ in range(5): run(con, form)
    tm[form] = (time.perf_counter() - t0) / 5

main = {"行数": {"事実": N, "商品": NP_, "店": NS},
        "SQLの行数_8本の合計": {"事実とマスタ": int(lines["事実とマスタ"].sum()), "1枚の表": int(lines["1枚の表"].sum())},
        "S6_黙って消えた売上の割合": round(s6_drop, 5), "S7_増えた売上の割合": round(s7_up, 5),
        "場面": sc.drop(columns="メモ").to_dict("records")}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
json.dump({"8本を1回流す秒数（参考、実行ごとに変わる）": {k: round(v, 3) for k, v in tm.items()}},
          open(RES / "timing_varies_each_run.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(len(lines)); w = .38
ax.bar(x - w / 2, lines["事実とマスタ"], w, color=BLUE, label=f"事実とマスタ（合計{lines['事実とマスタ'].sum()}行）")
ax.bar(x + w / 2, lines["1枚の表"], w, color=ORANGE, label=f"1枚の大きな表（合計{lines['1枚の表'].sum()}行）")
ax.set_xticks(x); ax.set_xticklabels(lines["レポート"], rotation=20, ha="right", fontsize=9)
ax.set_ylabel("SQL の行数"); ax.set_title("同じ8本のレポートの SQL の行数"); ax.legend(frameon=False)
save(fig, "a401_sql_lines.png", SRC, y=-0.08)

fig, ax = plt.subplots(figsize=(8.4, 4.6)); d = sc.iloc[[0, 3, 4, 5, 2]].reset_index(drop=True)   # S1,S3,S4,S5,S2
y = np.arange(len(d)); h = .38
a = d["直す行_事実とマスタ"].clip(lower=0.8); b = d["直す行_1枚の表"].clip(lower=0.8)
ax.barh(y + h / 2, a, h, color=BLUE, label="事実とマスタ"); ax.barh(y - h / 2, b, h, color=ORANGE, label="1枚の大きな表")
for i in range(len(d)):
    ax.text(a[i] * 1.15, i + h / 2, f"{d['直す行_事実とマスタ'][i]:,}行", va="center", fontsize=9)
    ax.text(b[i] * 1.15, i - h / 2, f"{d['直す行_1枚の表'][i]:,}行", va="center", fontsize=9)
ax.set_xscale("log"); ax.set_xlim(0.7, 5e6); ax.set_yticks(y); ax.set_yticklabels([s.split("（")[0] for s in d["場面"]], fontsize=9); ax.invert_yaxis()
ax.set_xlabel("書き換える行の数（対数の目盛り）"); ax.set_title("マスタが変わったとき、表のデータを何行書き換えるか"); ax.legend(frameon=False, loc="lower right")
save(fig, "a401_rows_to_update.png", SRC + "。0行は目盛りの左端に置いた")

fig, ax = plt.subplots(figsize=(8.4, 4.6)); d = sc.copy(); y = np.arange(len(d))
ax.barh(y + h / 2, d["直さないと合わないレポート_事実とマスタ"], h, color=BLUE, label="事実とマスタ")
ax.barh(y - h / 2, d["直さないと合わないレポート_1枚の表"], h, color=ORANGE, label="1枚の大きな表")
for i in range(len(d)):
    ax.text(d["直さないと合わないレポート_事実とマスタ"][i] + .1, i + h / 2, str(d["直さないと合わないレポート_事実とマスタ"][i]), va="center", fontsize=9)
    ax.text(d["直さないと合わないレポート_1枚の表"][i] + .1, i - h / 2, str(d["直さないと合わないレポート_1枚の表"][i]), va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([s.split("（")[0] for s in d["場面"]], fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 9)
ax.set_xlabel("8本のうち、答えが合わなくなるレポートの本数"); ax.set_title("何もしないと、8本のうち何本の答えが合わなくなるか"); ax.legend(frameon=False, loc="lower right")
save(fig, "a401_reports_wrong.png", SRC)
print(lines.to_string()); print(sc.drop(columns=["メモ"]).to_string()); print(main["SQLの行数_8本の合計"], s6_drop, s7_up, tm)
