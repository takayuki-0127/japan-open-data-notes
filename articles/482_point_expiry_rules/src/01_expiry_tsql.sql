-- 482 付与ごとの失効額をウィンドウ関数で出す（T-SQL 版。SQL Server では動かしていない：未検証）
-- grants(grant_id, member, day, exp_day, pts)：exp_day はこの日から使えない日
-- uses(member, day, pts)：使ったポイント。古い付与から順に使う（先入れ先出し）
-- 考え方：付与 g までの累計付与 − g の失効日より前の累計利用 を X_g とすると、
--         g までの累計失効額 = 0 と X_1..X_g の最大値（失効の順番が付与の順番と同じときに成り立つ）
WITH g AS (
    SELECT grant_id, member, day, exp_day, pts,
           SUM(pts) OVER (PARTITION BY member ORDER BY day, grant_id ROWS UNBOUNDED PRECEDING) AS cum_g
    FROM grants
), gu AS (
    SELECT g.*, ISNULL(u.cum_u, 0) AS cum_u
    FROM g
    OUTER APPLY (SELECT SUM(x.pts) AS cum_u FROM uses AS x
                 WHERE x.member = g.member AND x.day < g.exp_day) AS u
), x AS (
    SELECT *,
           MAX(cum_g - cum_u) OVER (PARTITION BY member ORDER BY day, grant_id ROWS UNBOUNDED PRECEDING) AS run_max
    FROM gu
), y AS (
    SELECT *, CASE WHEN run_max > 0 THEN run_max ELSE 0 END AS cum_e FROM x
)
SELECT grant_id, member, exp_day,
       cum_e - ISNULL(LAG(cum_e) OVER (PARTITION BY member ORDER BY day, grant_id), 0) AS expired
FROM y;
-- 失効日の決め方
--   付与日から1年      : DATEADD(day, 365, grant_date)
--   付与月の1年後の月末 : DATEADD(day, 1, EOMONTH(grant_date, 12))   -- この日から使えない
