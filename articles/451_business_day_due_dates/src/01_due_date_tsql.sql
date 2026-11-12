-- 451 「5営業日後」の期日を出す（T-SQL 版）
-- 未検証：SQL Server 本体では動かしていません。同じ考え方の SQL を DuckDB で実行し、Python の計算と6万件すべてで一致することを確かめました（a451_due_dates.py）。
-- 前提：dbo.calendar(d date, is_off bit) に、休みの日（土日・祝日と休日・年末年始）を 1 で入れておく。
--       dbo.tx(tx_id int, received date)
WITH cal AS (
    SELECT d, is_off,
           SUM(CASE WHEN is_off = 1 THEN 0 ELSE 1 END)
               OVER (ORDER BY d ROWS UNBOUNDED PRECEDING) AS biz_no   -- その日までの営業日の数
    FROM dbo.calendar
),
biz AS (
    SELECT d, biz_no FROM cal WHERE is_off = 0
)
SELECT t.tx_id, t.received, b.d AS due_date
FROM dbo.tx AS t
JOIN cal AS c ON c.d = t.received
JOIN biz AS b ON b.biz_no = c.biz_no + 5        -- 受付日の次の営業日を1日目として5営業日目
ORDER BY t.tx_id;

-- 祝日の一覧が足りているかの点検：取引の期間の最後の年まで、祝日が1件以上あるか
SELECT YEAR(d) AS y, COUNT(*) AS holidays
FROM dbo.holidays
GROUP BY YEAR(d)
ORDER BY y;
