-- 月ごとに「達成店」を3通りで数える（DuckDB）
SELECT month,
       COUNT(*) FILTER (WHERE actual >= target)                              AS achieved_exact,   -- 丸める前に判定
       COUNT(*) FILTER (WHERE ROUND(actual * 100.0 / target, 0) >= 100)      AS achieved_round0,  -- 整数の%に丸めてから
       COUNT(*) FILTER (WHERE ROUND(actual * 100.0 / target, 1) >= 100)      AS achieved_round1,  -- 小数1桁に丸めてから
       COUNT(*) AS stores
FROM results
GROUP BY month
ORDER BY month;
