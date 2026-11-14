-- 2025年の月ごとの前年比を「全店」と「既存店」で出す（DuckDB 版）
-- monthly(store_id, ym, sales, open_days, days_in_month)：その月に営業した店だけ行がある
WITH cur AS (SELECT * FROM monthly WHERE ym >= '2025-01' AND ym <= '2025-12'),
     prv AS (SELECT store_id, strftime(strptime(ym || '-01', '%Y-%m-%d') + INTERVAL 1 YEAR, '%Y-%m') AS ym, sales, open_days, days_in_month
             FROM monthly WHERE ym >= '2024-01' AND ym <= '2024-12')
SELECT c.ym,
       SUM(c.sales)                                                     AS sales_all,
       (SELECT SUM(p2.sales) FROM prv AS p2 WHERE p2.ym = c.ym)         AS sales_all_prev,
       SUM(CASE WHEN p.store_id IS NOT NULL AND c.open_days = c.days_in_month AND p.open_days = p.days_in_month
                THEN c.sales END)                                       AS sales_same,
       SUM(CASE WHEN c.open_days = c.days_in_month AND p.open_days = p.days_in_month THEN p.sales END) AS sales_same_prev
FROM cur AS c LEFT JOIN prv AS p ON p.store_id = c.store_id AND p.ym = c.ym
GROUP BY c.ym
ORDER BY c.ym;
