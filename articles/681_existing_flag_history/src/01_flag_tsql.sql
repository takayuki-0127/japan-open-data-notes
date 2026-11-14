-- T-SQL：未検証
-- 年ごとの売上を3通りで集計する。month は 'YYYY-MM' の文字列
SELECT CAST(LEFT(s.month, 4) AS INT)                                            AS [year],
       SUM(s.amount)                                                            AS [none],    -- 絞らない
       SUM(CASE WHEN p.is_active = 1 THEN s.amount ELSE 0 END)                  AS flag,      -- 「有効」フラグで絞る
       SUM(CASE WHEN s.month >= p.valid_from
                 AND (p.valid_to IS NULL OR s.month <= p.valid_to)
                THEN s.amount ELSE 0 END)                                       AS period     -- 期間つきで絞る
FROM dbo.sales AS s
JOIN dbo.products AS p ON p.product_id = s.product_id
GROUP BY CAST(LEFT(s.month, 4) AS INT)
ORDER BY [year];
