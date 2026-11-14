-- 「建物名」の未入力を3通りで数える（DuckDB）
SELECT source,
       COUNT(*)                                                         AS n,
       SUM(CASE WHEN building IS NULL THEN 1 ELSE 0 END)                AS blank_isnull,   -- NULL だけ
       SUM(CASE WHEN building IS NULL OR building = '' THEN 1 ELSE 0 END) AS blank_empty,  -- NULL と空の文字
       SUM(CASE WHEN building IS NULL OR trim(building, ' 　') = '' THEN 1 ELSE 0 END) AS blank_trim, -- 空白だけの値も
       COUNT(building)                                                  AS count_col       -- COUNT(列) は '' も数える
FROM customers
GROUP BY source
ORDER BY source;
