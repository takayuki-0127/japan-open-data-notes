-- 02 期間つきのマスタ（SCD2）を作る（T-SQL）。1行＝あるコードの、ある期間の姿（版）
WITH starts AS (            -- 版が始まる日：2000年10月1日と、新しく生まれた日・区域が変わった日
    SELECT code, CAST('2000-10-01' AS DATE) AS valid_from, name FROM dbo.units2000
    UNION
    SELECT new_code, eff_date, MIN(new_name) FROM dbo.events_x GROUP BY new_code, eff_date
),
ends AS (                   -- コードが消える日（別のコードに変わった日）
    SELECT old_code AS code, MIN(eff_date) AS end_date
    FROM dbo.events_x WHERE old_code <> new_code GROUP BY old_code
),
v AS (
    SELECT s.code, s.name, s.valid_from,
           COALESCE(DATEADD(day, -1, LEAD(s.valid_from) OVER (PARTITION BY s.code ORDER BY s.valid_from)),
                    DATEADD(day, -1, e.end_date),
                    CAST('9999-12-31' AS DATE)) AS valid_to
    FROM starts s LEFT JOIN ends e ON e.code = s.code
)
SELECT ROW_NUMBER() OVER (ORDER BY code, valid_from) AS sk,      -- 版ごとの番号（代理キー）
       code, name, valid_from, valid_to
INTO dbo.muni_scd2
FROM v
WHERE valid_from <= valid_to;   -- 同じ日に「編入→市制」があると長さ0の版ができるので落とす
