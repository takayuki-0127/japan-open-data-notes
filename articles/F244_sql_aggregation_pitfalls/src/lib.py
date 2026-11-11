"""F244 共通部品：データの生成・DB への読み込み・集計 SQL（誤り版／正しい版）・pandas の正解・テスト。

- 公開データ：経済産業省「商業動態統計」（F232 で取得したもの）と内閣府「国民の祝日」（F233 で作成したもの）
- シミュレーション：架空のネット書店「あおば書店（架空）」の注文データ（実在の会社ではない）
- SQL は DuckDB と SQLite の両方で実行する。SQL Server 版は sql/ に置く（SQL Server では実行していない）
"""
import os, sqlite3
import numpy as np
import pandas as pd
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# ---------------------------------------------------------------- 公開データ
def load_retail():
    d = pd.read_csv(os.path.join(RAW, "retail_national_2014_2026.csv"))
    d = d.rename(columns={"業態": "gyotai", "品目": "item", "値": "sales"})[["ym", "gyotai", "item", "sales"]]
    d["sales"] = d["sales"].round().astype("int64")          # 百万円の整数として DB に入れる
    nodes = pd.read_csv(os.path.join(RAW, "f232_nodes.csv"))
    leaf = set(nodes.loc[nodes["階層"] == 3, "ノード"])
    tot_name = {"百貨店": "合計", "スーパー": "合計", "コンビニ": "合計"}
    dim = d[["gyotai", "item"]].drop_duplicates().copy()
    dim["is_leaf"] = [int(f"{g}/{i}" in leaf) for g, i in zip(dim.gyotai, dim.item)]
    dim["is_total"] = [int(i == tot_name.get(g, "商品販売額")) for g, i in zip(dim.gyotai, dim.item)]
    hol = pd.read_csv(os.path.join(RAW, "holidays_jp.csv"))
    hol = hol[(hol.date >= "2014-01-01") & (hol.date <= "2026-12-31")].reset_index(drop=True)
    return d, dim, hol

