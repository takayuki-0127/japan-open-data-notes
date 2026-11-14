-- T-SQL：未検証（SQL Server では動かしていない）
SELECT store_id, profit_prev, profit_cur,
       profit_cur - profit_prev                                          AS diff,
       (profit_cur - profit_prev) * 1.0 / NULLIF(profit_prev, 0)         AS growth_plain,
       (profit_cur - profit_prev) * 1.0 / NULLIF(ABS(profit_prev), 0)    AS growth_absbase,
       CASE WHEN profit_prev <= 0 THEN NULL
            ELSE (profit_cur - profit_prev) * 1.0 / profit_prev END      AS growth_or_null
FROM profits
ORDER BY store_id;
