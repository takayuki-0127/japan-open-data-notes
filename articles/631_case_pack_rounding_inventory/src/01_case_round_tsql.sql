-- T-SQL：未検証（SQL Server では動かしていない）
-- 発注数をケース単位に直す。dbo.order_need(item_id, day, need_units, case_size, min_cases)
SELECT item_id, day, need_units, case_size,
       CASE WHEN need_units <= 0 THEN 0
            WHEN CEILING(CAST(need_units AS float) / case_size) < min_cases THEN min_cases * case_size
            ELSE CEILING(CAST(need_units AS float) / case_size) * case_size
       END AS order_units
FROM dbo.order_need;
