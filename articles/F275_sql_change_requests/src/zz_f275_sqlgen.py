"""F275: 3つの書き方（S1 コピペ型・S2 CTE 型・S3 共通ビュー型）で、8本のレポートの SQL を作る。
定義（P）を変えると、変更依頼を当てた後の SQL になる。SQL は SQL Server・DuckDB・SQLite で同じものが動く書き方にする
（日付関数を使わず、月はカレンダー表から引く。整数の割り算をしない。文字列の連結を使わない）。
"""
BASE = dict(st="cancel", tax=False, ret="return", gap=13, mon="cal", test=False, grp="old", cust="receipt")
CRS = {
    "CR1": ("返品を元の売上日に計上", dict(ret="sale")),
    "CR2": ("既存店を12か月以上に", dict(gap=12)),
    "CR3": ("月を21日締めの会計月に", dict(mon="fis")),
    "CR4": ("税込み→税抜き", dict(tax=True)),
    "CR5": ("テスト店を除外", dict(test=True)),
    "CR6": ("除外に void を追加", dict(st="void")),
    "CR7": ("部門のまとめ方の変更", dict(grp="new")),
    "CR8": ("客数を会員の延べ人数に", dict(cust="member")),
}
REPORTS = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]
VIEW_ORDER = ["line_ok", "net", "mon", "comp_store", "dept_grp", "cust"]


def apply(cr):
    p = dict(BASE)
    if cr:
        p.update(CRS[cr][1])
    return p


# ---------- 定義の部品 ----------
def st(P, a):
    return f"{a}.status <> 'cancel'" if P["st"] == "cancel" else f"{a}.status NOT IN ('cancel', 'void')"


def ym(P):
    return ("cal_ym", "cal_mi") if P["mon"] == "cal" else ("fis_ym", "fis_mi")


def grp_case(P, col, ind):
    sp = " " * ind
    if P["grp"] == "old":
        w = [("1, 2", "生鮮"), ("3, 4", "加工食品"), ("5", "日配"), ("6, 7", "日用品")]
    else:
        w = [("1, 2, 5", "生鮮・日配"), ("3, 4", "加工食品"), ("6, 7, 8", "日用品")]
    s = f"CASE\n"
    for k, v in w:
        s += f"{sp}  WHEN {col} IN ({k}) THEN '{v}'\n"
    s += f"{sp}  ELSE 'その他'\n{sp}END"
    return s


def cust_key(P, a):
    if P["cust"] == "receipt":
        return f"{a}.receipt_id"
    return (f"CASE WHEN {a}.member_id IS NULL THEN -{a}.receipt_id\n"
            f"       ELSE CAST({a}.member_id AS BIGINT) * 100000000 + {a}.date_key END")


# ---------- S2・S3 で共有する「定義のかたまり」（S3 ではビュー、S2 では各ファイルの CTE） ----------
def view_body(P, name):
    if name == "line_ok":
        fac = "1.0" if not P["tax"] else "100.0 / (100 + l.tax_pct)"
        j = "\n  JOIN store s ON s.store_id = l.store_id" if P["test"] else ""
        c = "\n    AND s.is_test = 0" if P["test"] else ""
        return (f"  SELECT l.receipt_id, l.line_no, l.date_key, l.store_id, l.item_id, l.amount_incl,\n"
                f"         {fac} AS amt_factor\n"
                f"  FROM sales_line l{j}\n"
                f"  WHERE {st(P, 'l')}{c}")
    if name == "net":
        rd = "r.return_date_key" if P["ret"] == "return" else "o.date_key"
        return ("  SELECT o.date_key AS d, o.store_id, o.item_id, o.amount_incl * o.amt_factor AS amt\n"
                "  FROM line_ok o\n"
                "  UNION ALL\n"
                f"  SELECT {rd} AS d, o.store_id, o.item_id, -r.amount_incl * o.amt_factor AS amt\n"
                "  FROM returns_line r\n"
                "  JOIN line_ok o ON o.receipt_id = r.receipt_id AND o.line_no = r.line_no")
    if name == "mon":
        y, m = ym(P)
        return f"  SELECT c.date_key, c.{y} AS ym, c.{m} AS mi\n  FROM calendar c"
    if name == "comp_store":
        return ("  SELECT s.store_id, m.mi\n"
                "  FROM store s\n"
                "  JOIN mon om ON om.date_key = s.open_date_key\n"
                "  CROSS JOIN (SELECT DISTINCT mi FROM mon) m\n"
                f"  WHERE om.mi <= m.mi - {P['gap']}")
    if name == "dept_grp":
        return f"  SELECT d.dept_id,\n         {grp_case(P, 'd.dept_id', 9)} AS grp\n  FROM dept d"
    if name == "cust":
        return (f"  SELECT r.date_key, r.store_id,\n         {cust_key(P, 'r').replace(chr(10), chr(10) + '         ')} AS cust_key\n"
                "  FROM receipt r\n"
                "  WHERE EXISTS (SELECT 1 FROM line_ok o WHERE o.receipt_id = r.receipt_id)")
    raise KeyError(name)


