-- T-SQL：未検証（TRIM で全角の空白を除けるかは版によって違う。ここでは REPLACE で全角の空白を半角にしてから LTRIM/RTRIM）
SELECT source,
       COUNT(*)                                                           AS n,
       SUM(CASE WHEN building IS NULL THEN 1 ELSE 0 END)                  AS blank_isnull,
       SUM(CASE WHEN building IS NULL OR building = '' THEN 1 ELSE 0 END) AS blank_empty,
       SUM(CASE WHEN building IS NULL
                  OR LTRIM(RTRIM(REPLACE(building, N'　', N' '))) = '' THEN 1 ELSE 0 END) AS blank_trim,
       COUNT(building)                                                    AS count_col
FROM dbo.customers
GROUP BY source
ORDER BY source;
