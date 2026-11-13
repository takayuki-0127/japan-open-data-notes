-- 保有の年数（10年以上はまとめる）ごとの事故率と、事故の有無ごとの更新率（DuckDB）
-- 表 policy_years(policy_id, year, tenure, claims, renewed)
SELECT LEAST(tenure, 10)                                        AS tenure_band,
       COUNT(*)                                                 AS policy_years,
       SUM(claims)                                              AS claims,
       SUM(claims) * 1.0 / COUNT(*)                             AS claim_rate,
       AVG(CASE WHEN claims = 0 THEN renewed END)               AS renew_rate_no_claim,
       AVG(CASE WHEN claims > 0 THEN renewed * 1.0 END)         AS renew_rate_claim
FROM policy_years
GROUP BY 1
ORDER BY 1;
