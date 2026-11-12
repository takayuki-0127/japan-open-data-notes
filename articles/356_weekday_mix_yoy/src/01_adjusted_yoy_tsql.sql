-- 曜日の型で割った前年同月比（T-SQL。SQL Server 本体では動かしていません：未検証）
-- calendar(d, dtype)：dtype は 0=月 … 6=日、7=祝日・休日　　weights(dtype, w)：日の種類ごとの重み
WITH m AS (
  SELECT DATEFROMPARTS(YEAR(s.d), MONTH(s.d), 1) AS ym,
         SUM(s.amount) AS sales,
         SUM(w.w)      AS wsum
  FROM sales AS s
  JOIN calendar AS c ON c.d = s.d
  JOIN weights  AS w ON w.dtype = c.dtype
  GROUP BY DATEFROMPARTS(YEAR(s.d), MONTH(s.d), 1)
)
SELECT ym, sales, wsum,
       (sales / LAG(sales, 12) OVER (ORDER BY ym) - 1) * 100 AS yoy_raw,
       ((sales / wsum) / (LAG(sales, 12) OVER (ORDER BY ym) / LAG(wsum, 12) OVER (ORDER BY ym)) - 1) * 100 AS yoy_adj
FROM m
ORDER BY ym;
-- 注意：LAG(…, 12) は月が1つも抜けていない前提（抜けがあると黙ってずれる。232 を参照）
