-- 452 小計や合計の行が混ざった表を足す（T-SQL 版）
-- 未検証：SQL Server 本体では動かしていません。同じ SQL を DuckDB で実行しました（a452_subtotals.py）。
-- 前提：dbo.cpi_weights(name nvarchar(100), code char(4), weight float, is_item bit, bekkei bit)
--       is_item＝品目（いちばん細かい行）、bekkei＝別掲（組み替えた合計・再掲）

-- そのまま足す（総合・類・品目・別掲がすべて入る）
SELECT SUM(weight) AS naive_all FROM dbo.cpi_weights;

-- 品目だけを足す（＝総合の行と一致するはず）
SELECT SUM(CASE WHEN is_item = 1 THEN weight END) AS items_only,
       MAX(CASE WHEN code = '0001' THEN weight END) AS total_row
FROM dbo.cpi_weights;

-- 照合：品目の合計と総合の行が合わなければ、行が抜けているか二重に入っている
SELECT CASE WHEN ABS(SUM(CASE WHEN is_item = 1 THEN weight END)
                   - MAX(CASE WHEN code = '0001' THEN weight END)) < 0.5
            THEN 'OK' ELSE 'NG' END AS check_result
FROM dbo.cpi_weights;
