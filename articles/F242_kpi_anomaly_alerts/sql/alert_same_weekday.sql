-- 毎日の KPI の警報（SQL Server／T-SQL）
-- ルール：今日の値（対数）を「前の同じ曜日4回の平均」と比べ、その差を「前56日の差の標準偏差」で割る。|z| > 3.5 なら警報。
-- テーブル kpi_daily(kpi_date DATE PRIMARY KEY, kpi_value FLOAT)。祝日・販促の日の扱いは別テーブル（calendar）で除外する想定。
WITH base AS (
    SELECT kpi_date,
           LOG(kpi_value) AS ly,
           DATEPART(weekday, kpi_date) AS wd
    FROM kpi_daily
),
same_wd AS (
    SELECT kpi_date, ly, wd,
           AVG(ly) OVER (PARTITION BY wd ORDER BY kpi_date ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) AS ly_base,
           COUNT(*) OVER (PARTITION BY wd ORDER BY kpi_date ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING) AS n_base
    FROM base
),
dev AS (
    SELECT kpi_date, ly, ly - ly_base AS e
    FROM same_wd
    WHERE n_base = 4
),
scored AS (
    SELECT kpi_date, e,
           STDEV(e) OVER (ORDER BY kpi_date ROWS BETWEEN 56 PRECEDING AND 1 PRECEDING) AS e_sd,
           COUNT(e) OVER (ORDER BY kpi_date ROWS BETWEEN 56 PRECEDING AND 1 PRECEDING) AS n_sd
    FROM dev
)
SELECT kpi_date,
       ROUND(e / NULLIF(e_sd, 0), 2) AS z,
       CASE WHEN ABS(e / NULLIF(e_sd, 0)) > 3.5 THEN 1 ELSE 0 END AS alert,
       CASE WHEN e < 0 THEN N'下振れ' ELSE N'上振れ' END AS direction
FROM scored
WHERE n_sd = 56
ORDER BY kpi_date;
