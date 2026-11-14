-- T-SQL：未検証（SQL Server では動かしていない）
-- items・member_flag が int の列だと、AVG の結果も int になり、小数は切り捨てられる（とされる）
SELECT store_id,
       AVG(items)                          AS avg_items_int,      -- 例：2.74 → 2
       AVG(items * 1.0)                    AS avg_items,          -- 小数で平均
       AVG(CAST(items AS decimal(10, 4)))  AS avg_items_dec,
       AVG(member_flag)                    AS member_rate_int,    -- 0/1 の列は 0（全員が1の店だけ1）
       AVG(CAST(member_flag AS float))     AS member_rate
FROM receipts
GROUP BY store_id
ORDER BY store_id;
