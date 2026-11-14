-- 年ごとの売上を3通りで集計する（DuckDB）
SELECT CAST(SUBSTR(s.month, 1, 4) AS INTEGER)                                  AS year,
       SUM(s.amount)                                                            AS "none",    -- 絞らない
       SUM(CASE WHEN p.is_active = 1 THEN s.amount ELSE 0 END)                  AS flag,      -- 「有効」フラグで絞る
       SUM(CASE WHEN s.month >= p.valid_from
                 AND (p.valid_to IS NULL OR s.month <= p.valid_to)
                THEN s.amount ELSE 0 END)                                       AS period     -- 期間つきで絞る
FROM sales s
JOIN products p USING (product_id)
GROUP BY 1
ORDER BY 1;
