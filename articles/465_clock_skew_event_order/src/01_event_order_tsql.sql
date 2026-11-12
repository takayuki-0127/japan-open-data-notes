-- 465 時計のずれと出来事の順番（T-SQL 版）
-- ※ SQL Server 本体では動かしていません（未検証）。同じ数え方を DuckDB で実行して確かめています（a465_clock.py）。
-- 表：dbo.access_log(user_id INT, seq INT, server INT, rec_t DECIMAL(12,3), kind NVARCHAR(10), gw_seq BIGINT)
--     seq は本当の順番（架空のデータなので分かっている）、rec_t はサーバーの時計で記録された時刻（秒）、
--     gw_seq は入口の装置が受け取った順に振った通し番号

-- 前の出来事との間隔がマイナスになった件数（本当の順に並べて、記録の時刻の差を見る）
SELECT SUM(CASE WHEN d < 0 THEN 1 ELSE 0 END) AS negative_gaps, COUNT(d) AS pairs
FROM (SELECT rec_t - LAG(rec_t) OVER (PARTITION BY user_id ORDER BY seq) AS d FROM dbo.access_log) AS x;

-- 記録された時刻で並べたときの「最初の出来事」
SELECT kind, COUNT(*) AS n_users
FROM (SELECT user_id, kind, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY rec_t, seq) AS rn
      FROM dbo.access_log) AS x
WHERE rn = 1 GROUP BY kind;

-- 通し番号で並べたときの「最初の出来事」（順番は時計に左右されない）
SELECT kind, COUNT(*) AS n_users
FROM (SELECT user_id, kind, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY gw_seq) AS rn
      FROM dbo.access_log) AS x
WHERE rn = 1 GROUP BY kind;

-- 購入の直前の出来事
SELECT prev_kind, COUNT(*) AS n
FROM (SELECT kind, LAG(kind) OVER (PARTITION BY user_id ORDER BY rec_t, seq) AS prev_kind FROM dbo.access_log) AS x
WHERE kind = N'購入' GROUP BY prev_kind;
