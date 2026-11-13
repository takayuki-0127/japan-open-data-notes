-- 2台の計量器の一致を、相関と「差の平均・一致の幅」で数える（DuckDB）
SELECT "case",
       CORR(old_kg, new_kg)                                         AS r,
       AVG(new_kg - old_kg)                                         AS mean_diff,
       STDDEV_SAMP(new_kg - old_kg)                                 AS sd_diff,
       AVG(new_kg - old_kg) - 1.96 * STDDEV_SAMP(new_kg - old_kg)   AS loa_low,
       AVG(new_kg - old_kg) + 1.96 * STDDEV_SAMP(new_kg - old_kg)   AS loa_high,
       AVG(CASE WHEN ABS(new_kg - old_kg) <= 0.3 THEN 1.0 ELSE 0 END) AS within_0_3
FROM paired
GROUP BY "case"
ORDER BY "case";
