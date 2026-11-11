-- 送る前の確認：集計表に「先週」の行がそろっているか（T-SQL）
-- @expected_week：送る日の前の週の月曜日
DECLARE @expected_week DATE = '2025-12-29';
SELECT MAX(week_start)                                         AS latest_week,
       SUM(CASE WHEN week_start = @expected_week THEN 1 ELSE 0 END) AS rows_for_expected,
       CASE WHEN MAX(week_start) = @expected_week
             AND SUM(CASE WHEN week_start = @expected_week THEN 1 ELSE 0 END) = 4  -- KPI 4つ
            THEN 'OK' ELSE 'WAIT' END                          AS status
FROM dbo.weekly_kpi;
