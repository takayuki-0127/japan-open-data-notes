-- 454 同時に同じ行を書き換えるときの3つの書き方（T-SQL 版）
-- 未検証：SQL Server 本体では動かしていません。SQL Server のロック・分離レベル・ROWVERSION の動きは確かめていません。
-- 同じ流れを SQLite の2つの接続で順番を決めて流し、結果を確かめました（a454_lost_updates.py、results/sqlite_demo.csv）。
-- 前提：dbo.stock(item_id int PRIMARY KEY, qty int, ver int)

-- ① 読んでから書く（2つの処理が同じ値を読むと、先に書いたほうの更新が消える）
DECLARE @q int;
SELECT @q = qty FROM dbo.stock WHERE item_id = 1;
-- （アプリの側で計算する時間）
UPDATE dbo.stock SET qty = @q - 3 WHERE item_id = 1;

-- ② 1文の UPDATE で足し引きする（読むのと書くのを1文にする）
UPDATE dbo.stock SET qty = qty - 3 WHERE item_id = 1;

-- ③ 版番号を確かめてから書く（読んだときの版と同じなら書く。0行ならやり直す）
DECLARE @q2 int, @v int;
SELECT @q2 = qty, @v = ver FROM dbo.stock WHERE item_id = 1;
UPDATE dbo.stock SET qty = @q2 - 3, ver = ver + 1 WHERE item_id = 1 AND ver = @v;
IF @@ROWCOUNT = 0
    PRINT '版が変わっている。読み直してやり直す';
