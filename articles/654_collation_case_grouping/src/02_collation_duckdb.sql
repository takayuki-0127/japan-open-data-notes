-- 大文字小文字を区別する／しない（DuckDB 版）。orders(order_id, email, amount)、coupons_used(code)
-- (1) メールアドレスの人数：区別する（DuckDB の既定）・区別しない（NOCASE）・LOWER でそろえる
SELECT COUNT(DISTINCT email)                    AS n_case_sensitive,
       COUNT(DISTINCT email COLLATE NOCASE)     AS n_nocase,
       COUNT(DISTINCT LOWER(email))             AS n_lower
FROM orders;
-- (2) 顧客表とつなぐ：区別するとつながらない注文
SELECT SUM(CASE WHEN c.email IS NULL THEN 1 ELSE 0 END)           AS unmatched_cs,
       SUM(CASE WHEN c.email IS NULL THEN o.amount ELSE 0 END)    AS unmatched_amount_cs
FROM orders AS o LEFT JOIN customers AS c ON o.email = c.email;
SELECT SUM(CASE WHEN c.email IS NULL THEN 1 ELSE 0 END)           AS unmatched_ci
FROM orders AS o LEFT JOIN customers AS c ON o.email COLLATE NOCASE = c.email COLLATE NOCASE;
-- (3) 大文字小文字に意味のあるクーポンの番号：区別しないと別の番号がまとまる
SELECT COUNT(DISTINCT code) AS n_cs, COUNT(DISTINCT code COLLATE NOCASE) AS n_ci
FROM coupons_used;
