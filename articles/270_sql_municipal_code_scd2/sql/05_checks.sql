-- 05 照合（T-SQL）。① 2000年の単位がちょうど1つの今の単位に入る ② 人口の合計が変わらない
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT code2000) AS n_old, COUNT(DISTINCT code_now) AS n_now
FROM dbo.crosswalk;

SELECT COUNT(*) AS n_now_not_in_2020
FROM (SELECT DISTINCT code_now FROM dbo.crosswalk) c
WHERE NOT EXISTS (SELECT 1 FROM dbo.units2020 u WHERE u.code = c.code_now);

SELECT SUM(u.pop2000) AS pop2000_rolled
FROM dbo.crosswalk c JOIN dbo.units2000 u ON u.code = c.code2000;
