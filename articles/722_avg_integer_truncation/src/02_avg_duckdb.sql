-- DuckDB で実行（1スレッド）。DuckDB の AVG は整数の列でも小数を返す。
-- SQL Server の AVG(整数の列) が小数を切り捨てることを、整数の割り算（//）で再現して並べる
SELECT store_id,
       COUNT(*)                         AS receipts,
       AVG(items)                       AS avg_items,            -- 小数のまま
       SUM(items) // COUNT(*)           AS avg_items_truncated,  -- SQL Server の AVG(items) の再現
       AVG(member_flag)                 AS member_rate,
       SUM(member_flag) // COUNT(*)     AS member_rate_truncated -- 0/1 の列は 0 になる
FROM receipts
GROUP BY store_id
ORDER BY store_id;
