-- 03 ある日に有効だったコードの数（T-SQL）。@d の日に valid_from <= @d <= valid_to の版を数える
SELECT d.as_of, COUNT(*) AS n_units,
       SUM(CASE WHEN m.code BETWEEN '13101' AND '13123' THEN 1 ELSE 0 END) AS n_ward23  -- 東京23区
FROM dbo.check_dates d
JOIN dbo.muni_scd2 m ON d.as_of BETWEEN m.valid_from AND m.valid_to
GROUP BY d.as_of
ORDER BY d.as_of;