DEPS = {"line_ok": [], "net": ["line_ok"], "mon": [], "comp_store": ["mon"], "dept_grp": [], "cust": ["line_ok"]}
SM = ("SELECT m.ym, m.mi, n.store_id, SUM(n.amt) AS sales\n"
      "    FROM net n JOIN mon m ON m.date_key = n.d\n"
      "    GROUP BY m.ym, m.mi, n.store_id")
REPORT_BODY = {
    "R1": (["net", "mon"], "SELECT m.ym, SUM(n.amt) AS sales\nFROM net n\nJOIN mon m ON m.date_key = n.d\nGROUP BY m.ym\nORDER BY m.ym"),
    "R2": (["net", "mon"], "SELECT m.ym, n.store_id, SUM(n.amt) AS sales\nFROM net n\nJOIN mon m ON m.date_key = n.d\nGROUP BY m.ym, n.store_id\nORDER BY m.ym, n.store_id"),
    "R3": (["net", "mon", "dept_grp"], "SELECT m.ym, g.grp, SUM(n.amt) AS sales\nFROM net n\nJOIN mon m ON m.date_key = n.d\nJOIN item i ON i.item_id = n.item_id\nJOIN dept_grp g ON g.dept_id = i.dept_id\nGROUP BY m.ym, g.grp\nORDER BY m.ym, g.grp"),
    "R4": (["net", "mon", "comp_store"],
           f"SELECT a.ym, SUM(a.sales) AS comp_sales, SUM(b.sales) AS comp_sales_ly,\n       SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy\n"
           f"FROM (\n    {SM}\n) a\nJOIN (\n    {SM}\n) b ON b.store_id = a.store_id AND b.mi = a.mi - 12\n"
           "JOIN comp_store cs ON cs.store_id = a.store_id AND cs.mi = a.mi\nGROUP BY a.ym\nORDER BY a.ym"),
    "R5": (["net", "mon", "cust"],
           "SELECT s.ym, s.sales, c.customers, s.sales * 1.0 / c.customers AS ticket\n"
           "FROM (SELECT m.ym, SUM(n.amt) AS sales FROM net n JOIN mon m ON m.date_key = n.d GROUP BY m.ym) s\n"
           "JOIN (SELECT m.ym, COUNT(DISTINCT u.cust_key) AS customers FROM cust u JOIN mon m ON m.date_key = u.date_key GROUP BY m.ym) c\n"
           "  ON c.ym = s.ym\nORDER BY s.ym"),
    "R6": (["net", "mon", "dept_grp"], "SELECT m.ym, n.store_id, g.grp, SUM(n.amt) AS sales\nFROM net n\nJOIN mon m ON m.date_key = n.d\nJOIN item i ON i.item_id = n.item_id\nJOIN dept_grp g ON g.dept_id = i.dept_id\nGROUP BY m.ym, n.store_id, g.grp\nORDER BY m.ym, n.store_id, g.grp"),
    "R7": (["net", "mon", "cust", "comp_store"],
           "SELECT s.ym, s.sales, c.customers, s.sales * 1.0 / c.customers AS ticket, k.yoy AS comp_yoy\n"
           "FROM (SELECT m.ym, SUM(n.amt) AS sales FROM net n JOIN mon m ON m.date_key = n.d GROUP BY m.ym) s\n"
           "JOIN (SELECT m.ym, COUNT(DISTINCT u.cust_key) AS customers FROM cust u JOIN mon m ON m.date_key = u.date_key GROUP BY m.ym) c\n"
           "  ON c.ym = s.ym\n"
           f"LEFT JOIN (\n  SELECT a.ym, SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy\n  FROM (\n    {SM}\n  ) a\n  JOIN (\n    {SM}\n  ) b ON b.store_id = a.store_id AND b.mi = a.mi - 12\n"
           "  JOIN comp_store cs ON cs.store_id = a.store_id AND cs.mi = a.mi\n  GROUP BY a.ym\n) k ON k.ym = s.ym\nORDER BY s.ym"),
    "R8": (["net", "mon"], "SELECT n.d AS date_key, SUM(n.amt) AS sales\nFROM net n\nJOIN mon m ON m.date_key = n.d\n"
           "WHERE m.ym = (SELECT MAX(m2.ym) FROM net n2 JOIN mon m2 ON m2.date_key = n2.d)\nGROUP BY n.d\nORDER BY n.d"),
}
TITLES = {"R1": "全社の月次売上", "R2": "店舗別の月次売上", "R3": "部門グループ別の月次売上", "R4": "既存店の前年比",
          "R5": "客数と客単価", "R6": "店舗×部門グループの月次売上", "R7": "KPI のまとめ", "R8": "直近月の日別売上"}


