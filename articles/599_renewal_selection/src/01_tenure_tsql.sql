-- 保有の年数（10年以上はまとめる）ごとの事故率と、事故の有無ごとの更新率
-- （T-SQL、未検証：SQL Server では動かしていない）。表 dbo.policy_years(policy_id, year, tenure, claims, renewed)
SELECT IIF(tenure >= 10, 10, tenure)                                  AS tenure_band,
       COUNT(*)                                                       AS policy_years,
       SUM(claims)                                                    AS claims,
       CAST(SUM(claims) AS float) / COUNT(*)                          AS claim_rate,
       AVG(CASE WHEN claims = 0 THEN CAST(renewed AS float) END)      AS renew_rate_no_claim,
       AVG(CASE WHEN claims > 0 THEN CAST(renewed AS float) END)      AS renew_rate_claim
FROM dbo.policy_years
GROUP BY IIF(tenure >= 10, 10, tenure)
ORDER BY tenure_band;
