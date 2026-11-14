-- T-SQL：未検証（SQL Server では動かしていない）
-- SQL Server の GROUP BY も、NULL のキーを1つのまとまりとして残す
SELECT store, SUM(amount) AS amount FROM dbo.lines GROUP BY store ORDER BY store;
-- キーの欠けを数える
SELECT SUM(CASE WHEN store IS NULL THEN 1 ELSE 0 END) AS n_null_store,
       SUM(CASE WHEN category IS NULL THEN 1 ELSE 0 END) AS n_null_category
FROM dbo.lines;
