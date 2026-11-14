-- DuckDB で実行（1スレッド）。月ごとの前年同月比を3通りで出す
WITH m AS (
    SELECT year(sales_date) AS y, month(sales_date) AS mo,
           SUM(sales) AS total, COUNT(*) AS days,
           SUM(CASE WHEN month(sales_date) = 2 AND day(sales_date) = 29 THEN 0 ELSE sales END) AS total_ex29
    FROM daily_sales
    GROUP BY 1, 2
)
SELECT c.y, c.mo,
       c.total / p.total - 1                               AS yoy_plain,     -- そのまま
       (c.total / c.days) / (p.total / p.days) - 1         AS yoy_per_day,   -- 日あたり
       c.total_ex29 / p.total_ex29 - 1                     AS yoy_ex29       -- 2月29日を除く
FROM m c JOIN m p ON p.y = c.y - 1 AND p.mo = c.mo
ORDER BY c.y, c.mo;
