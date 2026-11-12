-- 445 依存を書いた定義から、流す順番（段）を作る（T-SQL 版。SQL Server 本体では未検証。同じ考え方の SQL を DuckDB で実行して確かめた）
-- deps(table_name NVARCHAR(20), depends_on NVARCHAR(20))   … table_name は depends_on を読んで作る
-- tables(table_name NVARCHAR(20))
WITH lv AS (
  SELECT t.table_name, 0 AS lvl
  FROM tables t
  WHERE NOT EXISTS (SELECT 1 FROM deps d WHERE d.table_name = t.table_name)      -- 何も読まない表（取り込み）
  UNION ALL
  SELECT d.table_name, lv.lvl + 1
  FROM deps d JOIN lv ON lv.table_name = d.depends_on                            -- 読む表より1段あと
)
SELECT table_name, MAX(lvl) AS run_level       -- いちばん深い道の長さが、その表の段
FROM lv
GROUP BY table_name
ORDER BY run_level, table_name
OPTION (MAXRECURSION 100);

-- 流したあとの検査：読んだ表より古いデータの日付で作られた表を探す
-- run_log(table_name, data_date DATE, finished_at DATETIME2)
SELECT d.table_name, d.depends_on
FROM deps d
JOIN run_log a ON a.table_name = d.table_name
JOIN run_log b ON b.table_name = d.depends_on
WHERE a.data_date < b.data_date;           -- できあがりの時刻（finished_at）の比べでは見つからない場合がある
