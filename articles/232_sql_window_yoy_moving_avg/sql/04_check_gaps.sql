-- 04 抜けている月の点検：前の行との間が1か月でない行を探す（T-SQL）
SELECT gyotai, prev_ym, ym, DATEDIFF(month, prev_ym, ym) AS gap_months
FROM (
    SELECT gyotai, ym,
           LAG(ym) OVER (PARTITION BY gyotai ORDER BY ym) AS prev_ym
    FROM dbo.sales_monthly
) AS t
WHERE DATEDIFF(month, prev_ym, ym) <> 1;
