-- T-SQL 版（SQL Server では動かしていない：未検証）
-- dbo.sends(id int, variant char(1), auto_device bit, first_open_min float NULL, clicked bit)
SELECT variant,
    100.0 * AVG(CASE WHEN first_open_min IS NOT NULL THEN 1.0 ELSE 0 END)                AS all_opens,
    100.0 * AVG(CASE WHEN first_open_min > 5 THEN 1.0 ELSE 0 END)                       AS excl_quick,
    100.0 * AVG(CASE WHEN clicked = 1 THEN 1.0 ELSE 0 END)                              AS clickers,
    100.0 * AVG(CASE WHEN first_open_min > 5 OR clicked = 1 THEN 1.0 ELSE 0 END)        AS excl_quick_or_click,
    100.0 * AVG(CASE WHEN auto_device = 0 THEN CASE WHEN first_open_min IS NOT NULL THEN 1.0 ELSE 0 END END) AS non_auto_only
FROM dbo.sends
GROUP BY variant
ORDER BY variant;
