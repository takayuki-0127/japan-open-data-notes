-- T-SQL：未検証（SQL Server では動かしていない）
-- DATEDIFF(year, …) は年の境目をまたいだ回数を返すので、誕生日前の人は1歳多くなる
DECLARE @ref date = '2025-10-01';
SELECT member_id, birth_date,
       DATEDIFF(year, birth_date, @ref) AS age_year_diff,
       DATEDIFF(year, birth_date, @ref)
         - CASE WHEN FORMAT(@ref, 'MMdd') < FORMAT(birth_date, 'MMdd') THEN 1 ELSE 0 END AS age_true
FROM dbo.members;
-- 別の書き方：(CONVERT(int, FORMAT(@ref, 'yyyyMMdd')) - CONVERT(int, FORMAT(birth_date, 'yyyyMMdd'))) / 10000
