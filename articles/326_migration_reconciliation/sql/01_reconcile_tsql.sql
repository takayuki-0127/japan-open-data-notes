-- 326 移行の前後の照合（T-SQL 版）。SQL Server 本体では動かしていません（未検証）。
-- 同じ照合を DuckDB で動かしたものは src/a326_reconcile.py にあります。old_* が旧システム、new_* が新システムの表です。

-- C1 件数
SELECT (SELECT COUNT(*) FROM old_tx) AS old_rows, (SELECT COUNT(*) FROM new_tx) AS new_rows;

-- C2 合計（数値の列）
SELECT (SELECT SUM(amount) FROM old_tx) AS old_sum, (SELECT SUM(amount) FROM new_tx) AS new_sum;

-- C3 キーの有無と重複
SELECT tx_id FROM old_tx EXCEPT SELECT tx_id FROM new_tx;          -- 新システムにないキー
SELECT tx_id FROM new_tx EXCEPT SELECT tx_id FROM old_tx;          -- 新システムにだけあるキー
SELECT tx_id, COUNT(*) AS n FROM new_tx GROUP BY tx_id HAVING COUNT(*) > 1;   -- 2回以上出るキー

-- C4 列ごとのハッシュ：キーと値を1つの文字列にしてハッシュし、足し合わせる（NULL は印に置き換える）
-- 足し合わせる形にするのは、XOR でまとめる形だと、同じ値どうしの入れ替わりや偶数回の変化が打ち消し合うため
SELECT SUM(CAST(CAST(HASHBYTES('SHA2_256',
           CONCAT(tx_id, '|', COALESCE(CONVERT(VARCHAR(40), amount), '<NULL>'))) AS BINARY(7)) AS BIGINT) % 1000000007) AS h_amount
FROM old_tx;   -- new_tx でも同じ式を流し、列ごとに値を比べる

-- C5 抜き取り：旧システムから300行のキーを引き、全列を比べる
SELECT TOP (300) o.tx_id
INTO #pick FROM old_tx o ORDER BY NEWID();
SELECT o.*, n.*
FROM #pick p JOIN old_tx o ON o.tx_id = p.tx_id LEFT JOIN new_tx n ON n.tx_id = p.tx_id
WHERE n.tx_id IS NULL
   OR NOT EXISTS (SELECT o.account_id, o.tx_at, o.amount, o.memo INTERSECT SELECT n.account_id, n.tx_at, n.amount, n.memo);   -- NULL どうしも「同じ」と扱う比べ方
