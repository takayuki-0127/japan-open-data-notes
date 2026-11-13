-- T-SQL 版（SQL Server では動かしていない：未検証）
SELECT SUM(amount)                                                                AS sum_all,
       SUM(CASE WHEN filtered_out = 0 THEN amount END)                            AS subtotal_9,
       SUM(CASE WHEN filtered_out = 0 AND manual_hidden = 0 THEN amount END)      AS subtotal_109
FROM dbo.detail;