def closure(names):
    out = []
    def add(n):
        for d in DEPS[n]:
            add(d)
        if n not in out:
            out.append(n)
    for n in names:
        add(n)
    return [n for n in VIEW_ORDER if n in out]


def s3(P):
    files = {f"V_{v}.sql": f"CREATE VIEW {v} AS\n{view_body(P, v)};\n" for v in VIEW_ORDER}
    for r in REPORTS:
        files[f"{r}.sql"] = f"-- {r} {TITLES[r]}\n{REPORT_BODY[r][1]};\n"
    return files


def s2(P):
    files = {}
    for r in REPORTS:
        need = closure(REPORT_BODY[r][0])
        ctes = ",\n".join(f"{v} AS (\n{view_body(P, v)}\n)" for v in need)
        files[f"{r}.sql"] = f"-- {r} {TITLES[r]}\nWITH {ctes}\n{REPORT_BODY[r][1]};\n"
    return files


# ---------- S1 コピペ型：定義を式の中に直接書く ----------
def s1_net(P, ind):
    """明細の正味（売上−返品）を1つのサブクエリで書く。定義は全部ここに直接書かれる"""
    sp = " " * ind
    amt_s = "l.amount_incl" if not P["tax"] else "l.amount_incl * 100.0 / (100 + l.tax_pct)"
    amt_r = "r.amount_incl" if not P["tax"] else "r.amount_incl * 100.0 / (100 + l.tax_pct)"
    rd = "r.return_date_key" if P["ret"] == "return" else "l.date_key"
    j = f"\n{sp}JOIN store s ON s.store_id = l.store_id" if P["test"] else ""
    c = f"\n{sp}  AND s.is_test = 0" if P["test"] else ""
    return (f"{sp}SELECT l.date_key AS d, l.store_id, l.item_id, {amt_s} AS amt\n"
            f"{sp}FROM sales_line l{j}\n"
            f"{sp}WHERE {st(P, 'l')}{c}\n"
            f"{sp}UNION ALL\n"
            f"{sp}SELECT {rd} AS d, l.store_id, l.item_id, -{amt_r} AS amt\n"
            f"{sp}FROM returns_line r\n"
            f"{sp}JOIN sales_line l ON l.receipt_id = r.receipt_id AND l.line_no = r.line_no{j}\n"
            f"{sp}WHERE {st(P, 'l')}{c}")


def s1_sm(P, ind):
    y, m = ym(P)
    sp = " " * ind
    return (f"{sp}SELECT c.{y} AS ym, c.{m} AS mi, x.store_id, SUM(x.amt) AS sales\n"
            f"{sp}FROM (\n{s1_net(P, ind + 4)}\n{sp}) x\n"
            f"{sp}JOIN calendar c ON c.date_key = x.d\n"
            f"{sp}GROUP BY c.{y}, c.{m}, x.store_id")


def s1_comp_join(P, ind):
    y, m = ym(P)
    sp = " " * ind
    return (f"{sp}JOIN store cs ON cs.store_id = a.store_id\n"
            f"{sp}JOIN calendar oc ON oc.date_key = cs.open_date_key\n"
            f"{sp}WHERE oc.{m} <= a.mi - {P['gap']}")


def s1_cust(P, ind):
    y, m = ym(P)
    sp = " " * ind
    j = f"\n{sp}               JOIN store s ON s.store_id = l.store_id" if P["test"] else ""
    c = f" AND s.is_test = 0" if P["test"] else ""
    key = cust_key(P, "rc").replace("\n", "\n" + sp + "                      ")
    return (f"{sp}SELECT c.{y} AS ym, COUNT(DISTINCT {key}) AS customers\n"
            f"{sp}FROM receipt rc\n"
            f"{sp}JOIN calendar c ON c.date_key = rc.date_key\n"
            f"{sp}WHERE EXISTS (SELECT 1 FROM sales_line l{j}\n"
            f"{sp}              WHERE l.receipt_id = rc.receipt_id AND {st(P, 'l')}{c})\n"
            f"{sp}GROUP BY c.{y}")


def s1_sales_month(P, ind):
    y, m = ym(P)
    sp = " " * ind
    return (f"{sp}SELECT c.{y} AS ym, SUM(x.amt) AS sales\n"
            f"{sp}FROM (\n{s1_net(P, ind + 4)}\n{sp}) x\n"
            f"{sp}JOIN calendar c ON c.date_key = x.d\n"
            f"{sp}GROUP BY c.{y}")


