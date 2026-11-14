-- T-SQL：未検証（SQL Server では動かしていない）
-- A 列を固定した PIVOT（IN に書いた区分しか列にならない）
SELECT ym, [食品], [飲料], [日用品], [衣料], [家電], [雑貨]
FROM (SELECT ym, category, amount FROM dbo.sales) s
PIVOT (SUM(amount) FOR category IN ([食品], [飲料], [日用品], [衣料], [家電], [雑貨])) p
ORDER BY ym;
-- B 「その他」と「合計」の列を足しておく
SELECT ym,
       SUM(CASE WHEN category = N'食品' THEN amount ELSE 0 END) AS [食品],
       SUM(CASE WHEN category NOT IN (N'食品', N'飲料', N'日用品', N'衣料', N'家電', N'雑貨') THEN amount ELSE 0 END) AS [その他],
       SUM(amount) AS [合計]
FROM dbo.sales GROUP BY ym ORDER BY ym;
-- D 固定の列に入っていない区分を探す
SELECT category, MIN(ym) AS first_month, SUM(amount) AS amount
FROM dbo.sales
WHERE category NOT IN (N'食品', N'飲料', N'日用品', N'衣料', N'家電', N'雑貨')
GROUP BY category ORDER BY first_month;
