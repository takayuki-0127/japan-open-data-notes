-- DuckDB で実行（1スレッド）。3通りの「1人あたり」と、その順位
WITH s AS (
    SELECT staff_id,
           SUM(cases) / COUNT(DISTINCT work_date)   AS cases_per_day,
           SUM(cases) / SUM(hours)                  AS cases_per_hour,
           SUM(cases * difficulty) / SUM(hours)     AS weighted_per_hour
    FROM daily_work
    GROUP BY staff_id
)
SELECT *,
       RANK() OVER (ORDER BY cases_per_day DESC)     AS rank_day,
       RANK() OVER (ORDER BY cases_per_hour DESC)    AS rank_hour,
       RANK() OVER (ORDER BY weighted_per_hour DESC) AS rank_weighted
FROM s
ORDER BY staff_id;
