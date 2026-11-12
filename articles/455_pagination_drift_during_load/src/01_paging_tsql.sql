-- 455 1ページずつ取り込むときの3つの送り方（T-SQL 版）
-- 未検証：SQL Server 本体では動かしていません。同じ送り方を SQLite の SQL（LIMIT/OFFSET、キーの続き）で流し、
-- シミュレーションと数が一致することを確かめました（a455_pagination.py、results/sqlite_check.csv）。
-- 前提：dbo.t(id bigint PRIMARY KEY, ...)。@page＝1ページの行数

-- ① 何行目から、で区切る（途中で行が消えると、後ろの行が前に詰まって抜ける）
SELECT id FROM dbo.t ORDER BY id
OFFSET @offset ROWS FETCH NEXT @page ROWS ONLY;

-- ② キーの続きから取る（前のページの最後のキーより後ろを取る）
SELECT TOP (@page) id FROM dbo.t
WHERE id > @last_id
ORDER BY id;

-- ③ 取り込みを始めた時点で固定する（開始時点の最大のキーまでに限って、キーの続きから取る）
DECLARE @max_at_start bigint = (SELECT MAX(id) FROM dbo.t);   -- 取り込みの最初に1回だけ
SELECT TOP (@page) id FROM dbo.t
WHERE id > @last_id AND id <= @max_at_start
ORDER BY id;

-- 照合：件数ではなく、キーの重なりと抜けを見る
SELECT id, COUNT(*) AS n FROM dbo.loaded GROUP BY id HAVING COUNT(*) > 1;                 -- 重なった行
SELECT s.id FROM dbo.t AS s LEFT JOIN dbo.loaded AS l ON l.id = s.id WHERE l.id IS NULL;  -- 抜けた行（取り込みの後に増えた行も出る）
