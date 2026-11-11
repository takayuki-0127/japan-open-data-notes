-- 既存店の前年同月比を、客数・1回の買上点数・一品単価に分ける（SQL Server でも動く書き方：CTE・CASE・DATEADD 相当は避けて ym 文字列で）
-- 入力：fact_store_day(biz_date, store_id, receipts, items, sales), dim_store(store_id, open_date, close_date)
WITH m AS (
    SELECT store_id, SUBSTRING(CAST(biz_date AS VARCHAR), 1, 7) AS ym,
           SUM(receipts) AS receipts, SUM(items) AS items, SUM(sales) AS sales
    FROM fact_store_day
    GROUP BY store_id, SUBSTRING(CAST(biz_date AS VARCHAR), 1, 7)
), cal AS (   -- 月ごとの月初・月末（ym_prev は12か月前）
    SELECT DISTINCT ym, CAST(ym || '-01' AS DATE) AS m_start,
           CAST(ym || '-01' AS DATE) + INTERVAL 1 MONTH - INTERVAL 1 DAY AS m_end,
           CAST(CAST(SUBSTRING(ym, 1, 4) AS INTEGER) - 1 AS VARCHAR) || SUBSTRING(ym, 5, 3) AS ym_prev
    FROM m
), ex AS (   -- 既存店：月初で開店から13か月以上、かつ月末まで営業
    SELECT c.ym, c.ym_prev, s.store_id
    FROM cal c CROSS JOIN dim_store s
    WHERE s.open_date + INTERVAL 13 MONTH <= c.m_start
      AND (s.close_date IS NULL OR s.close_date >= c.m_end)
), agg AS (
    SELECT e.ym,
           COUNT(*) AS n_stores,
           SUM(cur.sales) AS s1, SUM(pre.sales) AS s0,
           SUM(cur.receipts) AS r1, SUM(pre.receipts) AS r0,
           SUM(cur.items) AS i1, SUM(pre.items) AS i0
    FROM ex e
    JOIN m cur ON cur.store_id = e.store_id AND cur.ym = e.ym
    JOIN m pre ON pre.store_id = e.store_id AND pre.ym = e.ym_prev
    GROUP BY e.ym
)
SELECT ym, n_stores,
       s1 / s0 - 1 AS sales_yoy,
       r1 / r0 - 1 AS receipts_yoy,
       (i1 / r1) / (i0 / r0) - 1 AS items_per_receipt_yoy,
       (s1 / i1) / (s0 / i0) - 1 AS unit_price_yoy
FROM agg
WHERE ym >= '2024-04'
ORDER BY ym;
