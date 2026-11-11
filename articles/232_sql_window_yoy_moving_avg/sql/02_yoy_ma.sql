-- 02 前年同月比と12か月移動平均（T-SQL。DuckDB でも同じ文で動くことを確認）
SELECT
    gyotai,
    ym,
    sales,
    LAG(sales, 12) OVER (PARTITION BY gyotai ORDER BY ym)          AS sales_12m_ago,
    CAST(sales AS FLOAT)
      / NULLIF(LAG(sales, 12) OVER (PARTITION BY gyotai ORDER BY ym), 0) - 1
                                                                   AS yoy,
    AVG(CAST(sales AS FLOAT)) OVER (PARTITION BY gyotai ORDER BY ym
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)                 AS ma12_raw,
    COUNT(*) OVER (PARTITION BY gyotai ORDER BY ym
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW)                 AS ma12_n
FROM dbo.sales_monthly
ORDER BY gyotai, ym;
-- ma12_n が 12 未満の行（最初の11か月）は、平均の月数が足りないので使わない
