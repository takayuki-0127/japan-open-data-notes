-- 曜日の型で割った前年同月比（DuckDB で実行した版）
WITH m AS (                       -- 月の売上と、その月の「重みの合計」
  SELECT strftime(s.d, '%Y-%m') AS ym,
         SUM(s.amount) AS sales,
         SUM(w.w)      AS wsum
  FROM sales AS s
  JOIN calendar AS c ON c.d = s.d
  JOIN weights  AS w ON w.dtype = c.dtype
  GROUP BY strftime(s.d, '%Y-%m')
)
SELECT ym, sales, wsum,
       (sales / LAG(sales, 12) OVER (ORDER BY ym) - 1) * 100 AS yoy_raw,
       ((sales / wsum) / (LAG(sales, 12) OVER (ORDER BY ym) / LAG(wsum, 12) OVER (ORDER BY ym)) - 1) * 100 AS yoy_adj
FROM m
ORDER BY ym;
