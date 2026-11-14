-- 月ごとの客単価を4通りで出す（DuckDB）
WITH q AS (
    SELECT month, quantile_cont(amount, 0.99) AS p99 FROM receipts GROUP BY month
)
SELECT r.month,
       AVG(r.amount)                                          AS mean_all,        -- 全体
       AVG(r.amount) FILTER (WHERE r.is_business = 0)         AS mean_personal,   -- 法人の大口を除く
       median(r.amount)                                       AS median_all,      -- 中央値
       AVG(LEAST(r.amount, q.p99))                            AS mean_capped      -- 上位1%の値で頭打ち
FROM receipts AS r
JOIN q USING (month)
GROUP BY r.month
ORDER BY r.month;
