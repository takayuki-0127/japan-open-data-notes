-- 新しいデータが予測の区間 [lo, hi] から外れた割合を、売場面積の帯ごとに数える（DuckDB）
-- 帯は面積 1〜10 を 0.9 ずつ10等分したもの
SELECT LEAST(CAST(FLOOR((area - 1) / 0.9) AS INTEGER), 9)  AS band,
       COUNT(*)                                             AS n,
       AVG(CASE WHEN sales < lo OR sales > hi THEN 1.0 ELSE 0.0 END) AS miss_rate,
       AVG(hi - lo)                                         AS avg_width
FROM pred
GROUP BY 1
ORDER BY 1;