def s1(P):
    y, m = ym(P)
    f = {}
    f["R1.sql"] = (f"-- R1 {TITLES['R1']}\nSELECT c.{y} AS ym, SUM(x.amt) AS sales\nFROM (\n{s1_net(P, 4)}\n) x\n"
                   f"JOIN calendar c ON c.date_key = x.d\nGROUP BY c.{y}\nORDER BY c.{y};\n")
    f["R2.sql"] = (f"-- R2 {TITLES['R2']}\nSELECT c.{y} AS ym, x.store_id, SUM(x.amt) AS sales\nFROM (\n{s1_net(P, 4)}\n) x\n"
                   f"JOIN calendar c ON c.date_key = x.d\nGROUP BY c.{y}, x.store_id\nORDER BY c.{y}, x.store_id;\n")
    g = grp_case(P, "i.dept_id", 7)
    f["R3.sql"] = (f"-- R3 {TITLES['R3']}\nSELECT c.{y} AS ym,\n       {g} AS grp,\n       SUM(x.amt) AS sales\nFROM (\n{s1_net(P, 4)}\n) x\n"
                   f"JOIN calendar c ON c.date_key = x.d\nJOIN item i ON i.item_id = x.item_id\n"
                   f"GROUP BY c.{y},\n       {g}\nORDER BY 1, 2;\n")
    f["R4.sql"] = (f"-- R4 {TITLES['R4']}\nSELECT a.ym, SUM(a.sales) AS comp_sales, SUM(b.sales) AS comp_sales_ly,\n"
                   f"       SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy\nFROM (\n{s1_sm(P, 4)}\n) a\nJOIN (\n{s1_sm(P, 4)}\n) b ON b.store_id = a.store_id AND b.mi = a.mi - 12\n"
                   f"{s1_comp_join(P, 0)}\nGROUP BY a.ym\nORDER BY a.ym;\n")
    f["R5.sql"] = (f"-- R5 {TITLES['R5']}\nSELECT s.ym, s.sales, k.customers, s.sales * 1.0 / k.customers AS ticket\nFROM (\n{s1_sales_month(P, 4)}\n) s\n"
                   f"JOIN (\n{s1_cust(P, 4)}\n) k ON k.ym = s.ym\nORDER BY s.ym;\n")
    f["R6.sql"] = (f"-- R6 {TITLES['R6']}\nSELECT c.{y} AS ym, x.store_id,\n       {g} AS grp,\n       SUM(x.amt) AS sales\nFROM (\n{s1_net(P, 4)}\n) x\n"
                   f"JOIN calendar c ON c.date_key = x.d\nJOIN item i ON i.item_id = x.item_id\n"
                   f"GROUP BY c.{y}, x.store_id,\n       {g}\nORDER BY 1, 2, 3;\n")
    f["R7.sql"] = (f"-- R7 {TITLES['R7']}\nSELECT s.ym, s.sales, k.customers, s.sales * 1.0 / k.customers AS ticket, q.yoy AS comp_yoy\nFROM (\n{s1_sales_month(P, 4)}\n) s\n"
                   f"JOIN (\n{s1_cust(P, 4)}\n) k ON k.ym = s.ym\n"
                   f"LEFT JOIN (\n  SELECT a.ym, SUM(a.sales) * 1.0 / SUM(b.sales) - 1 AS yoy\n  FROM (\n{s1_sm(P, 6)}\n  ) a\n  JOIN (\n{s1_sm(P, 6)}\n  ) b ON b.store_id = a.store_id AND b.mi = a.mi - 12\n"
                   f"{s1_comp_join(P, 2)}\n  GROUP BY a.ym\n) q ON q.ym = s.ym\nORDER BY s.ym;\n")
    f["R8.sql"] = (f"-- R8 {TITLES['R8']}\nSELECT x.d AS date_key, SUM(x.amt) AS sales\nFROM (\n{s1_net(P, 4)}\n) x\n"
                   f"JOIN calendar c ON c.date_key = x.d\n"
                   f"WHERE c.{y} = (\n    SELECT MAX(c2.{y})\n    FROM (\n{s1_net(P, 8)}\n    ) x2\n    JOIN calendar c2 ON c2.date_key = x2.d\n)\n"
                   f"GROUP BY x.d\nORDER BY x.d;\n")
    return f


STYLES = {"S1": s1, "S2": s2, "S3": s3}


def files(style, P):
    return STYLES[style](P)


def run_order(style, fs):
    """実行順：S3 はビューを先に作る"""
    if style == "S3":
        return [f"V_{v}.sql" for v in VIEW_ORDER], REPORTS
    return [], REPORTS
