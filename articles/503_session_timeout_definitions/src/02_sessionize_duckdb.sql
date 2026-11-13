-- 前のページから30分より空いたら新しいセッション（DuckDB で実行）。セッション数を返す
WITH g AS (
  SELECT user, ts,
         CASE WHEN LAG(ts) OVER (PARTITION BY user ORDER BY ts) IS NULL
                OR ts - LAG(ts) OVER (PARTITION BY user ORDER BY ts) > INTERVAL 30 MINUTE
              THEN 1 ELSE 0 END AS is_new
  FROM pv
), s AS (
  SELECT user, ts, SUM(is_new) OVER (PARTITION BY user ORDER BY ts ROWS UNBOUNDED PRECEDING) AS session_no
  FROM g
)
SELECT COUNT(DISTINCT (user, session_no)) FROM s
