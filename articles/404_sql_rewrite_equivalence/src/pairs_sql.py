"""もとの集計 SQL（BASE）と、違いを1つずつ入れた書き直し10本（DIFFS）、答えは同じ書き直し6本（HARMLESS）。
T-SQL でも通る書き方に寄せてある（MONTH・COALESCE・TRIM・CASE）。SQL Server では未検証。"""
BASE = """
SELECT COALESCE(TRIM(c.segment), '不明') AS seg, MONTH(o.ordered_at) AS m,
       COUNT(*) AS n, SUM(ROUND(o.amount - COALESCE(o.discount, 0), 0)) AS amount
FROM orders o
LEFT JOIN customers c ON c.cust_id = o.cust_id
WHERE o.ordered_at >= TIMESTAMP '2025-01-01' AND o.ordered_at < TIMESTAMP '2026-01-01'
  AND (o.status <> 'cancel' OR o.status IS NULL)
GROUP BY COALESCE(TRIM(c.segment), '不明'), MONTH(o.ordered_at)"""

def sub(old, new, sql=BASE):
    assert old in sql, old
    return sql.replace(old, new)

DETAIL = """
SELECT o.cust_id, CAST(o.ordered_at AS DATE) AS d, o.amount
FROM orders o
WHERE (o.status <> 'cancel' OR o.status IS NULL)"""

DIFFS = {
 "①LEFT JOIN を INNER JOIN に": dict(b=sub("LEFT JOIN customers", "JOIN customers"), num="amount"),
 "②期間の終わりを「12/31 以下」に": dict(b=sub("o.ordered_at < TIMESTAMP '2026-01-01'", "o.ordered_at <= TIMESTAMP '2025-12-31'"), num="amount"),
 "③値引きの COALESCE を外す": dict(b=sub("COALESCE(o.discount, 0)", "o.discount"), num="amount"),
 "④状態が NULL の行の扱いを落とす": dict(b=sub("(o.status <> 'cancel' OR o.status IS NULL)", "o.status <> 'cancel'"), num="amount"),
 "⑤丸めてから足す → 足してから丸める": dict(b=sub("SUM(ROUND(o.amount - COALESCE(o.discount, 0), 0))", "ROUND(SUM(o.amount - COALESCE(o.discount, 0)), 0)"), num="amount"),
 "⑥重複のあるマスタにつなぐ": dict(b=sub("LEFT JOIN customers c", "LEFT JOIN customers_dup c"), num="amount"),
 "⑦明細に DISTINCT を足す": dict(a=DETAIL, b=DETAIL.replace("SELECT o.cust_id", "SELECT DISTINCT o.cust_id"), num="amount"),
 "⑧区分の名前を2つ取り違える": dict(b="SELECT CASE seg WHEN '学校' THEN '官公庁' WHEN '官公庁' THEN '学校' ELSE seg END AS seg, m, n, amount FROM (" + BASE + ") x", num="amount"),
 "⑨半期ごとに分けて足し、6月が2回入る": dict(b="SELECT * FROM (" + BASE + ") x WHERE m <= 6 UNION ALL SELECT * FROM (" + BASE + ") y WHERE m >= 6", num="amount"),
 "⑩区分の TRIM を外す": dict(b=BASE.replace("TRIM(c.segment)", "c.segment"), num="amount"),
}

F_A = "SELECT cust_id % 50 AS g, SUM(amount) AS amount FROM orders_f GROUP BY cust_id % 50"
HARMLESS = {
 "ⓐ足す順が変わる（小数は浮動小数）": dict(a=F_A, b=F_A.replace("orders_f", "orders_f_desc"), num="amount"),
 "ⓑ数の型が変わる（整数 → 浮動小数）": dict(a="SELECT seg, m, n, CAST(amount AS BIGINT) AS amount FROM (" + BASE + ") x",
                                    b="SELECT seg, m, n, CAST(amount AS DOUBLE) AS amount FROM (" + BASE + ") x", num="amount"),
 "ⓒ並び順だけ変わる": dict(a="SELECT * FROM (" + BASE + ") x ORDER BY seg, m", b="SELECT * FROM (" + BASE + ") x ORDER BY m, seg", num="amount"),
 "ⓓ平均を AVG から SUM÷COUNT に": dict(a="SELECT cust_id % 50 AS g, AVG(amount) AS amount FROM orders_f GROUP BY cust_id % 50",
                                  b="SELECT cust_id % 50 AS g, SUM(amount) / COUNT(*) AS amount FROM orders_f_desc GROUP BY cust_id % 50", num="amount"),
 "ⓔ列の順だけ変わる": dict(a="SELECT seg, m, n, amount FROM (" + BASE + ") x", b="SELECT m, seg, amount, n FROM (" + BASE + ") x", num="amount"),
 "ⓕ外部結合＋絞り込み → 内部結合": dict(a=sub("GROUP BY", "  AND c.cust_id IS NOT NULL\nGROUP BY"), b=sub("LEFT JOIN customers", "JOIN customers"), num="amount"),
}
