-- 03 月が抜けていても正しい前年同月比：行の位置ではなく「12か月前の日付」で結合する（T-SQL）
SELECT
    c.gyotai,
    c.ym,
    c.sales,
    p.sales                                            AS sales_12m_ago,
    CAST(c.sales AS FLOAT) / NULLIF(p.sales, 0) - 1    AS yoy
FROM dbo.sales_monthly AS c
LEFT JOIN dbo.sales_monthly AS p
       ON p.gyotai = c.gyotai
      AND p.ym     = DATEADD(month, -12, c.ym)
ORDER BY c.gyotai, c.ym;
