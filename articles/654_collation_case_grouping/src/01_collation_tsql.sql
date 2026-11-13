-- T-SQL：未検証（SQL Server では動かしていない）
-- SQL Server の既定の照合順序（例：Japanese_CI_AS）は大文字小文字を区別しない（CI）。区別したいときは CS を指定する
SELECT COUNT(DISTINCT email COLLATE Japanese_CS_AS) AS n_case_sensitive,
       COUNT(DISTINCT email COLLATE Japanese_CI_AS) AS n_nocase,
       COUNT(DISTINCT LOWER(email))                 AS n_lower
FROM dbo.orders;

SELECT COUNT(DISTINCT code COLLATE Japanese_CS_AS) AS n_cs,
       COUNT(DISTINCT code COLLATE Japanese_CI_AS) AS n_ci
FROM dbo.coupons_used;
