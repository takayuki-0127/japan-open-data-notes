-- T-SQL 版（SQL Server では動かしていない：未検証）
-- 前のページから @timeout_min 分より空いたら新しいセッションにする
DECLARE @timeout_min int = 30;
WITH g AS (
  SELECT user_id, ts,
         CASE WHEN LAG(ts) OVER (PARTITION BY user_id ORDER BY ts) IS NULL
                OR DATEDIFF(second, LAG(ts) OVER (PARTITION BY user_id ORDER BY ts), ts) > @timeout_min * 60
              THEN 1 ELSE 0 END AS is_new
  FROM dbo.pageviews
), s AS (
  SELECT user_id, ts,
         SUM(is_new) OVER (PARTITION BY user_id ORDER BY ts ROWS UNBOUNDED PRECEDING) AS session_no
  FROM g
)
SELECT user_id, session_no, MIN(ts) AS started_at, COUNT(*) AS pages
FROM s GROUP BY user_id, session_no;
-- 日付が変わったら切る場合は、is_new に CAST(ts AS date) <> CAST(LAG(ts) ... AS date) を足す
-- 注意：同じ時刻のページが2つあると ORDER BY ts だけでは並びが決まらない（359 を参照）
