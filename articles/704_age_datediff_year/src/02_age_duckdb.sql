-- 年齢を「年の差」だけで出すか、誕生日を考えて出すか（DuckDB 版）
-- members(member_id, birth_date DATE)、基準日は $ref の代わりに DATE '2025-10-01' を直接書く
SELECT member_id, birth_date,
       date_diff('year', birth_date, DATE '2025-10-01') AS age_year_diff,          -- 年の境目をまたいだ回数
       date_diff('year', birth_date, DATE '2025-10-01')
         - CASE WHEN strftime(DATE '2025-10-01', '%m%d') < strftime(birth_date, '%m%d') THEN 1 ELSE 0 END AS age_true
FROM members
ORDER BY member_id;
-- 10歳ごとの人数
SELECT (age_year_diff // 10) * 10 AS band, COUNT(*) AS n_year_diff
FROM ages
GROUP BY band
ORDER BY band;
