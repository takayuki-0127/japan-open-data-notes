-- 発注数をケース単位に直す（DuckDB 版）。order_need(item_id, day, need_units, case_size, min_cases)
SELECT item_id, day, need_units, case_size,
       CASE WHEN need_units <= 0 THEN 0
            ELSE GREATEST(CEIL(need_units * 1.0 / case_size), min_cases) * case_size
       END AS order_units
FROM order_need;