# ---------------------------------------------------------------- シミュレーション
def simulate(seed=1, n_cust=8000, lam=150, p_split=0.12, p_ship2=0.08, p_coupon=0.30,
             p_return=0.04, p_cancel=0.04, p_ref=0.30, outage=("2025-03-15", "2025-03-16", "2025-07-08", "2025-11-20"),
             force_edges=False, year=2025):
    """あおば書店（架空）の1年分の注文。時刻は UTC の文字列で持つ（日本時間 = UTC + 9 時間）。"""
    rng = np.random.default_rng(seed)
    cust = pd.DataFrame({"customer_id": np.arange(1, n_cust + 1)})
    has_ref = rng.random(n_cust) < p_ref
    cust["referrer_id"] = np.where(has_ref, rng.integers(1, n_cust + 1, n_cust), -1)
    cust.loc[cust.referrer_id == cust.customer_id, "referrer_id"] = -1
    cust["referrer_id"] = cust["referrer_id"].astype("Int64").where(cust["referrer_id"] > 0)   # 紹介なしは NULL
    days = pd.date_range(f"{year}-01-01", f"{year}-12-31", freq="D")
    dow_f = np.array([1.0, 0.95, 0.95, 1.0, 1.1, 1.3, 1.25])
    rows = []
    oid = 0
    hours = np.arange(24); hw = np.exp(-0.5 * ((hours - 21) / 3.5) ** 2) + 0.15; hw /= hw.sum()
    for d in days:
        ds = d.strftime("%Y-%m-%d")
        if ds in outage:
            continue                      # システム停止で注文が1件もない日（日付の行が欠ける）
        n = rng.poisson(lam * dow_f[d.dayofweek] * (1.25 if d.month == 12 else 1.0))
        hh = rng.choice(24, n, p=hw); mm = rng.integers(0, 60, n); ss = rng.integers(0, 60, n)
        for h, m, s in zip(hh, mm, ss):
            oid += 1
            jst = d + pd.Timedelta(hours=int(h), minutes=int(m), seconds=int(s))
            rows.append((oid, int(rng.integers(1, n_cust + 1)), jst))
    if force_edges:   # 答え合わせ用の小さなデータには、境界の注文を必ず入れる
        for jst in [f"{year}-01-01 03:10:00", f"{year}-01-31 23:50:00", f"{year}-12-31 23:30:00", f"{year}-06-30 08:59:59"]:
            oid += 1; rows.append((oid, 1, pd.Timestamp(jst)))
    o = pd.DataFrame(rows, columns=["order_id", "customer_id", "jst"])
    o["ts_utc"] = (o["jst"] - pd.Timedelta(hours=9)).dt.strftime("%Y-%m-%d %H:%M:%S")
    o["status"] = np.where(rng.random(len(o)) < p_cancel, "cancelled", "paid")
    o["discount_yen"] = pd.array(np.where(rng.random(len(o)) < p_coupon, rng.integers(1, 9, len(o)) * 100, -1), dtype="Int64")
    o.loc[o.discount_yen < 0, "discount_yen"] = pd.NA     # クーポンなしは NULL（0 ではない）
    # 明細
    nl = rng.integers(1, 5, len(o))
    it = pd.DataFrame({"order_id": np.repeat(o.order_id.values, nl)})
    it["line_no"] = it.groupby("order_id").cumcount() + 1
    it["qty"] = rng.integers(1, 4, len(it))
    it["unit_price"] = rng.integers(5, 41, len(it)) * 100
    if force_edges:
        it.loc[it.order_id == oid, "qty"] = 1
    gross = (it.qty * it.unit_price).groupby(it.order_id).sum()
    o["gross"] = o.order_id.map(gross)
    o.loc[o.discount_yen.notna() & (o.discount_yen > o.gross), "discount_yen"] = 0
    net = o.gross - o.discount_yen.fillna(0).astype(int)
    # 支払い（ポイント＋カードの2回に分かれる注文がある）
    split = rng.random(len(o)) < p_split
    if force_edges: split[:3] = True
    pay = []
    for i, (k, v, sp) in enumerate(zip(o.order_id, net, split)):
        if sp and v > 100:
            a = int(rng.integers(1, max(2, v // 100)) * 100) if v >= 200 else 100
            a = min(a, int(v) - 1)
            pay += [(k, 1, a), (k, 2, int(v) - a)]
        else:
            pay.append((k, 1, int(v)))
    pay = pd.DataFrame(pay, columns=["order_id", "payment_no", "amount"])
    # 発送（2回に分かれる注文がある）
    s2 = rng.random(len(o)) < p_ship2
    if force_edges: s2[:2] = True
    ship = pd.DataFrame({"order_id": np.repeat(o.order_id.values, np.where(s2, 2, 1))})
    ship["ship_no"] = ship.groupby("order_id").cumcount() + 1
    # 返品（明細単位）
    rt = it[rng.random(len(it)) < p_return].copy()
    if force_edges and len(rt) == 0:
        rt = it.head(2).copy()
    rt["ret_qty"] = [int(rng.integers(1, q + 1)) for q in rt.qty]
    rt = rt[["order_id", "line_no", "ret_qty"]]
    # 訪問（セッション数、整数）
    allday = pd.DataFrame({"d": days.strftime("%Y-%m-%d")})
    cnt = o.assign(d=o.jst.dt.strftime("%Y-%m-%d")).groupby("d").size()
    allday["orders_expected"] = allday.d.map(cnt).fillna(0)
    allday["sessions"] = (allday.orders_expected / rng.uniform(0.025, 0.035, len(allday))).round().astype(int)
    allday.loc[allday.sessions == 0, "sessions"] = rng.integers(500, 900, (allday.sessions == 0).sum())
    sess = allday[["d", "sessions"]]
    orders = o[["order_id", "customer_id", "ts_utc", "status", "discount_yen"]]
    dates = pd.DataFrame({"d": days.strftime("%Y-%m-%d")})
    return dict(customers=cust, orders=orders, order_items=it, payments=pay, shipments=ship,
                returns=rt, sessions=sess, dates=dates)

# ---------------------------------------------------------------- DB
def make_dbs(tables):
    """同じ表を DuckDB と SQLite に入れる。NULL はそのまま NULL として入れる。"""
    dk = duckdb.connect(":memory:")
    sq = sqlite3.connect(":memory:")
    for name, df in tables.items():
        df2 = df.copy()
        for c in df2.columns:
            if str(df2[c].dtype) == "Int64":
                df2[c] = df2[c].astype(object).where(df2[c].notna(), None)
        dk.register("tmp_df", df2); dk.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df"); dk.unregister("tmp_df")
        cols = list(df2.columns)
        types = []
        for c in cols:
            s = df[c]
            types.append("INTEGER" if (pd.api.types.is_integer_dtype(s) or str(s.dtype) == "Int64") else ("REAL" if pd.api.types.is_float_dtype(s) else "TEXT"))
        sq.execute(f"CREATE TABLE {name} ({', '.join(f'{c} {t}' for c, t in zip(cols, types))})")
        vals = [tuple(None if (isinstance(v, float) and np.isnan(v)) else (int(v) if isinstance(v, (np.integer,)) else v) for v in r) for r in df2.itertuples(index=False)]
        sq.executemany(f"INSERT INTO {name} VALUES ({','.join('?' * len(cols))})", vals)
    # DuckDB では整数の列を整数型にそろえる（SQLite と同じ条件にする）
    for name, df in tables.items():
        for c in df.columns:
            if str(df[c].dtype) == "Int64" or pd.api.types.is_integer_dtype(df[c]):
                try: dk.execute(f"ALTER TABLE {name} ALTER {c} TYPE BIGINT")
                except Exception: pass
    return {"duckdb": dk, "sqlite": sq}

MACRO = {
    "duckdb": {"JST": "strftime(CAST({x} AS TIMESTAMP) + INTERVAL 9 HOUR, '%Y-%m-%d %H:%M:%S')", "FLOAT": "CAST({x} AS DOUBLE)", "DAYS": "date_diff('day', DATE '2025-01-01', CAST({x} AS DATE))"},
    "sqlite": {"JST": "datetime({x}, '+9 hours')", "FLOAT": "CAST({x} AS REAL)", "DAYS": "CAST(julianday({x}) - julianday('2025-01-01') AS INTEGER)"},
}

def render(sql, eng):
    import re
    m = MACRO[eng]
    for k, tmpl in m.items():
        sql = re.sub(k + r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)", lambda mm: tmpl.format(x=mm.group(1)), sql)
    return sql

def run(dbs, sql, eng):
    q = render(sql, eng)
    if eng == "duckdb":
        df = dbs["duckdb"].execute(q).df()
    else:
        df = pd.read_sql_query(q, dbs["sqlite"])
    df.columns = ["k", "v"]
    df["k"] = df["k"].astype(str)
    return df

# ---------------------------------------------------------------- 集計 SQL（誤り版と正しい版）
J_M = "substr(JST(o.ts_utc),1,7)"
SPECS = []
def spec(id, part, cat, title, bad, good, kind="sum", truth=None, note=""):
    SPECS.append(dict(id=id, part=part, cat=cat, title=title, bad=bad, good=good, kind=kind, truth=truth, note=note))

# ---- A 公開データ（商業動態統計を DB に入れる）
spec("A1", "公開", "粒度・二重計上", "2025年の業態別販売額（品目の合計行・中分類まで足す）",
     "SELECT gyotai, SUM(sales) FROM retail WHERE ym LIKE '2025-%' GROUP BY gyotai",
     "SELECT r.gyotai, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_leaf=1 AND r.ym LIKE '2025-%' GROUP BY r.gyotai")
spec("A2", "公開", "粒度・二重計上", "家電大型専門店の月次販売額（2021年からの細かい分類も足す）",
     "SELECT ym, SUM(sales) FROM retail WHERE gyotai='家電大型専門店' AND item<>'商品販売額' GROUP BY ym",
     "SELECT r.ym, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_leaf=1 AND r.gyotai='家電大型専門店' GROUP BY r.ym")
spec("A3", "公開", "JOIN の行の増え方", "月次のスーパー販売額に祝日の数を付ける（祝日の表をそのまま JOIN）",
     "SELECT r.ym, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item LEFT JOIN holidays h ON substr(h.date,1,7)=r.ym WHERE d.is_total=1 AND r.gyotai='スーパー' GROUP BY r.ym",
     "SELECT r.ym, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item LEFT JOIN (SELECT substr(date,1,7) AS ym, COUNT(*) AS n_hol FROM holidays GROUP BY substr(date,1,7)) h ON h.ym=r.ym WHERE d.is_total=1 AND r.gyotai='スーパー' GROUP BY r.ym")
spec("A4", "公開", "整数の割り算", "スーパーの前年同月比（%）",
     "SELECT ym, (s - s12) * 100 / s12 FROM (SELECT r.ym, r.sales AS s, LAG(r.sales,12) OVER (ORDER BY r.ym) AS s12 FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='スーパー') t WHERE s12 IS NOT NULL",
     "SELECT ym, FLOAT(s - s12) * 100 / s12 FROM (SELECT r.ym, r.sales AS s, LAG(r.sales,12) OVER (ORDER BY r.ym) AS s12 FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='スーパー') t WHERE s12 IS NOT NULL",
     kind="pct")
spec("A5", "公開", "期間の境目", "2024年度（2024年4月〜2025年3月）の業態別販売額",
     "SELECT r.gyotai, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND substr(r.ym,1,4)='2024' GROUP BY r.gyotai",
     "SELECT r.gyotai, SUM(r.sales) FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.ym >= '2024-04' AND r.ym <= '2025-03' GROUP BY r.gyotai")
spec("A6", "公開", "ウィンドウ関数", "コンビニの直近12か月の合計（12か月そろわない月も出す）",
     "SELECT ym, SUM(s) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) FROM (SELECT r.ym, r.sales AS s FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='コンビニ') t",
     "SELECT ym, s12 FROM (SELECT ym, SUM(s) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS s12, COUNT(*) OVER (ORDER BY ym ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS n FROM (SELECT r.ym, r.sales AS s FROM retail r JOIN item_dim d ON r.gyotai=d.gyotai AND r.item=d.item WHERE d.is_total=1 AND r.gyotai='コンビニ') t) u WHERE n = 12")

# ---- B 架空のネット書店（注文データ）
GROSS_M = f"SELECT {J_M}, SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id {{J}} WHERE o.status='paid' GROUP BY {J_M}"
spec("B1", "架空", "JOIN の行の増え方", "月次の売上（支払いの表を JOIN してから明細を足す）",
     GROSS_M.format(J="JOIN payments p ON p.order_id=o.order_id"), GROSS_M.format(J=""))
spec("B2", "架空", "JOIN の行の増え方", "月次の売上（支払いと発送の両方を JOIN）",
     GROSS_M.format(J="JOIN payments p ON p.order_id=o.order_id JOIN shipments s ON s.order_id=o.order_id"), GROSS_M.format(J=""))
spec("B3", "架空", "NULL", "月次の値引き後の売上（クーポンなしの値引きは NULL）",
     f"SELECT m, SUM(g - discount_yen) FROM (SELECT {J_M} AS m, o.order_id, MAX(o.discount_yen) AS discount_yen, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY {J_M}, o.order_id) t GROUP BY m",
     f"SELECT m, SUM(g - COALESCE(discount_yen,0)) FROM (SELECT {J_M} AS m, o.order_id, MAX(o.discount_yen) AS discount_yen, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY {J_M}, o.order_id) t GROUP BY m")
spec("B4", "架空", "NULL", "月次の1注文あたり平均値引き額（全注文で割る）",
     f"SELECT {J_M}, AVG(discount_yen) FROM orders o WHERE o.status='paid' GROUP BY {J_M}",
     f"SELECT {J_M}, AVG(FLOAT(COALESCE(discount_yen,0))) FROM orders o WHERE o.status='paid' GROUP BY {J_M}", kind="mean")
spec("B5", "架空", "NULL", "だれも紹介していない顧客の数（NOT IN と NULL）",
     "SELECT 'all', COUNT(*) FROM customers c WHERE c.customer_id NOT IN (SELECT referrer_id FROM customers)",
     "SELECT 'all', COUNT(*) FROM customers c WHERE NOT EXISTS (SELECT 1 FROM customers x WHERE x.referrer_id = c.customer_id)", kind="count")
spec("B6", "架空", "数え方（DISTINCT）", "月次の購入した顧客の数（日ごとの人数を足す）",
     f"SELECT m, SUM(n) FROM (SELECT substr(JST(o.ts_utc),1,7) AS m, substr(JST(o.ts_utc),1,10) AS d, COUNT(DISTINCT o.customer_id) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,7), substr(JST(o.ts_utc),1,10)) t GROUP BY m",
     f"SELECT {J_M}, COUNT(DISTINCT o.customer_id) FROM orders o WHERE o.status='paid' GROUP BY {J_M}", kind="count")
spec("B7", "架空", "数え方（DISTINCT）", "月次の購入した顧客の数（明細を JOIN して COUNT(*)）",
     f"SELECT {J_M}, COUNT(*) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY {J_M}",
     f"SELECT {J_M}, COUNT(DISTINCT o.customer_id) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY {J_M}", kind="count")
spec("B8", "架空", "日付・時間帯", "月次の売上（UTC のまま月に分ける）",
     "SELECT substr(o.ts_utc,1,7), SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(o.ts_utc,1,7)",
     GROSS_M.format(J=""))
spec("B9", "架空", "日付・時間帯", "12月の売上（BETWEEN '12-01' AND '12-31' で時刻つきの列を絞る）",
     "SELECT 'dec', SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' AND JST(o.ts_utc) BETWEEN '2025-12-01' AND '2025-12-31'",
     "SELECT 'dec', SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' AND JST(o.ts_utc) >= '2025-12-01' AND JST(o.ts_utc) < '2026-01-01'")
spec("B10", "架空", "ウィンドウ関数", "顧客ごとの最後の注文日（LAST_VALUE の既定の範囲）",
     "SELECT customer_id, DAYS(lastd) FROM (SELECT DISTINCT o.customer_id, substr(LAST_VALUE(JST(o.ts_utc)) OVER (PARTITION BY o.customer_id ORDER BY o.ts_utc),1,10) AS lastd FROM orders o WHERE o.status='paid') t",
     "SELECT customer_id, DAYS(lastd) FROM (SELECT DISTINCT o.customer_id, substr(LAST_VALUE(JST(o.ts_utc)) OVER (PARTITION BY o.customer_id ORDER BY o.ts_utc ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING),1,10) AS lastd FROM orders o WHERE o.status='paid') t",
     kind="level")
spec("B11", "架空", "ウィンドウ関数", "日次売上の7日移動平均（注文のない日は行がない）",
     "SELECT d, AVG(g) OVER (ORDER BY d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) FROM (SELECT substr(JST(o.ts_utc),1,10) AS d, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,10)) t",
     "SELECT d, ma FROM (SELECT c.d, AVG(FLOAT(COALESCE(t.g,0))) OVER (ORDER BY c.d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma, COUNT(*) OVER (ORDER BY c.d ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS n FROM dates c LEFT JOIN (SELECT substr(JST(o.ts_utc),1,10) AS d, SUM(i.qty*i.unit_price) AS g FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,10)) t ON t.d=c.d) u WHERE n = 7",
     kind="level")
spec("B12", "架空", "整数の割り算", "日次の購入率（注文数 ÷ 訪問数）",
     "SELECT s.d, COALESCE(n,0) / s.sessions FROM sessions s LEFT JOIN (SELECT substr(JST(o.ts_utc),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,10)) t ON t.d=s.d",
     "SELECT s.d, FLOAT(COALESCE(n,0)) / s.sessions FROM sessions s LEFT JOIN (SELECT substr(JST(o.ts_utc),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,10)) t ON t.d=s.d",
     kind="rate")
spec("B13", "架空", "定義のずれ", "月次の購入率（日ごとの率の平均）",
     "SELECT substr(s.d,1,7), AVG(FLOAT(COALESCE(n,0)) / s.sessions) FROM sessions s LEFT JOIN (SELECT substr(JST(o.ts_utc),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,10)) t ON t.d=s.d GROUP BY substr(s.d,1,7)",
     "SELECT substr(s.d,1,7), SUM(FLOAT(COALESCE(n,0))) / SUM(s.sessions) FROM sessions s LEFT JOIN (SELECT substr(JST(o.ts_utc),1,10) AS d, COUNT(*) AS n FROM orders o WHERE o.status='paid' GROUP BY substr(JST(o.ts_utc),1,10)) t ON t.d=s.d GROUP BY substr(s.d,1,7)",
     kind="rate")
spec("B14", "架空", "JOIN の行の増え方", "月次の返品額（返品を注文番号だけで JOIN）",
     f"SELECT {J_M}, SUM(r.ret_qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id JOIN returns r ON r.order_id=i.order_id WHERE o.status='paid' GROUP BY {J_M}",
     f"SELECT {J_M}, SUM(r.ret_qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id JOIN returns r ON r.order_id=i.order_id AND r.line_no=i.line_no WHERE o.status='paid' GROUP BY {J_M}")
spec("B15", "架空", "絞り込みの漏れ", "月次の売上（キャンセルを除き忘れ）",
     f"SELECT {J_M}, SUM(i.qty*i.unit_price) FROM orders o JOIN order_items i ON i.order_id=o.order_id GROUP BY {J_M}",
     GROSS_M.format(J=""))

# ---------------------------------------------------------------- pandas の正解（SQL とは別の書き方で計算する）
def truths_public(retail, dim, hol):
    r = retail.merge(dim, on=["gyotai", "item"])
    leaf = r[r.is_leaf == 1]; tot = r[r.is_total == 1]
    T = {}
    x = leaf[leaf.ym.str.startswith("2025-")].groupby("gyotai").sales.sum(); T["A1"] = x
    x = leaf[leaf.gyotai == "家電大型専門店"].groupby("ym").sales.sum(); T["A2"] = x
    sup = tot[tot.gyotai == "スーパー"].set_index("ym").sales.sort_index()
    T["A3"] = sup
    yoy = ((sup - sup.shift(12)) * 100 / sup.shift(12)).dropna(); T["A4"] = yoy
    T["A5"] = tot[(tot.ym >= "2024-04") & (tot.ym <= "2025-03")].groupby("gyotai").sales.sum()
    cvs = tot[tot.gyotai == "コンビニ"].set_index("ym").sales.sort_index()
    T["A6"] = cvs.rolling(12).sum().dropna()
    # 照合に使う「公表の合計行」
    C = {"A1": tot[tot.ym.str.startswith("2025-")].groupby("gyotai").sales.sum().sum(),
         "A2": tot[tot.gyotai == "家電大型専門店"].sales.sum(),
         "A3": tot[tot.gyotai == "スーパー"].sales.sum(),
         "A5": tot[(tot.ym >= "2024-04") & (tot.ym <= "2025-03")].sales.sum()}
    return T, C

def truths_sim(t):
    o = t["orders"].copy(); it = t["order_items"]
    o["jst"] = pd.to_datetime(o.ts_utc) + pd.Timedelta(hours=9)
    o["m"] = o.jst.dt.strftime("%Y-%m"); o["d"] = o.jst.dt.strftime("%Y-%m-%d")
    paid = o[o.status == "paid"]
    li = it.merge(paid[["order_id", "m", "d"]], on="order_id")
    li["amt"] = li.qty * li.unit_price
    T = {}
    gm = li.groupby("m").amt.sum()
    T["B1"] = T["B2"] = T["B8"] = T["B15"] = gm
    g_o = li.groupby("order_id").amt.sum()
    pp = paid.set_index("order_id")
    net = g_o - pp.loc[g_o.index, "discount_yen"].fillna(0).astype(float)
    T["B3"] = net.groupby(pp.loc[g_o.index, "m"]).sum()
    T["B4"] = paid.assign(dd=paid.discount_yen.fillna(0).astype(float)).groupby("m").dd.mean()
    c = t["customers"]; refs = set(c.referrer_id.dropna().astype(int))
    T["B5"] = pd.Series({"all": int((~c.customer_id.isin(refs)).sum())})
    T["B6"] = T["B7"] = paid.groupby("m").customer_id.nunique()
    T["B9"] = pd.Series({"dec": li[li.d >= "2025-12-01"].amt.sum()})
    last = paid.groupby("customer_id").jst.max().dt.normalize()
    T["B10"] = ((last - pd.Timestamp("2025-01-01")).dt.days).rename(index=str)
    daily = li.groupby("d").amt.sum()
    dd = t["dates"].d
    s = daily.reindex(dd).fillna(0); s.index = dd.values
    T["B11"] = s.rolling(7).mean().dropna()
    n_d = paid.groupby("d").size()
    se = t["sessions"].set_index("d").sessions
    T["B12"] = (n_d.reindex(se.index).fillna(0) / se)
    mm = se.index.str[:7]
    T["B13"] = n_d.reindex(se.index).fillna(0).groupby(mm).sum() / se.groupby(mm).sum()
    rt = t["returns"].merge(it[["order_id", "line_no", "unit_price"]], on=["order_id", "line_no"]).merge(paid[["order_id", "m"]], on="order_id")
    T["B14"] = (rt.ret_qty * rt.unit_price).groupby(rt.m).sum()
    C = {k: T[k].sum() for k in ["B1", "B2", "B3", "B8", "B9", "B14", "B15"]}
    C["B1src"] = li.amt.sum()
    return T, C

# ---------------------------------------------------------------- テスト
TESTS = ["T1 照合", "T2 粒度（キーの重複）", "T3 NULL", "T4 期間・キーの網羅", "T5 小さなデータで答え合わせ", "T6 値の範囲・型", "T7 エンジン間の一致"]
ADDITIVE = {"A1": 1e-4, "A2": 1e-4, "A3": 1e-9, "A5": 1e-9, "B1": 1e-9, "B2": 1e-9, "B3": 1e-9, "B8": 1e-9, "B9": 1e-9, "B14": 1e-9, "B15": 1e-9}

def _eq(df, truth, tol=1e-9):
    if len(df) != len(truth) or df.k.duplicated().any():
        return False
    a = df.set_index("k").v.astype(float)
    b = truth.copy(); b.index = b.index.astype(str); b = b.astype(float)
    if set(a.index) != set(b.index):
        return False
    a = a.reindex(b.index)
    if a.isna().any():
        return False
    return bool(np.allclose(a.values, b.values, rtol=tol, atol=1e-9))

def run_tests(sp, out, out_other, out_fix, truth, truth_fix, control):
    """out：本番データでの結果（DuckDB）、out_other：同じ SQL の SQLite の結果、out_fix：小さなデータでの結果。True＝テストが失敗＝バグを見つけた"""
    res = {}
    k = sp["id"]
    if k in ADDITIVE and k in control:
        tot = out.v.astype(float).sum()
        res[TESTS[0]] = not np.isclose(tot, float(control[k]), rtol=ADDITIVE[k], atol=0.5)
    else:
        res[TESTS[0]] = None   # 足し上げできない指標（率・人数・平均）には照合を使わない
    res[TESTS[1]] = bool(out.k.duplicated().any())
    res[TESTS[2]] = bool(out.v.isna().any())
    tk = set(truth.index.astype(str))
    res[TESTS[3]] = set(out.k) != tk
    res[TESTS[4]] = not _eq(out_fix, truth_fix, 1e-9 if k not in ("A1", "A2") else 1e-9)
    v = out.v.astype(float)
    if sp["kind"] == "rate":
        bad = (v < 0).any() or (v > 1).any() or bool(np.all(np.isclose(v, np.round(v))))
    elif sp["kind"] == "pct":
        bad = bool(np.all(np.isclose(v, np.round(v)))) or (v.abs() > 100).any()
    else:
        bad = bool((v < 0).any())
    res[TESTS[5]] = bool(bad)
    try:
        a = out.assign(v=out.v.astype(float)).sort_values(["k", "v"]).reset_index(drop=True); b = out_other.assign(v=out_other.v.astype(float)).sort_values(["k", "v"]).reset_index(drop=True)
        same = len(a) == len(b) and (a.k.values == b.k.values).all() and np.allclose(a.v.astype(float).fillna(-9e18), b.v.astype(float).fillna(-9e18), rtol=1e-9)
    except Exception:
        same = False
    res[TESTS[6]] = not bool(same)
    return res

# 答え合わせ用の小さなデータ（境目のケースを必ず含める）
FIXTURE_EDGE = dict(seed=99, n_cust=40, lam=2, p_split=0.5, p_ship2=0.5, p_coupon=0.5, p_return=0.3,
                    p_cancel=0.2, p_ref=0.5, outage=("2025-03-15", "2025-07-08"), force_edges=True)
# 比較用：境目のケースを含まない小さなデータ（分割払いなし・クーポン全員あり・返品なし・紹介 NULL なし・停止日なし）
FIXTURE_PLAIN = dict(seed=98, n_cust=40, lam=2, p_split=0.0, p_ship2=0.0, p_coupon=1.0, p_return=0.0,
                     p_cancel=0.0, p_ref=1.0, outage=(), force_edges=False)

def retail_fixture(retail):
    """公開データ側の答え合わせ用：3業態・2020〜2025年だけを切り出す"""
    return retail[retail.gyotai.isin(["スーパー", "コンビニ", "家電大型専門店"]) & (retail.ym >= "2020-01") & (retail.ym <= "2025-12")].reset_index(drop=True)
