SELECT store_id,
       COUNT(*)                                  AS n,
       AVG(score)                                AS mean_score,
       AVG(CASE WHEN score >= 4 THEN 1.0 ELSE 0.0 END) * 100 AS top2_pct,
       AVG(CASE WHEN score <= 2 THEN 1.0 ELSE 0.0 END) * 100 AS bottom2_pct
FROM survey
GROUP BY store_id
ORDER BY store_id
