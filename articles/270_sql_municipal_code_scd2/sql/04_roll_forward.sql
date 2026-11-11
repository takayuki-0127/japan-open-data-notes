-- 04 2000年のコードを、いまのコードまでたどる（T-SQL の再帰 CTE。DuckDB では WITH RECURSIVE）
WITH chain AS (
    SELECT code AS code2000, code AS cur, CAST('2000-10-01' AS DATE) AS since, 0 AS steps
    FROM dbo.units2000
    UNION ALL
    SELECT c.code2000, x.new_code, x.eff_date, c.steps + 1
    FROM chain c
    JOIN dbo.events_x x ON x.old_code = c.cur AND x.old_code <> x.new_code AND x.eff_date >= c.since  -- 同じ日の連続（編入→市制）もたどる
)
SELECT code2000, cur AS code_now, steps
INTO dbo.crosswalk
FROM chain c
WHERE NOT EXISTS (SELECT 1 FROM dbo.events_x x                 -- その先がもうない行だけ残す
                  WHERE x.old_code = c.cur AND x.old_code <> x.new_code AND x.eff_date >= c.since);
