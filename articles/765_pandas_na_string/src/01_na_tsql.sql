-- T-SQL：未検証（SQL Server では動かしていない）
-- 取り込んだ文字の列に、欠けを表す文字の候補がどれだけあるかを数える
SELECT region, COUNT(*) AS n
FROM dbo.orders_stage
WHERE UPPER(region) IN ('NA', 'N/A', 'NULL', 'NONE', 'NAN', '#N/A') OR region IS NULL OR region = ''
GROUP BY region;
-- 地域コードの表と結べない行（NULL を含む）を数える
SELECT COUNT(*) AS unmatched
FROM dbo.orders_stage o
LEFT JOIN dbo.regions r ON r.region = o.region
WHERE r.region IS NULL;
